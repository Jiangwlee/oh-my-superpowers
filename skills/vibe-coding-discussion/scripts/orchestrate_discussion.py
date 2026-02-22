#!/usr/bin/env python3
"""Orchestrate a self-organizing discussion among multiple agents.

This is the main controller that:
1. Initializes or resumes a discussion session
2. Manages discussion rounds
3. Spawns agents in tmux sessions
4. Injects prompts to agents in sequence
5. Detects convergence conditions
6. Closes the session with a summary
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from common import append_jsonl, load_meta, next_index, read_jsonl, session_paths, utc_now

SCRIPT_DIR = Path(__file__).resolve().parent

# Convergence detection settings
MAX_NO_OBJECTION_ROUNDS = 2  # Converge if no objections for this many rounds
DEFAULT_MAX_ROUNDS = 10


def script_path(name: str) -> str:
    """Return absolute path to a sibling script."""
    return str((SCRIPT_DIR / name).resolve())


def tmux_session_exists(session_name: str) -> bool:
    """Best-effort check whether a tmux session exists."""
    if not session_name:
        return False
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def workspace_root() -> Path:
    """Best-effort workspace root (current working directory)."""
    return Path.cwd().resolve()


def _attachment_entry(path: Path, category: str, required: bool = True) -> dict[str, Any]:
    """Build one attachment manifest entry."""
    return {
        "path": path.as_posix(),
        "title": path.name,
        "category": category,
        "required": required,
    }


def write_attachments_manifest(memory_root: str, session_id: str) -> Path:
    """Generate or refresh attachments.json for the session.

    Current strategy:
    - Include session-local background.md if present
    - Include local docs/vibe-coding-discussion/*.md if present
    """
    paths = session_paths(memory_root, session_id)
    root = paths["root"]
    manifest_path = root / "attachments.json"
    items: list[dict[str, Any]] = []

    background_path = root / "background.md"
    if background_path.exists():
        # Store session-relative path to keep session portable
        items.append(
            {
                "path": "background.md",
                "title": "Discussion Background",
                "category": "background",
                "required": True,
            }
        )

    docs_dir = workspace_root() / "docs" / "vibe-coding-discussion"
    if docs_dir.exists():
        for doc in sorted(docs_dir.glob("*.md")):
            items.append(_attachment_entry(doc.relative_to(workspace_root()), "research", True))

    payload = {
        "generated_at": utc_now(),
        "session_id": session_id,
        "attachments": items,
    }
    manifest_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    meta = load_meta(paths["meta"])
    meta.setdefault("attachments", {})
    meta["attachments"]["manifest_path"] = "attachments.json"
    if background_path.exists():
        meta["attachments"]["background_path"] = "background.md"
    paths["meta"].write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest_path


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Orchestrate a self-organizing discussion session."
    )
    parser.add_argument(
        "--memory-root",
        default=".memory",
        help="Memory root directory. Default: .memory",
    )
    parser.add_argument(
        "--session-id",
        default="",
        help="Session id (optional, will create new if not provided)",
    )
    parser.add_argument(
        "--topic",
        default="",
        help="Discussion topic (required for new session)",
    )
    parser.add_argument(
        "--background-file",
        default="",
        help="Path to background markdown file",
    )
    parser.add_argument(
        "--agents",
        default="",
        help='Comma-separated agent specs: "name:type,name2:type2" (e.g. "codex:codex,opencode:opencode")',
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=DEFAULT_MAX_ROUNDS,
        help=f"Maximum number of rounds. Default: {DEFAULT_MAX_ROUNDS}",
    )
    parser.add_argument(
        "--round-timeout",
        type=int,
        default=300,
        help="Timeout per round in seconds. Default: 300 (5 min)",
    )
    parser.add_argument(
        "--auto-close",
        action="store_true",
        default=True,
        help="Auto close session when converged (default: True)",
    )
    parser.add_argument(
        "--no-auto-close",
        action="store_true",
        help="Don't auto close session when converged",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )
    parser.add_argument(
        "--skip-spawn",
        action="store_true",
        help="Resume mode: do not spawn any agents, only continue orchestration",
    )
    parser.add_argument(
        "--mode",
        choices=["sequential", "parallel"],
        default="sequential",
        help="Discussion mode: sequential (round-robin) or parallel. Default: sequential",
    )
    return parser


def run_subprocess(
    cmd: list[str],
    timeout: int = 60,
    capture: bool = True,
) -> tuple[bool, str]:
    """Run a subprocess and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as exc:
        return False, str(exc)


def init_session(
    memory_root: str,
    topic: str,
    background_file: str = "",
    agents: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Initialize a new discussion session."""
    cmd = [
        sys.executable,
        script_path("init_session.py"),
        "--memory-root",
        memory_root,
        "--topic",
        topic,
    ]
    if background_file:
        cmd.extend(["--background-file", background_file])

    success, output = run_subprocess(cmd, timeout=30)
    if not success:
        raise RuntimeError(f"Failed to initialize session: {output}")

    result = json.loads(output)
    session_id = result["session_id"]

    # Add agents to meta
    if agents:
        update_session_agents(memory_root, session_id, agents)

    return result


def update_session_agents(
    memory_root: str, session_id: str, agents: dict[str, str]
) -> None:
    """Update session meta with agent configurations."""
    paths = session_paths(memory_root, session_id)
    meta = load_meta(paths["meta"])

    if "agents" not in meta:
        meta["agents"] = {}

    # Add agent configs
    for agent_name, agent_type in agents.items():
        if agent_name not in meta["agents"]:
            transport = "self" if agent_type == "claude-code" else "tmux"
            meta["agents"][agent_name] = {
                "type": agent_type,
                "kind": agent_type,
                "transport": transport,
                "tmux_session": None,
                "state": "active" if transport == "self" else "not_spawned",
            }

    speaker_order = [
        name for name in agents.keys() if meta["agents"].get(name, {}).get("transport") != "self"
    ]

    # Add top-level state fields (schema v2, keep orchestrator mirror for compatibility)
    meta["status"] = "open"
    meta["round"] = {
        "current": 0,
        "max": DEFAULT_MAX_ROUNDS,
        "speaker_order": speaker_order,
        "waiting_for": None,
        "deadline_at": None,
    }
    if "background_file" in meta:
        meta["attachments"] = {
            "background_path": meta.get("background_file", ""),
            "manifest_path": meta.get("attachments", {}).get("manifest_path", "attachments.json"),
        }

    # Add orchestrator fields
    meta["orchestrator"] = {
        "mode": "sequential",
        "status": "open",
        "round": dict(meta["round"]),
        "auto_close": False,
        "started_at": utc_now(),
        "last_run_at": utc_now(),
        "convergence_no_objection_rounds": MAX_NO_OBJECTION_ROUNDS,
    }

    paths["meta"].write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def spawn_agent(
    memory_root: str,
    session_id: str,
    agent: str,
    agent_type: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Spawn an agent in tmux session."""
    if dry_run:
        return {"ok": True, "dry_run": True, "agent": agent, "agent_type": agent_type}

    cmd = [
        sys.executable,
        script_path("spawn_agent.py"),
        "--memory-root",
        memory_root,
        "--session-id",
        session_id,
        "--agent",
        agent,
        "--agent-type",
        agent_type,
    ]

    success, output = run_subprocess(cmd, timeout=60)
    if not success:
        raise RuntimeError(f"Failed to spawn agent {agent}: {output}")

    return json.loads(output)


def inject_round(
    memory_root: str,
    session_id: str,
    agent: str,
    round_num: int,
    prompt: str,
    max_wait: int = 300,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Inject a round prompt to an agent."""
    if dry_run:
        return {"ok": True, "dry_run": True, "agent": agent, "round": round_num}

    cmd = [
        sys.executable,
        script_path("inject_round.py"),
        "--memory-root",
        memory_root,
        "--session-id",
        session_id,
        "--agent",
        agent,
        "--round",
        str(round_num),
        "--prompt",
        prompt,
        "--max-wait",
        str(max_wait),
    ]

    success, output = run_subprocess(cmd, timeout=max_wait + 30)
    if not success:
        # Log error but don't fail - agent might have issues
        return {"ok": False, "error": output, "agent": agent, "round": round_num}

    return json.loads(output)


def get_messages(
    memory_root: str, session_id: str, since_index: int = -1
) -> list[dict[str, Any]]:
    """Get messages from session."""
    paths = session_paths(memory_root, session_id)
    events = read_jsonl(paths["jsonl"])

    if since_index < 0:
        return events

    return [
        evt
        for evt in events
        if isinstance(evt.get("index"), int) and evt["index"] > since_index
    ]


def count_message_types(
    messages: list[dict[str, Any]], round_num: int | None = None
) -> dict[str, int]:
    """Count message types, optionally filtered by round."""
    counts: dict[str, int] = {}
    for msg in messages:
        if round_num is not None:
            msg_round = msg.get("extra", {}).get("round")
            if msg_round != round_num:
                continue

        msg_type = msg.get("message_type", "comment")
        counts[msg_type] = counts.get(msg_type, 0) + 1

    return counts


def check_convergence(
    messages: list[dict[str, Any]],
    current_round: int,
    max_rounds: int,
) -> tuple[bool, str]:
    """Check if discussion has converged.

    Returns (converged, reason)
    """
    # Check for decision message
    for msg in messages:
        if msg.get("message_type") == "decision":
            return True, "decision message found"

    # Check max rounds
    if current_round >= max_rounds:
        return True, f"max rounds ({max_rounds}) reached"

    # Check for N rounds with no objections
    if current_round >= MAX_NO_OBJECTION_ROUNDS:
        recent_rounds_have_no_objections = True
        for r in range(current_round - MAX_NO_OBJECTION_ROUNDS + 1, current_round + 1):
            round_counts = count_message_types(messages, r)
            if round_counts.get("objection", 0) > 0:
                recent_rounds_have_no_objections = False
                break

        if recent_rounds_have_no_objections and current_round >= 2:
            return True, f"no objections for {MAX_NO_OBJECTION_ROUNDS} rounds"

    return False, ""


def build_round_prompt(
    round_num: int,
    topic: str,
    previous_messages: list[dict[str, Any]],
    agent: str,
) -> str:
    """Build the prompt for a round."""
    # Get recent context (last few messages)
    context_msgs = (
        previous_messages[-10:] if len(previous_messages) > 10 else previous_messages
    )

    context_str = ""
    if context_msgs:
        context_str = "\n## Recent Discussion:\n\n"
        for msg in context_msgs:
            speaker = msg.get("speaker", "unknown")
            msg_type = msg.get("message_type", "comment")
            message = msg.get("message", "")[:500]  # Truncate long messages
            context_str += f"[{msg_type}] {speaker}: {message}\n\n"

    prompt = f"""# Discussion Topic: {topic}

Round {round_num}: Please share your thoughts on the topic.{context_str}

Guidelines:
- Be concise but thorough
- If you agree with previous points, use message-type 'support'
- If you disagree, use message-type 'objection' and explain why
- If you have a concrete proposal, use message-type 'proposal'
- If you think consensus is reached, use message-type 'decision'

Take your time to formulate a thoughtful response."""

    return prompt


def close_session(
    memory_root: str,
    session_id: str,
    summary: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Close the discussion session."""
    paths = session_paths(memory_root, session_id)

    if dry_run:
        return {"ok": True, "dry_run": True, "session_id": session_id}

    # Update meta status
    meta = load_meta(paths["meta"])
    meta["status"] = "closed"
    if "round" in meta and isinstance(meta["round"], dict):
        meta["round"]["waiting_for"] = None
    meta.setdefault("orchestrator", {})
    meta["orchestrator"]["status"] = "closed"
    meta["orchestrator"]["closed_at"] = utc_now()
    if summary:
        meta["summary"] = summary

    paths["meta"].write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Append close event
    close_event = {
        "index": next_index(paths["jsonl"]),
        "timestamp": utc_now(),
        "session_id": session_id,
        "topic": meta.get("topic", ""),
        "role": "system",
        "speaker": "orchestrator",
        "message_type": "session_close",
        "message": summary or "Session closed",
        "reply_to_index": None,
        "tags": ["session", "close"],
        "extra": {"summary": summary},
    }
    append_jsonl(paths["jsonl"], close_event)

    return {"ok": True, "session_id": session_id, "status": "closed"}


def kill_tmux_sessions(memory_root: str, session_id: str) -> None:
    """Kill all tmux sessions for this discussion."""
    paths = session_paths(memory_root, session_id)
    meta = load_meta(paths["meta"])

    agents = meta.get("agents", {})
    for agent_name, agent_info in agents.items():
        session_name = agent_info.get("tmux_session")
        if session_name:
            try:
                subprocess.run(
                    ["tmux", "kill-session", "-t", session_name],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass  # Ignore errors


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Run the orchestration loop."""
    # Parse agents (optional when resuming; fall back to meta.json)
    agents: dict[str, str] = {}
    if args.agents:
        for spec in args.agents.split(","):
            if ":" in spec:
                name, agent_type = spec.split(":", 1)
                agents[name.strip()] = agent_type.strip()

    # Initialize or resume session
    if args.session_id:
        session_id = args.session_id
        # Verify session exists
        paths = session_paths(args.memory_root, session_id)
        if not paths["jsonl"].exists():
            raise ValueError(f"Session not found: {session_id}")
    else:
        if not args.topic:
            raise ValueError("--topic required when creating new session")

        result = init_session(
            args.memory_root,
            args.topic,
            args.background_file,
            agents,
        )
        session_id = result["session_id"]
        print(f"Created session: {session_id}", file=sys.stderr)

    paths = session_paths(args.memory_root, session_id)
    meta = load_meta(paths["meta"])
    if not args.dry_run:
        try:
            manifest_path = write_attachments_manifest(args.memory_root, session_id)
            print(f"Attachments manifest: {manifest_path}", file=sys.stderr)
        except Exception as exc:
            print(f"Warning: Failed to write attachments manifest: {exc}", file=sys.stderr)
            # Non-fatal: discussion can still proceed
            meta = load_meta(paths["meta"])

    if not agents:
        for agent_name, agent_info in meta.get("agents", {}).items():
            agent_type = str(agent_info.get("type") or agent_info.get("kind") or "").strip()
            if agent_type:
                agents[agent_name] = agent_type
    if not agents:
        raise ValueError(
            "No agents specified and none found in meta.json. Use --agents name:type,name2:type2"
        )

    # Get speaker order from top-level round schema
    speaker_order = []
    for name, agent_type in agents.items():
        transport = meta.get("agents", {}).get(name, {}).get("transport")
        if transport == "self" or (transport is None and agent_type == "claude-code"):
            continue
        speaker_order.append(name)
    saved_order = meta.get("round", {}).get("speaker_order") if isinstance(meta.get("round"), dict) else None
    if saved_order:
        speaker_order = [name for name in saved_order if name in agents]

    # Spawn agents
    if args.skip_spawn:
        print("Skipping spawn phase (--skip-spawn enabled)", file=sys.stderr)
    else:
        print(f"Spawning {len(agents)} agents...", file=sys.stderr)
        for agent_name, agent_type in agents.items():
            agent_meta = meta.get("agents", {}).get(agent_name, {})
            transport = agent_meta.get("transport", "tmux")
            if transport == "self":
                print(f"Skipping spawn for self agent: {agent_name}", file=sys.stderr)
                continue
            if args.dry_run:
                print(
                    f"[DRY-RUN] Would spawn: {agent_name} ({agent_type})", file=sys.stderr
                )
                continue

            try:
                # Skip if already attached to an existing tmux session
                if tmux_session_exists(str(agent_meta.get("tmux_session", ""))):
                    print(f"Reusing existing tmux session for: {agent_name}", file=sys.stderr)
                    continue
                result = spawn_agent(args.memory_root, session_id, agent_name, agent_type)
                print(f"Spawned: {agent_name}", file=sys.stderr)
            except Exception as exc:
                print(f"Warning: Failed to spawn {agent_name}: {exc}", file=sys.stderr)

    # Get current round
    current_round = 0
    if isinstance(meta.get("round"), dict):
        current_round = int(meta["round"].get("current", 0) or 0)

    # Main discussion loop
    converged = False
    convergence_reason = ""

    while not converged and current_round < args.max_rounds:
        current_round += 1
        print(f"\n=== Round {current_round} ===", file=sys.stderr)

        # Update round in meta
        meta = load_meta(paths["meta"])
        meta.setdefault("status", "discussing")
        if not isinstance(meta.get("round"), dict):
            meta["round"] = {}
        meta["round"]["current"] = current_round
        meta["round"]["max"] = args.max_rounds
        meta["round"]["speaker_order"] = speaker_order
        meta["round"]["waiting_for"] = None
        if "orchestrator" not in meta:
            meta["orchestrator"] = {}
        meta["orchestrator"]["status"] = meta.get("status", "discussing")
        meta["orchestrator"]["round"] = dict(meta["round"])
        meta["orchestrator"]["last_run_at"] = utc_now()
        if not args.dry_run:
            paths["meta"].write_text(
                json.dumps(meta, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        # Get messages before this round
        messages_before = get_messages(args.memory_root, session_id)

        # Ask each agent to speak
        for agent in speaker_order:
            agent_meta = meta.get("agents", {}).get(agent, {})
            if agent_meta.get("transport") == "self":
                print(f"Skipping inject for self agent: {agent}", file=sys.stderr)
                continue
            print(f"Prompting {agent}...", file=sys.stderr)
            # Update waiting_for in meta before dispatch
            if not args.dry_run:
                latest_meta = load_meta(paths["meta"])
                if not isinstance(latest_meta.get("round"), dict):
                    latest_meta["round"] = {}
                latest_meta["round"]["waiting_for"] = agent
                latest_meta.setdefault("orchestrator", {})
                latest_meta["orchestrator"]["round"] = dict(latest_meta["round"])
                latest_meta["status"] = "discussing"
                latest_meta["orchestrator"]["status"] = "discussing"
                paths["meta"].write_text(
                    json.dumps(latest_meta, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

            prompt = build_round_prompt(
                current_round,
                meta.get("topic", "Discussion"),
                messages_before,
                agent,
            )

            result = inject_round(
                args.memory_root,
                session_id,
                agent,
                current_round,
                prompt,
                max_wait=args.round_timeout,
                dry_run=args.dry_run,
            )

            if not result.get("ok"):
                print(
                    f"Warning: {agent} may not have responded: {result.get('error')}",
                    file=sys.stderr,
                )

        # Clear waiting_for after round
        if not args.dry_run:
            latest_meta = load_meta(paths["meta"])
            if isinstance(latest_meta.get("round"), dict):
                latest_meta["round"]["waiting_for"] = None
            latest_meta.setdefault("orchestrator", {})
            latest_meta["orchestrator"]["round"] = dict(latest_meta.get("round", {}))
            paths["meta"].write_text(
                json.dumps(latest_meta, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        # Get messages after round
        messages_after = get_messages(args.memory_root, session_id)

        # Check convergence
        converged, convergence_reason = check_convergence(
            messages_after,
            current_round,
            args.max_rounds,
        )

        if converged:
            if not args.dry_run:
                latest_meta = load_meta(paths["meta"])
                latest_meta["status"] = "converging"
                latest_meta.setdefault("orchestrator", {})
                latest_meta["orchestrator"]["status"] = "converging"
                paths["meta"].write_text(
                    json.dumps(latest_meta, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            print(f"Converged: {convergence_reason}", file=sys.stderr)
            break

        # Small delay between rounds
        if not args.dry_run:
            time.sleep(1)

    # Generate summary
    if converged or current_round >= args.max_rounds:
        all_messages = get_messages(args.memory_root, session_id)

        # Count message types
        type_counts = count_message_types(all_messages)

        summary_parts = [
            f"Discussion completed after {current_round} rounds.",
            f"Reason: {convergence_reason if converged else 'max rounds reached'}",
            "",
            "Message statistics:",
        ]
        for msg_type, count in sorted(type_counts.items()):
            summary_parts.append(f"  - {msg_type}: {count}")

        summary = "\n".join(summary_parts)

        # Append summary event
        if not args.dry_run:
            summary_event = {
                "index": len(all_messages),
                "timestamp": utc_now(),
                "session_id": session_id,
                "topic": meta.get("topic", ""),
                "role": "system",
                "speaker": "orchestrator",
                "message_type": "summary",
                "message": summary,
                "reply_to_index": None,
                "tags": ["summary", "convergence"],
                "extra": {
                    "rounds": current_round,
                    "reason": convergence_reason,
                    "message_counts": type_counts,
                },
            }
            append_jsonl(paths["jsonl"], summary_event)

        # Close session
        if args.auto_close and not args.no_auto_close and not args.dry_run:
            close_session(args.memory_root, session_id, summary)
            kill_tmux_sessions(args.memory_root, session_id)
            print("\nSession closed.", file=sys.stderr)

    return {
        "ok": True,
        "session_id": session_id,
        "rounds": current_round,
        "converged": converged,
        "reason": convergence_reason,
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
