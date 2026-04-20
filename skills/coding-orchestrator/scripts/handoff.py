#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Write task-level `.handoff-context` files for active orchestrator stories."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import dump_yaml, load_yaml, now_iso, require_story_dir

VALID_PHASES = {"executing", "reviewing", "accepting", "advancing"}


def _task_status_for_phase(phase: str) -> str:
    if phase == "accepting":
        return "reviewed"
    if phase == "advancing":
        return "completed"
    return "executing"


def _load_context(path: Path, story_name: str) -> dict:
    if path.is_file():
        data = load_yaml(path)
        if isinstance(data.get("wave_state"), dict):
            data["wave_state"] = {
                str(key): value for key, value in data["wave_state"].items()
            }
        return data

    return {
        "story": story_name,
        "updated_at": now_iso(),
        "current_wave": None,
        "current_phase": "executing",
        "wave_state": {},
        "pending_dispatches": [],
        "deviations_accepted": [],
        "next_action": "",
    }


def cmd_update(args: argparse.Namespace) -> int:
    if args.phase not in VALID_PHASES:
        print(
            f"[handoff] invalid phase '{args.phase}'. Valid: {sorted(VALID_PHASES)}",
            file=sys.stderr,
        )
        return 2

    story_root = Path(args.story_dir)
    try:
        story_dir = require_story_dir(story_root, args.story)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    tasks_file = story_dir / "tasks.yaml"
    tasks_data = load_yaml(tasks_file)
    tasks = tasks_data.get("tasks")
    if not isinstance(tasks, list):
        print(f"[handoff] tasks list missing in {tasks_file}", file=sys.stderr)
        return 2

    task = next((item for item in tasks if str(item.get("id")) == args.task_id), None)
    if task is None:
        print(f"[handoff] task id not found: {args.task_id}", file=sys.stderr)
        return 2

    wave = int(task.get("wave", 0))
    context_path = story_dir / ".handoff-context"
    context = _load_context(context_path, story_dir.name)
    context["story"] = story_dir.name
    context["updated_at"] = now_iso()
    context["current_wave"] = wave
    context["current_phase"] = args.phase
    context["next_action"] = args.next_action

    wave_key = str(wave)
    wave_entry = context.setdefault("wave_state", {}).setdefault(
        wave_key,
        {"status": "in-progress", "tasks": []},
    )
    wave_entry["status"] = "completed" if args.phase == "advancing" else "in-progress"

    task_entries = wave_entry.setdefault("tasks", [])
    target = next(
        (item for item in task_entries if str(item.get("id")) == args.task_id),
        None,
    )
    if target is None:
        target = {
            "id": args.task_id,
            "status": _task_status_for_phase(args.phase),
            "worker_agent_id": None,
            "reviewer_agent_id": None,
            "commit": None,
            "pending_action": args.next_action,
        }
        task_entries.append(target)

    target["status"] = _task_status_for_phase(args.phase)
    target["pending_action"] = args.next_action
    if args.worker_agent_id is not None:
        target["worker_agent_id"] = args.worker_agent_id
    if args.reviewer_agent_id is not None:
        target["reviewer_agent_id"] = args.reviewer_agent_id
    if args.commit is not None:
        target["commit"] = args.commit

    pending_dispatches = [
        item for item in context.get("pending_dispatches", [])
        if not (
            str(item.get("task_id")) == args.task_id
            and item.get("kind") in {"worker", "reviewer"}
        )
    ]
    if args.worker_agent_id and args.phase in {"executing", "reviewing"}:
        pending_dispatches.append(
            {
                "agent_id": args.worker_agent_id,
                "task_id": args.task_id,
                "kind": "worker",
                "dispatched_at": now_iso(),
            }
        )
    if args.reviewer_agent_id and args.phase == "reviewing":
        pending_dispatches.append(
            {
                "agent_id": args.reviewer_agent_id,
                "task_id": args.task_id,
                "kind": "reviewer",
                "dispatched_at": now_iso(),
            }
        )
    context["pending_dispatches"] = pending_dispatches

    if args.deviation:
        deviations = context.setdefault("deviations_accepted", [])
        deviations.append({"task_id": args.task_id, "note": args.deviation})

    dump_yaml(context_path, context)
    print(f"[handoff] updated {context_path}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="handoff",
        description="Write task-level .handoff-context files.",
    )
    parser.add_argument(
        "--story-dir",
        required=True,
        help="Resolved project stories directory.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser("update", help="Update one story's .handoff-context.")
    up.add_argument("--story", required=True, help="Story slug or <YYYY-MM-DD>-<slug>.")
    up.add_argument("--task-id", required=True, help="Task id, e.g. '01'.")
    up.add_argument("--phase", required=True, help="executing|reviewing|accepting|advancing.")
    up.add_argument("--next-action", required=True, help="Concrete next step.")
    up.add_argument("--worker-agent-id", help="Worker agent id.")
    up.add_argument("--reviewer-agent-id", help="Reviewer agent id.")
    up.add_argument("--commit", help="Commit hash associated with the task.")
    up.add_argument("--deviation", help="Accepted deviation note.")
    up.set_defaults(func=cmd_update)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
