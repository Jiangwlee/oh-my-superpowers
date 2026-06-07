"""Stage one invoice message for agent extraction.

Called after the agent judges a message to be an invoice. Collects PDFs from
pdf/zip attachments (zip members expanded) or allowlisted provider links,
saves them under the data directory, and writes a pending manifest for
`submit` to finalize.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from common import (
    already_processed,
    append_jsonl,
    data_dir,
    dedupe_key,
    events_dir,
    load_accounts,
    load_processors,
    mark_processed,
    open_dedupe_db,
    pending_dir,
    safe_name,
    safe_relative_path,
    select_accounts,
    within_root,
)
from linkfetch import fetch_link_attachments
from mailfetch import fetch_message
from parser import parse_file


def _fail(error: str) -> None:
    print(json.dumps({"status": "error", "error": error}, ensure_ascii=False, indent=2), file=sys.stderr)
    raise SystemExit(1)


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


def _collect_pdfs(message: dict, processor) -> tuple[list[dict], dict]:
    """Collect invoice PDFs from pdf/zip attachments, falling back to link fetch."""
    pdfs: list[dict] = []
    for item in message.get("attachments", []):
        name = str(item.get("filename", "")).lower()
        if name.endswith(".pdf"):
            pdfs.append(item)
        elif name.endswith(".zip"):
            pdfs.extend(_zip_pdfs(item))
    if pdfs:
        return pdfs, {}
    if processor.link_providers:
        fetched, provider_meta = fetch_link_attachments(message, processor.link_providers)
        if fetched:
            return fetched, provider_meta
    raise ValueError("no pdf/zip attachment and no allowlisted invoice link")


def _attachment_dir(root: Path, processor, message: dict) -> Path:
    template = processor.file_dir or "files/{account_id}/{category}"
    rendered = template.format(
        account_id=safe_name(str(message["account_id"])),
        category=safe_name(processor.name),
    )
    return safe_relative_path(root, rendered)


def _save_attachments(root: Path, processor, message: dict, attachments: list[dict]) -> list[dict]:
    if "save_attachment" not in processor.allowed_actions:
        raise ValueError(f"processor {processor.name!r} does not allow save_attachment")
    saved = []
    target_dir = _attachment_dir(root, processor, message)
    for item in attachments:
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
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(item["content_b64"]))
        saved.append(record)
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage one invoice message for agent extraction.")
    parser.add_argument("--account", required=True, help="Account id.")
    parser.add_argument("--uid", required=True, help="IMAP uid (or file stem in fixture mode).")
    parser.add_argument("--fixture-dir", help="Read local .eml files instead of IMAP.")
    args = parser.parse_args()

    root = data_dir()
    try:
        processors = load_processors(root)
        processor = next((item for item in processors if item.extract == "invoice"), None)
        if processor is None:
            raise ValueError("no processor with `extract: invoice` configured")
        if args.fixture_dir:
            path = Path(args.fixture_dir).expanduser() / f"{args.uid}.eml"
            if not path.exists():
                raise ValueError(f"fixture not found: {path}")
            message = parse_file(path, account_id=args.account)
            message["source"]["imap_uid"] = args.uid
        else:
            account = select_accounts(load_accounts(root), args.account)[0]
            message = fetch_message(account, args.uid)
            if message is None:
                raise ValueError(f"message uid {args.uid!r} not found in inbox of account {account.id!r}")
    except Exception as exc:
        _fail(str(exc))

    key = dedupe_key(message)
    conn = open_dedupe_db(root, create=True)
    if already_processed(conn, key):
        conn.close()
        _fail(f"message already staged or processed (dedupe key match); uid {args.uid}")

    processed_at = datetime.now(timezone.utc).isoformat()
    try:
        pdfs, provider_meta = _collect_pdfs(message, processor)
        processor_jsonl = safe_relative_path(root, processor.output_jsonl)
        saved = _save_attachments(root, processor, message, pdfs)
    except (ValueError, OSError) as exc:
        conn.close()
        _fail(str(exc))

    pending_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    manifest = {
        "pending_id": pending_id,
        "created_at": processed_at,
        "account_id": message["account_id"],
        "source": message["source"],
        "category": processor.name,
        "processor": processor.name,
        "output_jsonl": processor.output_jsonl,
        "rename_template": processor.rename_template,
        "provider_meta": provider_meta,
        "attachments": saved,
    }
    manifest_path = pending_dir(root) / f"{pending_id}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    event = {
        "schema_version": "1.0",
        "processed_at": processed_at,
        "account_id": message["account_id"],
        "source": message["source"],
        "classification": {"category": processor.name, "confidence": 1.0, "reason": "Agent judged this message an invoice and staged it."},
        "extracted": {},
        "attachments": saved,
        "actions": [
            {"type": "write_jsonl", "target": "events/all.jsonl"},
            {"type": "write_jsonl", "target": processor.output_jsonl},
            {"type": "save_attachment", "count": len(saved)},
            {"type": "stage_for_extraction", "pending_id": pending_id},
        ],
        "status": "pending_extraction",
    }
    append_jsonl(events_dir(root) / "all.jsonl", event)
    append_jsonl(processor_jsonl, event)
    mark_processed(conn, key, processed_at)
    conn.close()

    print(
        json.dumps(
            {
                "status": "ok",
                "pending_id": pending_id,
                "subject": message["source"].get("subject"),
                "files": [record["saved_path"] for record in saved],
                "provider_meta": provider_meta,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
