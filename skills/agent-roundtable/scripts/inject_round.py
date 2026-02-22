#!/usr/bin/env python3
"""Inject a round prompt into an agent's tmux session.

This script sends a prompt to a specific agent in a discussion session,
telling them it's their turn to speak and providing context about
what they should respond to.
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


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Inject a round prompt into an agent's tmux session."
    )
    parser.add_argument(
        "--memory-root",
        default=".memory",
        help="Memory root directory. Default: .memory",
    )
    parser.add_argument("--session-id", required=True, help="Session id")
    parser.add_argument("--agent", required=True, help="Agent name to inject prompt to")
    parser.add_argument("--round", type=int, required=True, help="Current round number")
    parser.add_argument(
        "--prompt", required=True, help="The prompt/instruction for this round"
    )
    parser.add_argument(
        "--max-wait",
        type=int,
        default=300,
        help="Max seconds to wait for agent to respond. Default: 300 (5 min)",
    )
    parser.add_argument(
        "--check-interval",
        type=float,
        default=2.0,
        help="Interval in seconds between checks. Default: 2.0",
    )
    parser.add_argument(
        "--send-interrupt",
        action="store_true",
        default=True,
        help="Send Ctrl+C before injecting (default: True)",
    )
    parser.add_argument(
        "--no-interrupt",
        action="store_true",
        help="Don't send Ctrl+C before injecting",
    )
    return parser


def get_tmux_session_name(session_id: str, agent: str) -> str:
    """Generate tmux session name."""
    safe_session = "".join(c if c.isalnum() or c in "-_" else "-" for c in session_id)
    safe_agent = "".join(c if c.isalnum() or c in "-_" else "-" for c in agent)
    return f"vcd_{safe_session}_{safe_agent}"[:64]


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
        prompt_patterns = [">>>", "$", ">", "#", "┌", "│", "└", "╭", "╰"]

    content = capture_pane(session_name)
    lines = content.strip().split("\n")
    if not lines:
        return False

    last_line = lines[-1].strip()
    for pattern in prompt_patterns:
        if last_line.endswith(pattern) or pattern in last_line:
            return True

    return len(last_line) < 100 and not last_line.startswith(" ")


def wait_for_idle(session_name: str, timeout: int = 60, interval: float = 0.5) -> bool:
    """Wait for pane to become idle."""
    start = time.time()
    while time.time() - start < timeout:
        if is_pane_idle(session_name):
            return True
        time.sleep(interval)
    return False


def send_keys_to_tmux(session_name: str, keys: str) -> None:
    """Send keys to tmux session."""
    subprocess.run(
        ["tmux", "send-keys", "-t", session_name, keys],
        check=True,
        capture_output=True,
    )


def send_interrupt(session_name: str) -> None:
    """Send Ctrl+C to interrupt current task."""
    subprocess.run(
        ["tmux", "send-keys", "-t", session_name, "C-c"],
        check=False,
        capture_output=True,
    )
    time.sleep(0.3)


def build_round_prompt(
    round_num: int,
    prompt: str,
    session_id: str,
    agent: str,
    memory_root: str,
) -> str:
    """Build the round prompt with instructions."""
    # Get read_updates command
    script_root = SCRIPT_DIR.as_posix()
    read_cmd = (
        f"python3 {script_root}/read_updates.py "
        f"--memory-root {memory_root} --session-id {session_id} "
        f"--consumer {agent} --save-cursor"
    )

    # Get append_message command template
    append_cmd = (
        f"python3 {script_root}/append_message.py "
        f"--memory-root {memory_root} --session-id {session_id} "
        f"--speaker {agent} --role agent --round {round_num} "
        f'--message "YOUR_MESSAGE_HERE"'
    )

    full_prompt = f"""
╔══════════════════════════════════════════════════════════════════╗
║  ROUND {round_num} - Your Turn to Speak                                          ║
╚══════════════════════════════════════════════════════════════════╝

{prompt}

---

## Instructions:

1. First, read any new messages:
   {read_cmd}

2. Then, compose your response and send it:
   {append_cmd} --message-type comment

   For proposals use: --message-type proposal
   For objections use: --message-type objection
   For questions use: --message-type question
   For final decisions use: --message-type decision

3. Wait for the next round prompt.

Press Enter to acknowledge and start your response.
"""
    return full_prompt


def count_messages_since(
    jsonl_path: Path, since_index: int, speaker: str | None = None
) -> int:
    """Count messages in JSONL since a given index."""
    if not jsonl_path.exists():
        return 0

    count = 0
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                idx = obj.get("index")
                if isinstance(idx, int) and idx > since_index:
                    if speaker is None or obj.get("speaker") == speaker:
                        count += 1
        except json.JSONDecodeError:
            continue
    return count


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Inject round prompt into agent's tmux session."""
    paths = session_paths(args.memory_root, args.session_id)

    # Load meta to get agent info
    meta = load_meta(paths["meta"])
    agents = meta.get("agents", {})

    if args.agent not in agents:
        raise ValueError(f"agent not found in session: {args.agent}")

    agent_info = agents[args.agent]
    session_name = agent_info.get("tmux_session")

    if not session_name:
        raise ValueError(f"agent {args.agent} has no tmux session")

    if not tmux_session_exists(session_name):
        raise ValueError(f"tmux session does not exist: {session_name}")

    # Check session status
    status = meta.get("status", "open")
    if status == "closed":
        raise ValueError("session is closed, cannot inject")

    # Get message count before injection
    msg_count_before = count_messages_since(paths["jsonl"], -1, args.agent)

    # Wait for idle if needed
    if not is_pane_idle(session_name):
        if not args.no_interrupt:
            send_interrupt(session_name)
            time.sleep(0.5)

        # Wait for idle (shorter timeout, just to ensure we're at a prompt)
        if not wait_for_idle(session_name, timeout=10):
            # If not idle after interrupt, proceed anyway with warning
            pass

    # Build and send round prompt
    full_prompt = build_round_prompt(
        args.round,
        args.prompt,
        args.session_id,
        args.agent,
        args.memory_root,
    )

    send_keys_to_tmux(session_name, full_prompt)
    send_keys_to_tmux(session_name, "Enter")

    # Update agent state
    agent_info["state"] = "responding"
    agent_info["last_prompted_at"] = utc_now()
    agent_info["round"] = args.round

    meta["agents"] = agents
    paths["meta"].write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Wait for response if max_wait > 0
    responded = False
    if args.max_wait > 0:
        start = time.time()
        while time.time() - start < args.max_wait:
            time.sleep(args.check_interval)
            msg_count_after = count_messages_since(paths["jsonl"], -1, args.agent)
            if msg_count_after > msg_count_before:
                responded = True
                # Update agent state
                agent_info["state"] = "idle"
                agent_info["last_response_at"] = utc_now()
                meta["agents"] = agents
                paths["meta"].write_text(
                    json.dumps(meta, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                break

    return {
        "ok": True,
        "session_id": args.session_id,
        "agent": args.agent,
        "round": args.round,
        "injected": True,
        "responded": responded,
        "tmux_session": session_name,
    }


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    # Handle --no-interrupt flag
    if args.no_interrupt:
        args.send_interrupt = False

    try:
        result = run(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
