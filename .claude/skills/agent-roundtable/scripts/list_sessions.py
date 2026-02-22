#!/usr/bin/env python3
"""List discussion sessions under memory root."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from common import ensure_layout


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="List vibe coding discussion sessions.")
    parser.add_argument("--memory-root", default=".memory", help="Memory root directory. Default: .memory")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of sessions")
    return parser


def _last_updated_ts(entry: Path) -> float:
    """Return last-update mtime of session.jsonl, falling back to meta.json then 0."""
    jsonl = entry / "session.jsonl"
    if jsonl.exists():
        return jsonl.stat().st_mtime
    meta = entry / "meta.json"
    if meta.exists():
        return meta.stat().st_mtime
    return 0.0


def _mtime_to_iso(mtime: float) -> str:
    """Convert mtime float to UTC ISO8601 string."""
    return dt.datetime.fromtimestamp(mtime, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(memory_root: str, limit: int) -> dict:
    """Enumerate sessions sorted by last update time (most recent first)."""
    layout = ensure_layout(memory_root)
    sessions_dir = layout["sessions"]
    candidates = []
    for entry in sessions_dir.iterdir():
        if not entry.is_dir():
            continue
        meta_path = entry / "meta.json"
        if not meta_path.exists():
            continue
        candidates.append((entry, _last_updated_ts(entry)))

    candidates.sort(key=lambda t: t[1], reverse=True)

    items = []
    for entry, last_mtime in candidates:
        meta_path = entry / "meta.json"
        jsonl_path = entry / "session.jsonl"
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        items.append(
            {
                "session_id": meta.get("session_id", entry.name),
                "topic": meta.get("topic", ""),
                "created_at": meta.get("created_at", ""),
                "last_updated_at": _mtime_to_iso(last_mtime),
                "participants": meta.get("participants", []),
                "has_log": jsonl_path.exists(),
            }
        )
        if limit > 0 and len(items) >= limit:
            break
    return {"ok": True, "count": len(items), "sessions": items}


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()
    result = run(args.memory_root, args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
