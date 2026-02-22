#!/usr/bin/env python3
"""Append one user/agent message into a discussion session JSONL."""

from __future__ import annotations

import argparse
import json
from typing import Any

from common import (
    append_jsonl,
    load_meta,
    next_index,
    parse_csv,
    session_paths,
    utc_now,
)

ALLOWED_ROLES = {"user", "agent", "system"}
ALLOWED_MESSAGE_TYPES = {
    "kickoff",
    "context",
    "comment",
    "proposal",
    "objection",
    "support",
    "question",
    "summary",
    "decision",
    "action",
    "heartbeat",
    "error",
    "session_close",
}


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Append one message to a vibe discussion session."
    )
    parser.add_argument(
        "--memory-root",
        default=".memory",
        help="Memory root directory. Default: .memory",
    )
    parser.add_argument("--session-id", required=True, help="Session id")
    parser.add_argument(
        "--speaker", required=True, help="Speaker identity, e.g. codex or claude-code"
    )
    parser.add_argument(
        "--role", required=True, choices=sorted(ALLOWED_ROLES), help="Message role"
    )
    parser.add_argument("--message", required=True, help="Message content")
    parser.add_argument(
        "--message-type",
        default="comment",
        help="Message type, e.g. comment/proposal/decision",
    )
    parser.add_argument("--round", type=int, default=-1, help="Round number (optional)")
    parser.add_argument(
        "--reply-to-index", type=int, default=-1, help="Optional reply index"
    )
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument(
        "--extra-json", default="", help="Additional metadata as JSON object"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if message_type is invalid (default: warn)",
    )
    return parser


def _parse_extra(extra_json: str) -> dict[str, Any]:
    """Parse extra json object argument."""
    if not extra_json.strip():
        return {}
    parsed = json.loads(extra_json)
    if not isinstance(parsed, dict):
        raise ValueError("--extra-json must be a JSON object")
    return parsed


def _validate_message_type(message_type: str, strict: bool) -> str:
    """Validate message type and return normalized value."""
    normalized = message_type.strip() or "comment"
    if normalized not in ALLOWED_MESSAGE_TYPES:
        msg = f"Warning: message_type '{normalized}' not in allowed types: {ALLOWED_MESSAGE_TYPES}"
        if strict:
            raise ValueError(msg)
        # In non-strict mode, we allow it but still print warning
        import sys

        print(msg, file=sys.stderr)
    return normalized


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Append one message event and return summary."""
    paths = session_paths(args.memory_root, args.session_id)
    meta = load_meta(paths["meta"])
    if not paths["jsonl"].exists():
        raise ValueError(f"session file not found: {paths['jsonl']}")

    idx = next_index(paths["jsonl"])
    reply_to_index = args.reply_to_index if args.reply_to_index >= 0 else None
    tags = parse_csv(args.tags)
    extra = _parse_extra(args.extra_json)
    message_type = _validate_message_type(args.message_type, args.strict)

    # Add round info to extra if provided
    if args.round >= 0:
        extra["round"] = args.round

    event = {
        "index": idx,
        "timestamp": utc_now(),
        "session_id": args.session_id,
        "topic": meta.get("topic", ""),
        "role": args.role,
        "speaker": args.speaker.strip(),
        "message_type": message_type,
        "message": args.message,
        "reply_to_index": reply_to_index,
        "tags": tags,
        "extra": extra,
    }
    append_jsonl(paths["jsonl"], event)
    return {"ok": True, "session_id": args.session_id, "index": idx}


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
