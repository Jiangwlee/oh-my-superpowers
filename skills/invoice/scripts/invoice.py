#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["pyyaml>=6.0.0,<7"]
# ///
"""Invoice registry command implementation."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any

import yaml

DEFAULT_ROOT = Path.home() / ".local" / "share" / "oh-my-superpowers" / "invoice"
DATA_DIR = Path(os.environ.get("INVOICE_DATA_DIR", DEFAULT_ROOT)).expanduser()
SUPPORTED_SUFFIXES = {".pdf"}
VALID_PURPOSES = {"claim", "substitute"}
VALID_STATUSES = {"available", "used", "archived"}


def now_iso() -> str:
    return dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def root() -> Path:
    return DATA_DIR


def db_path() -> Path:
    return root() / "state" / "invoices.sqlite"


def events_path() -> Path:
    return root() / "events" / "all.jsonl"


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


def ensure_dirs() -> None:
    for rel in [
        "config",
        "events",
        "files/pending",
        "files/available",
        "state",
    ]:
        (root() / rel).mkdir(parents=True, exist_ok=True)


def ensure_schema() -> None:
    ensure_dirs()
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS pending (
              id TEXT PRIMARY KEY,
              owner TEXT NOT NULL,
              source_id TEXT NOT NULL,
              source_path TEXT NOT NULL,
              imported_path TEXT NOT NULL,
              file_sha256 TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_sha
              ON pending(file_sha256);

            CREATE TABLE IF NOT EXISTS invoices (
              invoice_number TEXT PRIMARY KEY,
              owner TEXT NOT NULL,
              purpose TEXT NOT NULL,
              status TEXT NOT NULL,
              invoice_date TEXT NOT NULL,
              amount REAL NOT NULL,
              seller TEXT NOT NULL,
              purchase_content TEXT,
              tax_rate TEXT,
              currency TEXT NOT NULL DEFAULT 'CNY',
              source_id TEXT NOT NULL,
              source_path TEXT NOT NULL,
              imported_path TEXT NOT NULL,
              file_sha256 TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              used_reason TEXT,
              archived_reason TEXT
            );
            """
        )


def emit_event(event: str, payload: dict[str, Any]) -> None:
    events_path().parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": now_iso(), "event": event, **payload}
    with events_path().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def load_sources() -> dict[str, dict[str, Any]]:
    data = read_yaml(root() / "config" / "sources.yaml")
    sources = data.get("sources", {})
    if not isinstance(sources, dict):
        raise SystemExit("ERROR: config/sources.yaml must contain a mapping named 'sources'.")
    return sources


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_part(value: str, limit: int = 80) -> str:
    compact = re.sub(r"\s+", "", value.strip())
    compact = re.sub(r"[\\/:\*\?\"<>\|\x00-\x1f]", "_", compact)
    return compact[:limit] or "unknown"


def pending_path(pending_id: str, original: Path) -> Path:
    return root() / "files" / "pending" / f"{pending_id}{original.suffix.lower()}"


def final_path(fields: dict[str, Any], owner: str, original: Path) -> Path:
    name = "_".join(
        [
            safe_part(str(fields["invoice_date"])),
            safe_part(str(fields["invoice_number"])),
            safe_part(owner),
            safe_part(str(fields["seller"])),
        ]
    )
    return root() / "files" / "available" / f"{name}{original.suffix.lower()}"


def is_supported_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES


def already_imported(conn: sqlite3.Connection, sha: str) -> bool:
    pending = conn.execute("SELECT 1 FROM pending WHERE file_sha256 = ?", (sha,)).fetchone()
    if pending:
        return True
    invoice = conn.execute("SELECT 1 FROM invoices WHERE file_sha256 = ?", (sha,)).fetchone()
    return invoice is not None


def import_file(file_path: Path, owner: str, source_id: str, source_path: str) -> dict[str, Any]:
    ensure_schema()
    if not is_supported_file(file_path):
        raise SystemExit(f"ERROR: unsupported invoice file type: {file_path}")
    file_sha = sha256_file(file_path)
    with connect() as conn:
        if already_imported(conn, file_sha):
            return {"status": "duplicate", "source_path": str(file_path), "sha256": file_sha}
        pending_id = uuid.uuid4().hex[:12]
        dest = pending_path(pending_id, file_path)
        shutil.copy2(file_path, dest)
        conn.execute(
            """
            INSERT INTO pending
              (id, owner, source_id, source_path, imported_path, file_sha256, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (pending_id, owner, source_id, source_path, str(dest), file_sha, now_iso()),
        )
    emit_event(
        "pending_created",
        {
            "id": pending_id,
            "owner": owner,
            "source_id": source_id,
            "source_path": source_path,
            "imported_path": str(dest),
            "sha256": file_sha,
        },
    )
    return {"status": "imported", "id": pending_id, "owner": owner, "source_id": source_id, "file": str(dest)}


def cmd_init(args: argparse.Namespace) -> int:
    print(f"invoice data dir: {root()}")
    if args.dry_run:
        print("dry run: no files written; rerun with --apply")
        return 0
    ensure_schema()
    sources_file = root() / "config" / "sources.yaml"
    owners_file = root() / "config" / "owners.yaml"
    if not sources_file.exists():
        sources_file.write_text(
            """sources:
  example_source:
    kind: local_dir
    path: ~/path/to/invoice/inbox
    owner: Example Owner
""",
            encoding="utf-8",
        )
    if not owners_file.exists():
        owners_file.write_text(
            """owners:
  Example Owner:
    substitute_rule: ""
""",
            encoding="utf-8",
        )
    print("initialized")
    print(f"- {sources_file}")
    print(f"- {owners_file}")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    ensure_schema()
    sources = load_sources()
    if args.source:
        if args.source not in sources:
            raise SystemExit(f"ERROR: source '{args.source}' not found in config/sources.yaml.")
        sources = {args.source: sources[args.source]}

    imported = 0
    duplicates = 0
    missing = 0
    for source_id, cfg in sources.items():
        if cfg.get("kind", "local_dir") != "local_dir":
            print(f"skip {source_id}: unsupported kind {cfg.get('kind')}")
            continue
        owner = cfg.get("owner")
        raw_path = cfg.get("path")
        if not owner or not raw_path:
            print(f"skip {source_id}: missing owner or path")
            continue
        directory = expand_path(str(raw_path))
        if not directory.is_dir():
            print(f"missing {source_id}: {directory}")
            missing += 1
            continue
        for file_path in sorted(directory.rglob("*")):
            if args.limit is not None and imported >= args.limit:
                break
            if not is_supported_file(file_path):
                continue
            result = import_file(file_path, str(owner), source_id, str(file_path))
            if result["status"] == "imported":
                imported += 1
                print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            else:
                duplicates += 1
        if args.limit is not None and imported >= args.limit:
            break
    print(json.dumps({"imported": imported, "duplicates": duplicates, "missing_sources": missing}, ensure_ascii=False))
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    result = import_file(expand_path(args.file), args.owner, args.source_id, str(expand_path(args.file)))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_pending(args: argparse.Namespace) -> int:
    ensure_schema()
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, owner, source_id, source_path, imported_path, created_at FROM pending ORDER BY created_at"
        ).fetchall()
    for row in rows:
        print(json.dumps(dict(row), ensure_ascii=False, sort_keys=True))
    if not rows:
        print("no pending invoices")
    return 0


def require_fields(fields: dict[str, Any]) -> None:
    required = ["invoice_number", "invoice_date", "amount", "seller"]
    missing = [name for name in required if fields.get(name) in (None, "")]
    if missing:
        raise SystemExit(f"ERROR: missing required fields: {', '.join(missing)}")
    try:
        dt.date.fromisoformat(str(fields["invoice_date"]))
    except ValueError as exc:
        raise SystemExit("ERROR: invoice_date must be YYYY-MM-DD.") from exc
    try:
        float(fields["amount"])
    except (TypeError, ValueError) as exc:
        raise SystemExit("ERROR: amount must be numeric.") from exc


def cmd_submit(args: argparse.Namespace) -> int:
    ensure_schema()
    if args.purpose not in VALID_PURPOSES:
        raise SystemExit("ERROR: --purpose must be claim or substitute.")
    try:
        fields = json.loads(args.fields)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: --fields must be a JSON object: {exc}") from exc
    if not isinstance(fields, dict):
        raise SystemExit("ERROR: --fields must be a JSON object.")
    require_fields(fields)
    invoice_number = str(fields["invoice_number"])
    ts = now_iso()
    with connect() as conn:
        pending = conn.execute("SELECT * FROM pending WHERE id = ?", (args.id,)).fetchone()
        if not pending:
            raise SystemExit(f"ERROR: pending id '{args.id}' not found.")
        existing = conn.execute("SELECT 1 FROM invoices WHERE invoice_number = ?", (invoice_number,)).fetchone()
        if existing:
            raise SystemExit(f"ERROR: duplicate invoice_number '{invoice_number}'.")
        imported = Path(str(pending["imported_path"]))
        dest = final_path(fields, str(pending["owner"]), imported)
        if dest.exists():
            stem = dest.stem
            dest = dest.with_name(f"{stem}_{args.id}{dest.suffix}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(imported), dest)
        conn.execute(
            """
            INSERT INTO invoices
              (invoice_number, owner, purpose, status, invoice_date, amount, seller,
               purchase_content, tax_rate, currency, source_id, source_path, imported_path,
               file_sha256, created_at, updated_at)
            VALUES (?, ?, ?, 'available', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_number,
                pending["owner"],
                args.purpose,
                str(fields["invoice_date"]),
                float(fields["amount"]),
                str(fields["seller"]),
                fields.get("purchase_content"),
                fields.get("tax_rate"),
                str(fields.get("currency") or "CNY"),
                pending["source_id"],
                pending["source_path"],
                str(dest),
                pending["file_sha256"],
                ts,
                ts,
            ),
        )
        conn.execute("DELETE FROM pending WHERE id = ?", (args.id,))
    emit_event(
        "invoice_submitted",
        {
            "id": args.id,
            "invoice_number": invoice_number,
            "owner": str(pending["owner"]),
            "purpose": args.purpose,
            "imported_path": str(dest),
        },
    )
    print(json.dumps({"status": "submitted", "invoice_number": invoice_number, "file": str(dest)}, ensure_ascii=False))
    return 0


def cmd_discard(args: argparse.Namespace) -> int:
    ensure_schema()
    with connect() as conn:
        pending = conn.execute("SELECT * FROM pending WHERE id = ?", (args.id,)).fetchone()
        if not pending:
            raise SystemExit(f"ERROR: pending id '{args.id}' not found.")
        imported = Path(str(pending["imported_path"]))
        if imported.exists():
            imported.unlink()
        conn.execute("DELETE FROM pending WHERE id = ?", (args.id,))
    emit_event(
        "pending_discarded",
        {
            "id": args.id,
            "owner": str(pending["owner"]),
            "source_id": str(pending["source_id"]),
            "source_path": str(pending["source_path"]),
            "imported_path": str(pending["imported_path"]),
            "reason": args.reason,
        },
    )
    print(json.dumps({"status": "discarded", "id": args.id, "reason": args.reason}, ensure_ascii=False))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    ensure_schema()
    clauses: list[str] = []
    params: list[Any] = []
    if args.owner:
        clauses.append("owner = ?")
        params.append(args.owner)
    if args.purpose:
        clauses.append("purpose = ?")
        params.append(args.purpose)
    if args.status and args.status != "all":
        clauses.append("status = ?")
        params.append(args.status)
    if not args.include_archived:
        clauses.append("status != 'archived'")
    if args.since:
        clauses.append("invoice_date >= ?")
        params.append(args.since)
    if args.until:
        clauses.append("invoice_date <= ?")
        params.append(args.until)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT invoice_number, owner, purpose, status, invoice_date, amount, currency, seller, imported_path
        FROM invoices
        {where}
        ORDER BY invoice_date DESC, created_at DESC
    """
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    for row in rows:
        print(json.dumps(dict(row), ensure_ascii=False, sort_keys=True))
    if not rows:
        print("no invoices")
    return 0


def update_status(invoice_number: str, status: str, reason_field: str, reason: str | None) -> None:
    ensure_schema()
    if status not in VALID_STATUSES:
        raise SystemExit(f"ERROR: invalid status {status}")
    with connect() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE invoice_number = ?", (invoice_number,)).fetchone()
        if not row:
            raise SystemExit(f"ERROR: invoice_number '{invoice_number}' not found.")
        conn.execute(
            f"UPDATE invoices SET status = ?, updated_at = ?, {reason_field} = ? WHERE invoice_number = ?",
            (status, now_iso(), reason, invoice_number),
        )
    emit_event(
        f"invoice_{status}",
        {"invoice_number": invoice_number, "reason": reason or ""},
    )
    print(json.dumps({"status": status, "invoice_number": invoice_number}, ensure_ascii=False))


def cmd_mark_used(args: argparse.Namespace) -> int:
    update_status(args.invoice_number, "used", "used_reason", args.reason)
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    update_status(args.invoice_number, "archived", "archived_reason", args.reason)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ensure_schema()
    with connect() as conn:
        pending_count = conn.execute("SELECT COUNT(*) FROM pending").fetchone()[0]
        by_status = conn.execute("SELECT status, COUNT(*) AS n FROM invoices GROUP BY status").fetchall()
        by_purpose = conn.execute("SELECT purpose, COUNT(*) AS n FROM invoices GROUP BY purpose").fetchall()
    print(json.dumps(
        {
            "data_dir": str(root()),
            "pending": pending_count,
            "by_status": {row["status"]: row["n"] for row in by_status},
            "by_purpose": {row["purpose"]: row["n"] for row in by_purpose},
        },
        ensure_ascii=False,
        sort_keys=True,
    ))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage a unified invoice registry.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Create data directories and config templates.")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("scan", help="Scan configured local sources.")
    p.add_argument("--source")
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("add", help="Manually copy one file into pending.")
    p.add_argument("file")
    p.add_argument("--owner", required=True)
    p.add_argument("--source-id", default="manual")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("pending", help="List pending invoices.")
    p.set_defaults(func=cmd_pending)

    p = sub.add_parser("submit", help="Finalize pending invoice fields.")
    p.add_argument("--id", required=True)
    p.add_argument("--fields", required=True)
    p.add_argument("--purpose", required=True)
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("discard", help="Discard one pending invoice.")
    p.add_argument("--id", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_discard)

    p = sub.add_parser("list", help="List registered invoices.")
    p.add_argument("--owner")
    p.add_argument("--purpose")
    p.add_argument("--status", default="available")
    p.add_argument("--since")
    p.add_argument("--until")
    p.add_argument("--include-archived", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("mark-used", help="Mark invoice as used.")
    p.add_argument("--invoice-number", required=True)
    p.add_argument("--reason")
    p.set_defaults(func=cmd_mark_used)

    p = sub.add_parser("archive", help="Archive invoice.")
    p.add_argument("--invoice-number", required=True)
    p.add_argument("--reason")
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser("status", help="Report counts.")
    p.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
