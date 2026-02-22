#!/usr/bin/env python3
"""Close a discussion session and clean up associated tmux sessions.

Writes a session_close event to the JSONL log, kills each agent's tmux session
(unless --keep-tmux), and marks the session as closed in meta.json.
Idempotent: re-running on an already-closed session is safe.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any

from common import append_jsonl, load_meta, meta_locked, next_index, session_paths, utc_now


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Close a discussion session and clean up tmux sessions."
    )
    parser.add_argument(
        "--memory-root",
        default=".memory",
        help="Memory root directory. Default: .memory",
    )
    parser.add_argument("--session-id", required=True, help="Session id to close")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )
    parser.add_argument(
        "--keep-tmux",
        action="store_true",
        help="Update session status but do not kill tmux sessions",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-close an already-closed session and re-kill its tmux sessions",
    )
    return parser


def _kill_tmux(session_name: str) -> dict[str, Any]:
    """Kill one tmux session. Returns a result dict."""
    try:
        result = subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return {"session": session_name, "action": "killed", "ok": True}
        return {"session": session_name, "action": "not_found", "ok": True}
    except FileNotFoundError:
        return {"session": session_name, "action": "tmux_not_available", "ok": False}


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Close session and optionally kill tmux sessions."""
    paths = session_paths(args.memory_root, args.session_id)
    meta = load_meta(paths["meta"])

    already_closed = meta.get("status") == "closed"
    if already_closed and not args.force:
        return {
            "ok": True,
            "session_id": args.session_id,
            "skipped": True,
            "reason": "already_closed (use --force to re-close)",
        }

    # Collect tmux sessions from meta.agents
    agents = meta.get("agents", {})
    tmux_sessions: dict[str, str] = {
        name: info["tmux_session"]
        for name, info in agents.items()
        if info.get("transport") == "tmux" and info.get("tmux_session")
    }

    if args.dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "session_id": args.session_id,
            "status": meta.get("status"),
            "would_write_session_close": True,
            "would_kill_tmux": list(tmux_sessions.values()),
        }

    # Write session_close event
    idx = next_index(paths["jsonl"])
    event = {
        "index": idx,
        "timestamp": utc_now(),
        "session_id": args.session_id,
        "topic": meta.get("topic", ""),
        "role": "system",
        "speaker": "system",
        "message_type": "session_close",
        "message": (
            f"Session closed. Terminating {len(tmux_sessions)} tmux session(s): "
            + ", ".join(tmux_sessions.keys())
            if tmux_sessions
            else "Session closed. No tmux sessions to terminate."
        ),
        "reply_to_index": None,
        "tags": ["session", "close"],
        "extra": {"agents": list(tmux_sessions.keys()), "keep_tmux": args.keep_tmux},
    }
    append_jsonl(paths["jsonl"], event)

    # Kill tmux sessions
    kill_results: dict[str, Any] = {}
    if not args.keep_tmux:
        for agent_name, tmux_name in tmux_sessions.items():
            kill_results[agent_name] = _kill_tmux(tmux_name)

    # Update meta.json (locked)
    with meta_locked(paths["meta"]) as m:
        m["status"] = "closed"
        m["closed_at"] = utc_now()
        for agent_name in tmux_sessions:
            if agent_name in m.get("agents", {}):
                m["agents"][agent_name]["state"] = "terminated"

    return {
        "ok": True,
        "session_id": args.session_id,
        "closed": True,
        "tmux_killed": kill_results,
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
