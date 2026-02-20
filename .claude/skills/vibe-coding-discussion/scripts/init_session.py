#!/usr/bin/env python3
"""Initialize one discussion session for a project topic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import append_jsonl, ensure_layout, parse_csv, session_paths, slugify_topic, utc_now


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="Initialize a vibe coding discussion session.")
    parser.add_argument("--memory-root", default=".memory", help="Memory root directory. Default: .memory")
    parser.add_argument("--topic", required=True, help="Discussion topic")
    parser.add_argument(
        "--participants",
        default="user,codex,claude-code,opencode",
        help="Comma-separated participant names",
    )
    parser.add_argument("--session-id", default="", help="Optional explicit session id")
    parser.add_argument("--background", default="", help="Inline background context")
    parser.add_argument("--background-file", default="", help="Path to background markdown/text")
    return parser


def _read_background(args: argparse.Namespace) -> str:
    """Load background from inline content or file."""
    if args.background:
        return args.background.strip()
    if args.background_file:
        return Path(args.background_file).expanduser().read_text(encoding="utf-8").strip()
    return ""


def _create_session_id(topic: str) -> str:
    """Build deterministic-ish session id from timestamp and topic."""
    ts = utc_now().replace("-", "").replace(":", "").replace("T", "-").replace("Z", "")
    return f"{ts}-{slugify_topic(topic)}"


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Create files and bootstrap first system event."""
    ensure_layout(args.memory_root)
    participants = parse_csv(args.participants)
    if "user" not in participants:
        participants.insert(0, "user")

    session_id = args.session_id.strip() or _create_session_id(args.topic)
    paths = session_paths(args.memory_root, session_id)
    if paths["root"].exists():
        raise ValueError(f"session already exists: {session_id}")

    paths["root"].mkdir(parents=True, exist_ok=False)
    paths["cursors"].mkdir(parents=True, exist_ok=True)

    background = _read_background(args)
    background_file_name = ""
    if background:
        background_file_name = "background.md"
        (paths["root"] / background_file_name).write_text(background.rstrip() + "\n", encoding="utf-8")

    meta = {
        "session_id": session_id,
        "topic": args.topic.strip(),
        "participants": participants,
        "created_at": utc_now(),
        "background": background,
        "background_file": background_file_name,
    }
    paths["meta"].write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    bootstrap_event = {
        "index": 0,
        "timestamp": utc_now(),
        "session_id": session_id,
        "topic": meta["topic"],
        "role": "system",
        "speaker": "system",
        "message_type": "session_open",
        "message": "Session initialized",
        "reply_to_index": None,
        "tags": ["session", "open"],
        "extra": {
            "participants": participants,
            "background_file": background_file_name,
            "background_preview": background[:500],
        },
    }
    append_jsonl(paths["jsonl"], bootstrap_event)

    return {
        "ok": True,
        "session_id": session_id,
        "session_dir": str(paths["root"]),
        "session_file": str(paths["jsonl"]),
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
