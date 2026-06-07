"""Run the mail-pipeline ingest."""

from __future__ import annotations

import argparse
import base64
import imaplib
import json
import os
import sqlite3
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import data_dir, events_dir, load_accounts, load_processors, select_accounts, select_processors, state_dir
from parser import parse_bytes, parse_file


def _classify(message: dict, processor_names: set[str]) -> dict:
    subject = str(message["source"].get("subject") or "").lower()
    text = str(message.get("text") or "").lower()
    attachment_names = " ".join(str(item.get("filename", "")).lower() for item in message.get("attachments", []))
    haystack = " ".join([subject, text, attachment_names])
    if "invoice" in haystack or "发票" in haystack or "账单" in haystack:
        category = "invoices"
        reason = "Invoice-like keyword found in subject, body, or attachment filename."
        confidence = 0.82
    elif any(term in haystack for term in ["unsubscribe", "promotion", "newsletter", "sale"]):
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


def _fetch_imap(account, limit: int) -> list[dict]:
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
        status, data = client.uid("search", None, "ALL")
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


def _safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value.strip())
    return cleaned.strip("._") or "message"


def _within_root(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _safe_relative_path(root: Path, value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        raise ValueError(f"path must be relative to data dir: {value}")
    target = root / raw
    if not _within_root(root, target):
        raise ValueError(f"path escapes data dir: {value}")
    return target


def _attachment_dir(root: Path, processor, message: dict, category: str) -> Path:
    template = processor.file_dir or "files/{account_id}/{category}"
    rendered = template.format(
        account_id=_safe_name(str(message["account_id"])),
        category=_safe_name(category),
    )
    return _safe_relative_path(root, rendered)


def _save_attachments(root: Path, processor, message: dict, category: str, apply: bool) -> list[dict]:
    if "save_attachment" not in processor.allowed_actions:
        return []
    saved = []
    target_dir = _attachment_dir(root, processor, message, category)
    for item in message.get("attachments", []):
        sha8 = item["sha256"][:8]
        filename = _safe_name(item["filename"])
        subject = _safe_name(str(message["source"].get("subject") or "message"))[:80]
        target = target_dir / f"{subject}_{sha8}_{filename}"
        if not _within_root(root, target):
            raise ValueError(f"attachment path escapes data dir: {target}")
        record = {
            "original_filename": item["filename"],
            "saved_path": str(target),
            "sha256": item["sha256"],
            "mime_type": item["mime_type"],
            "size_bytes": item["size_bytes"],
        }
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(item["content_b64"]))
        saved.append(record)
    return saved


def _write_jsonl(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run mail-pipeline ingest.")
    parser.add_argument("--account", default="all", help="Account id or 'all'.")
    parser.add_argument("--processor", default="all", help="Processor name or 'all'.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum messages per account.")
    parser.add_argument("--fixture-dir", help="Read local .eml files instead of IMAP.")
    parser.add_argument("--apply", action="store_true", help="Write files/state and modify allowed mailbox state.")
    args = parser.parse_args()

    root = data_dir()
    try:
        processors = select_processors(load_processors(root), args.processor)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)

    if args.fixture_dir:
        fixture_dir = Path(args.fixture_dir).expanduser()
        paths = sorted(fixture_dir.glob("*.eml"))[: args.limit]
        messages = [parse_file(path, account_id=args.account if args.account != "all" else "fixture") for path in paths]
    else:
        try:
            accounts = select_accounts(load_accounts(root), args.account)
            messages = []
            for account in accounts:
                messages.extend(_fetch_imap(account, args.limit))
        except Exception as exc:
            print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
            raise SystemExit(1)

    processor_names = {processor.name for processor in processors}
    processors_by_name = {processor.name: processor for processor in processors}
    conn = _init_state(state_dir(root) / "processed.sqlite") if args.apply else None
    events = []
    skipped = 0
    for message in messages:
        classification = _classify(message, processor_names)
        processor = processors_by_name[classification["category"]]
        processed_at = datetime.now(timezone.utc).isoformat()
        key = _dedupe_key(message)
        if conn is not None and _already_processed(conn, key):
            skipped += 1
            continue
        try:
            processor_jsonl = _safe_relative_path(root, processor.output_jsonl)
            saved_attachments = _save_attachments(root, processor, message, classification["category"], args.apply)
        except ValueError as exc:
            if conn is not None:
                conn.close()
            print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
            raise SystemExit(1)
        event = {
            "schema_version": "1.0",
            "processed_at": processed_at,
            "account_id": message["account_id"],
            "source": message["source"],
            "classification": classification,
            "extracted": {},
            "attachments": saved_attachments,
            "actions": [
                {"type": "write_jsonl", "target": "events/all.jsonl"},
                {"type": "write_jsonl", "target": processor.output_jsonl},
            ] + ([{"type": "save_attachment", "count": len(saved_attachments)}] if saved_attachments else []),
            "status": "processed" if args.apply else "dry_run",
        }
        events.append(event)
        if args.apply:
            _write_jsonl(events_dir(root) / "all.jsonl", event)
            _write_jsonl(processor_jsonl, event)
            if conn is not None:
                _mark_processed(conn, key, processed_at)
    if conn is not None:
        conn.close()

    print(
        json.dumps(
            {
                "status": "ok",
                "apply": args.apply,
                "data_dir": str(root),
                "processed": len(events),
                "skipped": skipped,
                "events": events if not args.apply else [],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
