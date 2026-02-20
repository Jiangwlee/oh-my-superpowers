#!/usr/bin/env python3
"""List discussion sessions under memory root."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ensure_layout


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="List vibe coding discussion sessions.")
    parser.add_argument("--memory-root", default=".memory", help="Memory root directory. Default: .memory")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of sessions")
    return parser


def run(memory_root: str, limit: int) -> dict:
    """Enumerate sessions and return metadata summary."""
    layout = ensure_layout(memory_root)
    sessions_dir = layout["sessions"]
    items = []
    for entry in sorted(sessions_dir.iterdir(), key=lambda p: p.name, reverse=True):
        if not entry.is_dir():
            continue
        meta_path = entry / "meta.json"
        jsonl_path = entry / "session.jsonl"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        items.append(
            {
                "session_id": meta.get("session_id", entry.name),
                "topic": meta.get("topic", ""),
                "created_at": meta.get("created_at", ""),
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
