#!/usr/bin/env python3
"""Clean up stale tmux sessions left over from agent-roundtable discussions.

Scans all sessions under memory-root and kills any tmux sessions that are
still running but belong to a closed (or force-flagged open) discussion session.
Idempotent and safe to run repeatedly as a maintenance task.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from common import ensure_layout, load_meta, meta_locked, utc_now


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Clean up stale tmux sessions from all agent-roundtable sessions."
    )
    parser.add_argument(
        "--memory-root",
        default=".memory",
        help="Memory root directory. Default: .memory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be killed without executing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Also kill tmux sessions from open (not yet closed) discussion sessions",
    )
    parser.add_argument(
        "--session-id",
        default="",
        help="Limit cleanup to a specific session id (default: all sessions)",
    )
    return parser


def _tmux_exists(session_name: str) -> bool:
    """Return True if the tmux session is currently running."""
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _kill_tmux(session_name: str) -> bool:
    """Kill a tmux session. Returns True on success."""
    try:
        result = subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _scan_session(
    session_dir: Path, force: bool, dry_run: bool
) -> dict[str, Any] | None:
    """Scan one session directory and clean up stale tmux sessions.

    Returns a result dict if any stale tmux sessions were found, else None.
    """
    meta_path = session_dir / "meta.json"
    if not meta_path.exists():
        return None

    try:
        meta = load_meta(meta_path)
    except ValueError:
        return None

    session_id = meta.get("session_id", session_dir.name)
    status = meta.get("status", "open")
    agents = meta.get("agents", {})

    # Collect running tmux sessions for this discussion
    running: list[tuple[str, str]] = []
    for agent_name, info in agents.items():
        if info.get("transport") != "tmux":
            continue
        tmux_name = info.get("tmux_session")
        if tmux_name and _tmux_exists(tmux_name):
            running.append((agent_name, tmux_name))

    if not running:
        return None

    is_stale = (status == "closed") or force
    result: dict[str, Any] = {
        "session_id": session_id,
        "status": status,
        "running_tmux": [t for _, t in running],
        "action": "skipped_open",
    }

    if not is_stale:
        return result

    if dry_run:
        result["action"] = "would_kill"
        return result

    killed: list[str] = []
    for agent_name, tmux_name in running:
        if _kill_tmux(tmux_name):
            killed.append(tmux_name)
            with meta_locked(meta_path) as m:
                a = m.get("agents", {}).get(agent_name)
                if a:
                    a["state"] = "terminated"
                    a["terminated_at"] = utc_now()

    result["action"] = "killed"
    result["killed"] = killed
    return result


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Scan all (or one) session(s) and clean up stale tmux sessions."""
    layout = ensure_layout(args.memory_root)
    sessions_dir = layout["sessions"]

    scanned: list[dict[str, Any]] = []

    if args.session_id:
        # Single-session mode
        target = sessions_dir / args.session_id
        if not target.is_dir():
            return {"ok": False, "error": f"session not found: {args.session_id}"}
        r = _scan_session(target, args.force, args.dry_run)
        if r:
            scanned.append(r)
    else:
        for entry in sorted(sessions_dir.iterdir()):
            if not entry.is_dir():
                continue
            r = _scan_session(entry, args.force, args.dry_run)
            if r:
                scanned.append(r)

    killed_count = sum(
        len(r.get("killed", [])) for r in scanned if r.get("action") == "killed"
    )
    would_kill_count = sum(
        len(r.get("running_tmux", [])) for r in scanned if r.get("action") == "would_kill"
    )

    return {
        "ok": True,
        "dry_run": args.dry_run,
        "sessions_with_stale_tmux": len(scanned),
        "killed": killed_count,
        "would_kill": would_kill_count,
        "details": scanned,
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
