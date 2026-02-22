#!/usr/bin/env python3
"""Read incremental updates from a discussion session JSONL."""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
from typing import Any

from common import load_meta, read_jsonl, session_paths


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Read incremental updates from session JSONL."
    )
    parser.add_argument(
        "--memory-root",
        default=".memory",
        help="Memory root directory. Default: .memory",
    )
    parser.add_argument("--session-id", required=True, help="Session id")
    parser.add_argument(
        "--since-index",
        type=int,
        default=-1,
        help="Read events with index > since-index",
    )
    parser.add_argument(
        "--consumer", default="", help="Consumer name to load/save cursor, e.g. codex"
    )
    parser.add_argument(
        "--save-cursor",
        action="store_true",
        help="Persist new cursor index for consumer",
    )
    parser.add_argument("--speaker", default="", help="Filter by speaker")
    parser.add_argument("--role", default="", help="Filter by role")
    parser.add_argument("--message-type", default="", help="Filter by message_type")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max returned events, 0 means all (deprecated, use --max-events)",
    )
    parser.add_argument(
        "--max-events", type=int, default=0, help="Max returned events, 0 means all"
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=0,
        help="Alias of --max-events (one JSONL line per event)",
    )
    parser.add_argument(
        "--json-cursor",
        action="store_true",
        help="Use JSON format for cursor (includes last_read_at)",
    )
    return parser


def _load_cursor(cursor_file: Path, use_json: bool = False) -> dict[str, Any]:
    """Load cursor from file. Returns dict with last_index and optional fields."""
    if not cursor_file.exists():
        return {"last_index": -1}
    text = cursor_file.read_text(encoding="utf-8").strip()
    if not text:
        return {"last_index": -1}

    # Try JSON format first
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "last_index" in data:
            return data
    except json.JSONDecodeError:
        pass

    # Fallback to plain integer format
    try:
        return {"last_index": int(text)}
    except ValueError:
        return {"last_index": -1}


def _save_cursor(
    cursor_file: Path, data: dict[str, Any], use_json: bool = False
) -> None:
    """Write cursor value."""
    cursor_file.parent.mkdir(parents=True, exist_ok=True)
    if use_json:
        cursor_file.write_text(
            json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    else:
        # Backward compatible: just write the index
        cursor_file.write_text(f"{data.get('last_index', -1)}\n", encoding="utf-8")


def _apply_filters(
    events: list[dict[str, Any]], since_index: int, args: argparse.Namespace
) -> list[dict[str, Any]]:
    """Filter events by optional fields."""
    filtered = [
        evt
        for evt in events
        if isinstance(evt.get("index"), int) and int(evt["index"]) > since_index
    ]
    if args.speaker:
        filtered = [evt for evt in filtered if evt.get("speaker") == args.speaker]
    if args.role:
        filtered = [evt for evt in filtered if evt.get("role") == args.role]
    if args.message_type:
        filtered = [
            evt for evt in filtered if evt.get("message_type") == args.message_type
        ]
    # Use max-events if set, otherwise fall back to limit for backward compatibility
    max_events = (
        args.max_events
        if args.max_events > 0
        else (args.max_lines if args.max_lines > 0 else args.limit)
    )
    if max_events > 0:
        filtered = filtered[:max_events]
    return filtered


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Read updates using either explicit index or consumer cursor."""
    paths = session_paths(args.memory_root, args.session_id)
    meta = load_meta(paths["meta"])
    if not paths["jsonl"].exists():
        raise ValueError(f"session file not found: {paths['jsonl']}")

    effective_since = args.since_index
    cursor_data: dict[str, Any] = {"last_index": -1}
    cursor_file = None
    if args.consumer:
        cursor_file = paths["cursors"] / f"{args.consumer}.cursor"
        if effective_since < 0:
            cursor_data = _load_cursor(cursor_file, args.json_cursor)
            effective_since = cursor_data.get("last_index", -1)
    if effective_since < 0:
        effective_since = -1

    events = read_jsonl(paths["jsonl"])
    filtered = _apply_filters(events, effective_since, args)
    latest_index = effective_since
    if filtered:
        latest_index = int(filtered[-1]["index"])

    if args.save_cursor and cursor_file is not None:
        # Update cursor data
        cursor_data["last_index"] = latest_index
        cursor_data["last_read_at"] = (
            datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        _save_cursor(cursor_file, cursor_data, args.json_cursor)

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
