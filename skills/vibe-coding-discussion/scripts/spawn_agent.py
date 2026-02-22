#!/usr/bin/env python3
"""Spawn an agent in tmux session with initial prompt injection.

This script creates a tmux session for an agent, launches the CLI tool,
and injects an initial prompt that instructs the agent on how to
participate in the discussion.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from common import load_meta, session_paths, utc_now

SCRIPT_DIR = Path(__file__).resolve().parent

# Agent type to CLI command mapping
AGENT_COMMANDS: dict[str, dict[str, str]] = {
    "claude-code": {
        "cmd": "claude",
        "args": "--dangerously-skip-permissions",
    },
    "codex": {
        "cmd": "codex",
        "args": "--dangerously-bypass-approvals-and-sandbox",
    },
    "opencode": {
        "cmd": "opencode",
        "args": "",
    },
}


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Spawn an agent in tmux session for discussion."
    )
    parser.add_argument(
        "--memory-root",
        default=".memory",
        help="Memory root directory. Default: .memory",
    )
    parser.add_argument("--session-id", required=True, help="Session id")
    parser.add_argument("--agent", required=True, help="Agent name, e.g. codex-1")
    parser.add_argument(
        "--agent-type",
        required=True,
        choices=list(AGENT_COMMANDS.keys()),
        help="Agent type (determines CLI command)",
    )
    parser.add_argument(
        "--workdir",
        default=".",
        help="Working directory for the agent. Default: current directory",
    )
    parser.add_argument(
        "--extra-args",
        default="",
        help="Extra arguments to pass to the agent CLI",
    )
    parser.add_argument(
        "--wait-idle",
        action="store_true",
        help="Wait for agent to become idle before returning",
    )
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=60,
        help="Timeout in seconds for idle detection. Default: 60",
    )
    return parser


def get_tmux_session_name(session_id: str, agent: str) -> str:
    """Generate tmux session name."""
    # Sanitize for tmux session name (alphanumeric, dash, underscore only)
    safe_session = "".join(c if c.isalnum() or c in "-_" else "-" for c in session_id)
    safe_agent = "".join(c if c.isalnum() or c in "-_" else "-" for c in agent)
    return f"vcd_{safe_session}_{safe_agent}"[:64]  # tmux has limit


def tmux_session_exists(session_name: str) -> bool:
    """Check if tmux session exists."""
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        raise RuntimeError("tmux not found. Please install tmux.")


def create_tmux_session(session_name: str, workdir: str) -> None:
    """Create a new tmux session."""
    workdir_path = Path(workdir).resolve()
    subprocess.run(
        [
            "tmux",
            "new-session",
            "-d",  # detached
            "-s",
            session_name,
            "-c",
            str(workdir_path),
        ],
        check=True,
        capture_output=True,
    )


def get_agent_command(agent_type: str, extra_args: str = "") -> str:
    """Get the command to launch an agent."""
    config = AGENT_COMMANDS.get(agent_type)
    if not config:
        raise ValueError(f"Unknown agent type: {agent_type}")

    cmd = config["cmd"]
    args = config["args"]
    if extra_args:
        args = f"{args} {extra_args}".strip()

    return f"{cmd} {args}".strip()


def send_keys_to_tmux(session_name: str, keys: str) -> None:
    """Send keys to tmux session."""
    subprocess.run(
        ["tmux", "send-keys", "-t", session_name, keys],
        check=True,
        capture_output=True,
    )


def capture_pane(session_name: str) -> str:
    """Capture current pane content."""
    result = subprocess.run(
        ["tmux", "capture-pane", "-p", "-t", session_name],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def is_pane_idle(session_name: str, prompt_patterns: list[str] | None = None) -> bool:
    """Check if pane is idle (showing prompt)."""
    if prompt_patterns is None:
        # Default patterns for common CLI prompts
        prompt_patterns = [">>>", "$", ">", "#", "┌", "│", "└", "╭", "╰"]

    content = capture_pane(session_name)
    lines = content.strip().split("\n")
    if not lines:
        return False

    last_line = lines[-1].strip()
    # Check if last line ends with a prompt pattern
    for pattern in prompt_patterns:
        if last_line.endswith(pattern) or pattern in last_line:
            return True

    # Also check if there's been no output change in the last few lines
    # (simplistic heuristic)
    return len(last_line) < 100 and not last_line.startswith(" ")


def wait_for_idle(session_name: str, timeout: int = 60, interval: float = 0.5) -> bool:
    """Wait for pane to become idle."""
    start = time.time()
    while time.time() - start < timeout:
        if is_pane_idle(session_name):
            return True
        time.sleep(interval)
    return False


def send_interrupt(session_name: str) -> None:
    """Send Ctrl+C to interrupt current task."""
    subprocess.run(
        ["tmux", "send-keys", "-t", session_name, "C-c"],
        check=False,
        capture_output=True,
    )
    time.sleep(0.3)


def build_initial_prompt(
    session_id: str,
    agent: str,
    agent_type: str,
    memory_root: str,
) -> str:
    """Build initial prompt for agent."""
    paths = session_paths(memory_root, session_id)
    background_path = paths["root"] / "background.md"

    script_root = SCRIPT_DIR.as_posix()
    prompt = f"""# Vibe Coding Discussion - Agent Instructions

You are participating in a group discussion as agent "{agent}" (type: {agent_type}).

## Session Info
- Session ID: {session_id}
- Your role: Participate in the discussion, read context, and respond when prompted

## How to Participate

1. **Read Background** (if exists):
   The background document is at: {background_path}
   Run: `cat {background_path}` to read it.

2. **Read Discussion History**:
   Run this command to get updates:
   ```
   python3 {script_root}/read_updates.py \\
     --memory-root {memory_root} \\
     --session-id {session_id} \\
     --consumer {agent} \\
     --save-cursor
   ```

3. **Write Your Response**:
   When you have something to say, use:
   ```
   python3 {script_root}/append_message.py \\
     --memory-root {memory_root} \\
     --session-id {session_id} \\
     --speaker {agent} \\
     --role agent \\
     --message "Your message here" \\
     --message-type comment
   ```

   Message types: kickoff, context, comment, proposal, objection, support, question, summary, decision, action, heartbeat, error

4. **Wait for Instructions**:
   The orchestrator will prompt you when it's your turn to speak.

Press Enter to acknowledge and start participating.
"""
    return prompt


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Spawn agent in tmux session."""
    # Validate session exists
    paths = session_paths(args.memory_root, args.session_id)
    if not paths["jsonl"].exists():
        raise ValueError(f"session not found: {args.session_id}")

    session_name = get_tmux_session_name(args.session_id, args.agent)

    # Check if session already exists
    if tmux_session_exists(session_name):
        raise ValueError(f"tmux session already exists: {session_name}")

    # Create tmux session
    create_tmux_session(session_name, args.workdir)

    # Get agent command
    agent_cmd = get_agent_command(args.agent_type, args.extra_args)

    # Launch agent in tmux
    send_keys_to_tmux(session_name, agent_cmd)
    send_keys_to_tmux(session_name, "Enter")

    # Wait a bit for agent to start
    time.sleep(1.0)

    # Build and inject initial prompt
    initial_prompt = build_initial_prompt(
        args.session_id,
        args.agent,
        args.agent_type,
        args.memory_root,
    )

    # Send initial prompt
    send_keys_to_tmux(session_name, initial_prompt)
    send_keys_to_tmux(session_name, "Enter")

    # Wait for idle if requested
    idle_detected = False
    if args.wait_idle:
        idle_detected = wait_for_idle(session_name, args.idle_timeout)

    # Update meta.json with tmux session info
    meta = load_meta(paths["meta"])
    if "agents" not in meta:
        meta["agents"] = {}

    existing = meta["agents"].get(args.agent, {})
    meta["agents"][args.agent] = {
        "type": args.agent_type,
        "kind": args.agent_type,
        "transport": existing.get("transport", "tmux"),
        "tmux_session": session_name,
        "state": "idle" if idle_detected else "starting",
        "spawned_at": utc_now(),
    }

    paths["meta"].write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "ok": True,
        "session_id": args.session_id,
        "agent": args.agent,
        "agent_type": args.agent_type,
        "tmux_session": session_name,
        "state": "idle" if idle_detected else "starting",
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
