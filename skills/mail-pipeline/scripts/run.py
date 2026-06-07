"""Run the mail-pipeline ingest."""

from __future__ import annotations

import argparse
import base64
import hashlib
import imaplib
import io
import json
import os
import sqlite3
import ssl
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

from common import (
    append_jsonl,
    data_dir,
    events_dir,
    load_accounts,
    load_processors,
    pending_dir,
    safe_name,
    safe_relative_path,
    select_accounts,
    select_processors,
    state_dir,
    within_root,
)
from linkfetch import extract_urls, fetch_link_attachments, match_provider
from parser import parse_bytes, parse_file


def _classify(message: dict, processor_names: set[str]) -> dict:
    subject = str(message["source"].get("subject") or "").lower()
    text = str(message.get("text") or "").lower()
    html = str(message.get("html") or "").lower()
    attachment_names = " ".join(str(item.get("filename", "")).lower() for item in message.get("attachments", []))
    haystack = " ".join([subject, text, html, attachment_names])
    if "invoice" in haystack or "发票" in haystack or "账单" in haystack:
        category = "invoices"
        reason = "Invoice-like keyword found in subject, body, or attachment filename."
        confidence = 0.82
    elif any(term in haystack for term in ["unsubscribe", "promotion", "newsletter", "sale", "退订"]):
        category = "spam_ads"
        reason = "Marketing or subscription keyword found."
        confidence = 0.76
    elif any(term in haystack for term in ["urgent", "deadline", "action required", "security"]):
        category = "important"
        reason = "Important action or security keyword found."
        confidence = 0.74
    else:
        category = "needs_review"
        reason = "No configured deterministic rule matched."
        confidence = 0.45
    if category not in processor_names:
        category = "needs_review" if "needs_review" in processor_names else next(iter(processor_names))
        reason = "Matched category is not selected; routed to available processor."
        confidence = min(confidence, 0.5)
    return {"category": category, "confidence": confidence, "reason": reason}


_IMAP_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _imap_since(value: date) -> str:
    """Format a date as a locale-independent IMAP SEARCH date."""
    return f"{value.day:02d}-{_IMAP_MONTHS[value.month - 1]}-{value.year}"


def _message_on_or_after(message: dict, since: date) -> bool:
    raw = message["source"].get("date")
    if not raw:
        return True
    try:
        return datetime.fromisoformat(raw).date() >= since
    except ValueError:
        return True


def _fetch_imap(account, limit: int, since: date | None) -> list[dict]:
    """Fetch the most recent inbox messages for one account, read-only."""
    password = os.environ.get(account.password_env) if account.password_env else None
    if not password:
        raise ValueError(f"missing password env: {account.password_env or '<unset>'} for account {account.id!r}")
    context = ssl.create_default_context()
    messages: list[dict] = []
    with imaplib.IMAP4_SSL(account.host, account.port, ssl_context=context, timeout=30) as client:
        client.login(account.username, password)
        status, _ = client.select(account.inbox, readonly=True)
        if status != "OK":
            raise ValueError(f"select failed for inbox {account.inbox!r} on account {account.id!r}")
        criteria = ("SINCE", _imap_since(since)) if since else ("ALL",)
        status, data = client.uid("search", None, *criteria)
        if status != "OK":
            raise ValueError(f"uid search failed on account {account.id!r}")
        uids = data[0].split()
        for uid in uids[-limit:]:
            status, msg_data = client.uid("fetch", uid, "(BODY.PEEK[])")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            messages.append(parse_bytes(raw, account_id=account.id, mailbox=account.inbox, imap_uid=uid.decode()))
        client.logout()
    return messages


def _init_state(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        create table if not exists processed_messages (
            dedupe_key text primary key,
            processed_at text not null
        )
        """
    )
    return conn


def _dedupe_key(message: dict) -> str:
    message_id = message["source"].get("message_id") or ""
    attachments = message.get("attachments") or []
    hashes = ",".join(item["sha256"] for item in attachments)
    return f"{message['account_id']}|{message_id}|{hashes}"


def _already_processed(conn: sqlite3.Connection, key: str) -> bool:
    row = conn.execute("select 1 from processed_messages where dedupe_key = ?", (key,)).fetchone()
    return row is not None


def _mark_processed(conn: sqlite3.Connection, key: str, processed_at: str) -> None:
    conn.execute(
        "insert or ignore into processed_messages (dedupe_key, processed_at) values (?, ?)",
        (key, processed_at),
    )
    conn.commit()


def _attachment_dir(root: Path, processor, message: dict, category: str) -> Path:
    template = processor.file_dir or "files/{account_id}/{category}"
    rendered = template.format(
        account_id=safe_name(str(message["account_id"])),
        category=safe_name(category),
    )
    return safe_relative_path(root, rendered)


def _save_attachments(root: Path, processor, message: dict, category: str, apply: bool, attachments: list[dict] | None = None) -> list[dict]:
    if "save_attachment" not in processor.allowed_actions:
        return []
    saved = []
    target_dir = _attachment_dir(root, processor, message, category)
    for item in attachments if attachments is not None else message.get("attachments", []):
        sha8 = item["sha256"][:8]
        filename = safe_name(item["filename"])
        subject = safe_name(str(message["source"].get("subject") or "message"))[:80]
        target = target_dir / f"{subject}_{sha8}_{filename}"
        if not within_root(root, target):
            raise ValueError(f"attachment path escapes data dir: {target}")
        record = {
            "original_filename": item["filename"],
            "saved_path": str(target),
            "sha256": item["sha256"],
            "mime_type": item["mime_type"],
            "size_bytes": item["size_bytes"],
        }
        for key in ("origin", "source_url", "source_zip"):
            if item.get(key):
                record[key] = item[key]
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(item["content_b64"]))
        saved.append(record)
    return saved


def _zip_pdfs(item: dict) -> list[dict]:
    """Expand PDF members from a zip attachment into attachment records."""
    payload = base64.b64decode(item["content_b64"])
    records: list[dict] = []
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for info in archive.infolist():
                if info.is_dir() or not info.filename.lower().endswith(".pdf"):
                    continue
                data = archive.read(info)
                records.append(
                    {
                        "filename": Path(info.filename).name,
                        "mime_type": "application/pdf",
                        "size_bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "content_b64": base64.b64encode(data).decode("ascii"),
                        "origin": "zip",
                        "source_zip": item["filename"],
                    }
                )
    except zipfile.BadZipFile:
        return []
    return records


def _invoice_attachments(message: dict, processor, apply: bool) -> tuple[list[dict], dict, str | None, str | None]:
    """Collect invoice PDFs from pdf/zip attachments, falling back to link fetch.

    Returns (pdfs, provider_meta, planned_provider, error). Link fetch only
    touches the network under --apply; dry-run reports the matched provider.
    """
    pdfs: list[dict] = []
    for item in message.get("attachments", []):
        name = str(item.get("filename", "")).lower()
        if name.endswith(".pdf"):
            pdfs.append(item)
        elif name.endswith(".zip"):
            pdfs.extend(_zip_pdfs(item))
    if pdfs:
        return pdfs, {}, None, None
    if processor.link_providers:
        matched = next(
            (provider for url in extract_urls(message) if (provider := match_provider(url, processor.link_providers))),
            None,
        )
        if matched and not apply:
            return [], {}, matched, None
        if matched:
            try:
                fetched, provider_meta = fetch_link_attachments(message, processor.link_providers)
            except (ValueError, OSError) as exc:
                return [], {}, None, f"link fetch failed: {exc}"
            if fetched:
                return fetched, provider_meta, None, None
            return [], {}, None, f"link fetch from {matched} returned no PDF"
    return [], {}, None, "no pdf/zip attachment and no allowlisted invoice link"


def _pending_id(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def _move_target(processor) -> str | None:
    """Return the processor's move folder key when moving is allowed."""
    if processor.move_to and "move_email" in processor.allowed_actions:
        return processor.move_to
    return None


def _apply_mailbox_mutations(account, mark_read: list[str], moves: list[tuple[str, str]]) -> list[str]:
    """Mark messages read and move them; returns error descriptions.

    Runs after events and dedupe state are written so a mailbox failure
    never loses pipeline data.
    """
    errors: list[str] = []
    password = os.environ.get(account.password_env) if account.password_env else None
    if not password:
        return [f"missing password env for account {account.id!r}"]
    folder_map = {"inbox": account.inbox, "processed": account.processed, "needs_review": account.needs_review, "trash": account.trash}
    context = ssl.create_default_context()
    with imaplib.IMAP4_SSL(account.host, account.port, ssl_context=context, timeout=30) as client:
        client.login(account.username, password)
        status, _ = client.select(account.inbox)
        if status != "OK":
            return [f"select failed for inbox {account.inbox!r} on account {account.id!r}"]
        if mark_read:
            status, _ = client.uid("STORE", ",".join(mark_read), "+FLAGS.SILENT", r"(\Seen)")
            if status != "OK":
                errors.append(f"mark_read failed for uids {','.join(mark_read)}")
        has_move = any(cap.upper() == "MOVE" for cap in client.capabilities)
        expunge_needed = False
        for uid, folder_key in moves:
            target = folder_map.get(folder_key)
            if not target:
                errors.append(f"move_email target {folder_key!r} not configured for account {account.id!r}")
                continue
            quoted = f'"{target}"'
            if has_move:
                status, _ = client.uid("MOVE", uid, quoted)
                if status != "OK":
                    errors.append(f"move failed for uid {uid} -> {target}")
            else:
                status, _ = client.uid("COPY", uid, quoted)
                if status != "OK":
                    errors.append(f"copy failed for uid {uid} -> {target}")
                    continue
                client.uid("STORE", uid, "+FLAGS.SILENT", r"(\Deleted)")
                expunge_needed = True
        if expunge_needed:
            client.expunge()
        client.logout()
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Run mail-pipeline ingest.")
    parser.add_argument("--account", default="all", help="Account id or 'all'.")
    parser.add_argument("--processor", default="all", help="Processor name or 'all'.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum messages per account.")
    parser.add_argument("--fixture-dir", help="Read local .eml files instead of IMAP.")
    parser.add_argument("--apply", action="store_true", help="Write files/state and modify allowed mailbox state.")
    parser.add_argument("--since", help="Only process messages dated on/after this day (YYYY-MM-DD).")
    args = parser.parse_args()
    try:
        since = date.fromisoformat(args.since) if args.since else None
    except ValueError as exc:
        print(json.dumps({"status": "error", "error": f"invalid --since: {exc}"}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)

    root = data_dir()
    try:
        processors = select_processors(load_processors(root), args.processor)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)

    accounts_by_id = {}
    if args.fixture_dir:
        fixture_dir = Path(args.fixture_dir).expanduser()
        paths = sorted(fixture_dir.glob("*.eml"))[: args.limit]
        messages = [parse_file(path, account_id=args.account if args.account != "all" else "fixture") for path in paths]
        if since:
            messages = [message for message in messages if _message_on_or_after(message, since)]
    else:
        try:
            accounts = select_accounts(load_accounts(root), args.account)
            accounts_by_id = {account.id: account for account in accounts}
            messages = []
            for account in accounts:
                messages.extend(_fetch_imap(account, args.limit, since))
        except Exception as exc:
            print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
            raise SystemExit(1)

    processor_names = {processor.name for processor in processors}
    processors_by_name = {processor.name: processor for processor in processors}
    # Dry-run reads existing dedupe state (without creating it) so the
    # preview matches what --apply would actually process.
    db_path = state_dir(root) / "processed.sqlite"
    if args.apply:
        conn = _init_state(db_path)
    else:
        conn = sqlite3.connect(db_path) if db_path.exists() else None
    events = []
    pending = []
    skipped = 0
    mutations: dict[str, dict[str, list]] = {}
    for message in messages:
        classification = _classify(message, processor_names)
        processor = processors_by_name[classification["category"]]
        processed_at = datetime.now(timezone.utc).isoformat()
        key = _dedupe_key(message)
        if conn is not None and _already_processed(conn, key):
            skipped += 1
            continue

        stage_attachments: list[dict] | None = None
        provider_meta: dict = {}
        planned_provider: str | None = None
        if processor.extract == "invoice":
            pdfs, provider_meta, planned_provider, error = _invoice_attachments(message, processor, args.apply)
            if error:
                processor = processors_by_name.get("needs_review", processor)
                classification = {"category": processor.name, "confidence": 0.3, "reason": f"invoice staging failed: {error}"}
            else:
                stage_attachments = pdfs

        try:
            processor_jsonl = safe_relative_path(root, processor.output_jsonl)
            saved_attachments = _save_attachments(root, processor, message, classification["category"], args.apply, stage_attachments)
        except ValueError as exc:
            if conn is not None:
                conn.close()
            print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
            raise SystemExit(1)

        actions = [
            {"type": "write_jsonl", "target": "events/all.jsonl"},
            {"type": "write_jsonl", "target": processor.output_jsonl},
        ]
        if saved_attachments:
            actions.append({"type": "save_attachment", "count": len(saved_attachments)})
        if planned_provider:
            actions.append({"type": "fetch_links", "provider": planned_provider})
        move_folder_key = _move_target(processor)
        imap_uid = message["source"].get("imap_uid")
        if imap_uid:
            actions.append({"type": "mark_read"})
            if move_folder_key:
                actions.append({"type": "move_email", "target": move_folder_key})
            if args.apply and message["account_id"] in accounts_by_id:
                account_mutations = mutations.setdefault(message["account_id"], {"mark_read": [], "moves": []})
                account_mutations["mark_read"].append(imap_uid)
                if move_folder_key:
                    account_mutations["moves"].append((imap_uid, move_folder_key))

        status = "dry_run"
        pending_id = None
        if processor.extract == "invoice" and stage_attachments is not None:
            pending_id = _pending_id(key)
            actions.append({"type": "stage_for_extraction", "pending_id": pending_id})
            if args.apply:
                status = "pending_extraction"
                manifest = {
                    "pending_id": pending_id,
                    "created_at": processed_at,
                    "account_id": message["account_id"],
                    "source": message["source"],
                    "category": classification["category"],
                    "processor": processor.name,
                    "output_jsonl": processor.output_jsonl,
                    "rename_template": processor.rename_template,
                    "provider_meta": provider_meta,
                    "attachments": saved_attachments,
                }
                manifest_path = pending_dir(root) / f"{pending_id}.json"
                manifest_path.parent.mkdir(parents=True, exist_ok=True)
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            pending.append(
                {
                    "pending_id": pending_id,
                    "subject": message["source"].get("subject"),
                    "files": [record["saved_path"] for record in saved_attachments],
                }
            )
        elif args.apply:
            status = "processed"

        event = {
            "schema_version": "1.0",
            "processed_at": processed_at,
            "account_id": message["account_id"],
            "source": message["source"],
            "classification": classification,
            "extracted": {},
            "attachments": saved_attachments,
            "actions": actions,
            "status": status,
        }
        events.append(event)
        if args.apply:
            append_jsonl(events_dir(root) / "all.jsonl", event)
            append_jsonl(processor_jsonl, event)
            _mark_processed(conn, key, processed_at)
    if conn is not None:
        conn.close()

    mailbox_errors: list[str] = []
    mailbox_applied = {"mark_read": 0, "moved": 0}
    for account_id, account_mutations in mutations.items():
        try:
            errors = _apply_mailbox_mutations(accounts_by_id[account_id], account_mutations["mark_read"], account_mutations["moves"])
        except Exception as exc:
            errors = [f"mailbox mutation failed for account {account_id!r}: {exc}"]
        mailbox_errors.extend(errors)
        mailbox_applied["mark_read"] += len(account_mutations["mark_read"])
        mailbox_applied["moved"] += len(account_mutations["moves"])

    print(
        json.dumps(
            {
                "status": "ok",
                "apply": args.apply,
                "data_dir": str(root),
                "processed": len(events),
                "skipped": skipped,
                "pending": pending,
                "mailbox": mailbox_applied,
                "mailbox_errors": mailbox_errors,
                "events": events if not args.apply else [],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
