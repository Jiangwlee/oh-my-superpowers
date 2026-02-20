#!/usr/bin/env python3
"""Read incremental updates from a discussion session JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import load_meta, read_jsonl, session_paths


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="Read incremental updates from session JSONL.")
    parser.add_argument("--memory-root", default=".memory", help="Memory root directory. Default: .memory")
    parser.add_argument("--session-id", required=True, help="Session id")
    parser.add_argument("--since-index", type=int, default=-1, help="Read events with index > since-index")
    parser.add_argument("--consumer", default="", help="Consumer name to load/save cursor, e.g. codex")
    parser.add_argument("--save-cursor", action="store_true", help="Persist new cursor index for consumer")
    parser.add_argument("--speaker", default="", help="Filter by speaker")
    parser.add_argument("--role", default="", help="Filter by role")
    parser.add_argument("--message-type", default="", help="Filter by message_type")
    parser.add_argument("--limit", type=int, default=0, help="Max returned events, 0 means all")
    return parser


def _load_cursor(cursor_file: Path) -> int:
    """Load integer cursor from file."""
    if not cursor_file.exists():
        return -1
    text = cursor_file.read_text(encoding="utf-8").strip()
    if not text:
        return -1
    try:
        return int(text)
    except ValueError:
        return -1


def _save_cursor(cursor_file: Path, value: int) -> None:
    """Write cursor value."""
    cursor_file.parent.mkdir(parents=True, exist_ok=True)
    cursor_file.write_text(f"{value}\n", encoding="utf-8")


def _apply_filters(events: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    """Filter events by optional fields."""
    filtered = [evt for evt in events if isinstance(evt.get("index"), int) and int(evt["index"]) > args.since_index]
    if args.speaker:
        filtered = [evt for evt in filtered if evt.get("speaker") == args.speaker]
    if args.role:
        filtered = [evt for evt in filtered if evt.get("role") == args.role]
    if args.message_type:
        filtered = [evt for evt in filtered if evt.get("message_type") == args.message_type]
    if args.limit > 0:
        filtered = filtered[: args.limit]
    return filtered


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Read updates using either explicit index or consumer cursor."""
    paths = session_paths(args.memory_root, args.session_id)
    meta = load_meta(paths["meta"])
    if not paths["jsonl"].exists():
        raise ValueError(f"session file not found: {paths['jsonl']}")

    effective_since = args.since_index
    cursor_file = None
    if args.consumer:
        cursor_file = paths["cursors"] / f"{args.consumer}.cursor"
        if effective_since < 0:
            effective_since = _load_cursor(cursor_file)
    if effective_since < 0:
        effective_since = -1
    args.since_index = effective_since

    events = read_jsonl(paths["jsonl"])
    filtered = _apply_filters(events, args)
    latest_index = effective_since
    if filtered:
        latest_index = int(filtered[-1]["index"])

    if args.save_cursor and cursor_file is not None:
        _save_cursor(cursor_file, latest_index)

    return {
        "ok": True,
        "session_id": args.session_id,
        "topic": meta.get("topic", ""),
        "requested_since_index": effective_since,
        "returned_count": len(filtered),
        "latest_index": latest_index,
        "events": filtered,
    }


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = run(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
