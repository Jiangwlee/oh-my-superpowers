"""Finalize a pending extraction with agent-submitted invoice fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import append_jsonl, data_dir, events_dir, pending_dir, safe_name, safe_relative_path, within_root
from extract import cross_check, validate_invoice_fields


def _fail(error: str, **extra) -> None:
    print(json.dumps({"status": "error", "error": error, **extra}, ensure_ascii=False, indent=2), file=sys.stderr)
    raise SystemExit(1)


def _render_rename_base(template: str, fields: dict) -> str:
    """Render a rename template from submitted fields, sanitized per component."""
    rendered = template.format(**{key: safe_name(str(value)) for key, value in fields.items()})
    return safe_name(rendered)


def _rename_files(root: Path, records: list[dict], rename_base: str) -> list[dict]:
    """Rename staged files to the rendered base, keeping extensions."""
    renamed = []
    used_names: set[str] = set()
    for record in records:
        source = Path(record["saved_path"])
        if not within_root(root, source):
            raise ValueError(f"staged path escapes data dir: {source}")
        if not source.exists():
            raise ValueError(f"staged file missing: {source}")
        suffix = source.suffix
        name = f"{rename_base}{suffix}"
        if name in used_names:
            name = f"{rename_base}_{record['sha256'][:8]}{suffix}"
        target = source.with_name(name)
        # Never overwrite an existing file with different content (e.g. two
        # invoices rendering the same base name from a prior submit).
        if target.exists() and target != source:
            existing_sha = hashlib.sha256(target.read_bytes()).hexdigest()
            if existing_sha != record["sha256"]:
                name = f"{rename_base}_{record['sha256'][:8]}{suffix}"
                target = source.with_name(name)
        used_names.add(name)
        if not within_root(root, target):
            raise ValueError(f"rename target escapes data dir: {target}")
        if source != target:
            source.rename(target)
        renamed.append({**record, "saved_path": str(target)})
    return renamed


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit extracted invoice fields for a pending message.")
    parser.add_argument("--id", required=True, help="Pending extraction id from `run` output or `status`.")
    parser.add_argument("--fields", required=True, help="Extracted fields as a JSON object string.")
    args = parser.parse_args()

    root = data_dir()
    manifest_path = pending_dir(root) / f"{safe_name(args.id)}.json"
    if not manifest_path.exists():
        _fail(f"no pending extraction with id {args.id!r}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    try:
        fields = validate_invoice_fields(json.loads(args.fields))
    except (json.JSONDecodeError, ValueError) as exc:
        _fail(f"invalid fields: {exc}")

    mismatches = cross_check(fields, manifest.get("provider_meta") or {})
    if mismatches:
        _fail(
            "submitted fields disagree with provider metadata; re-check the PDF and resubmit",
            mismatches=mismatches,
            pending_id=manifest["pending_id"],
        )

    records = manifest.get("attachments") or []
    try:
        if manifest.get("rename_template"):
            rename_base = _render_rename_base(manifest["rename_template"], fields)
            records = _rename_files(root, records, rename_base)
        processor_jsonl = safe_relative_path(root, manifest["output_jsonl"])
    except (KeyError, ValueError) as exc:
        _fail(str(exc))

    processed_at = datetime.now(timezone.utc).isoformat()
    event = {
        "schema_version": "1.0",
        "processed_at": processed_at,
        "account_id": manifest["account_id"],
        "source": manifest["source"],
        "classification": {
            "category": manifest["category"],
            "confidence": fields.get("confidence", 1.0),
            "reason": "Fields extracted by agent and validated via submit.",
        },
        "extracted": {"invoice": fields},
        "attachments": records,
        "actions": [
            {"type": "write_jsonl", "target": "events/all.jsonl"},
            {"type": "write_jsonl", "target": manifest["output_jsonl"]},
            {"type": "rename_attachment", "count": len(records)},
        ],
        "status": "processed",
        "pending_id": manifest["pending_id"],
    }
    append_jsonl(events_dir(root) / "all.jsonl", event)
    append_jsonl(processor_jsonl, event)
    manifest_path.unlink()

    print(
        json.dumps(
            {
                "status": "ok",
                "pending_id": manifest["pending_id"],
                "extracted": fields,
                "files": [record["saved_path"] for record in records],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
