#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Convenience CLI for the hot-path edits of tasks.yaml.

Covers task status flips, worker assignment, free-form notes, and per-wave
snapshot append (reviewer + commit live in the wave snapshot, not on the task).
Adding, removing, or reordering tasks is NOT the hot path; edit tasks.yaml
directly for those.

Auto-maintains:
  - tasks[*].started     (first time status becomes executing)
  - tasks[*].completed   (status becomes completed)
  - waves[*].completed_at (auto-set when wave entry is appended/replaced)
  - story.updated        (any successful update)

Invoke via: `omp kickoff task update | show | wave-update ...`
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import dump_yaml, load_yaml, now_iso, require_story_dir, today_date

VALID_STATUSES = {"pending", "executing", "completed", "blocked"}


def _load(tasks_file: Path) -> dict:
    data = load_yaml(tasks_file)
    if "tasks" not in data or not isinstance(data["tasks"], list):
        raise SystemExit(f"[task] tasks.yaml missing 'tasks' list: {tasks_file}")
    return data


def cmd_update(args: argparse.Namespace) -> int:
    story_root = Path(args.story_dir)
    try:
        story_dir = require_story_dir(story_root, args.story)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    tasks_file = story_dir / "tasks.yaml"
    data = _load(tasks_file)

    target = next((t for t in data["tasks"] if str(t.get("id")) == args.id), None)
    if target is None:
        print(f"[task] task id not found: {args.id}", file=sys.stderr)
        return 2

    changed = False

    if args.status is not None:
        if args.status not in VALID_STATUSES:
            print(
                f"[task] invalid status '{args.status}'. Valid: {sorted(VALID_STATUSES)}",
                file=sys.stderr,
            )
            return 2
        if args.status == "executing" and not target.get("spec"):
            print(
                f"[task] JIT spec missing for task {args.id}: "
                f"cannot transition to executing while 'spec' is null/empty. "
                f"Write tasks/task-{args.id}.md and set spec before dispatching.",
                file=sys.stderr,
            )
            return 2
        prev = target.get("status")
        target["status"] = args.status
        if args.status == "executing" and not target.get("started"):
            target["started"] = now_iso()
        if args.status == "completed" and not target.get("completed"):
            target["completed"] = now_iso()
        changed = changed or prev != args.status

    if args.worker is not None:
        target["worker"] = args.worker
        changed = True

    if args.note is not None:
        target["notes"] = args.note
        changed = True

    if not changed:
        print("[task] no change", file=sys.stderr)
        return 0

    data["updated"] = today_date()
    dump_yaml(tasks_file, data)
    print(f"[task] updated {tasks_file}:{args.id}", file=sys.stderr)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    story_root = Path(args.story_dir)
    try:
        story_dir = require_story_dir(story_root, args.story)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    data = _load(story_dir / "tasks.yaml")
    tasks = data.get("tasks", [])

    if args.id:
        target = next((t for t in tasks if str(t.get("id")) == args.id), None)
        if target is None:
            print(f"[task] task id not found: {args.id}", file=sys.stderr)
            return 2
        import yaml
        print(yaml.safe_dump(target, sort_keys=False, allow_unicode=True))
        return 0

    print(f"{'ID':<4} {'STATUS':<11} {'WAVE':<4} TITLE")
    for t in tasks:
        print(
            f"{str(t.get('id','')):<4} "
            f"{str(t.get('status','')):<11} "
            f"{str(t.get('wave','')):<4} "
            f"{t.get('title','')}"
        )
    return 0


def cmd_wave_update(args: argparse.Namespace) -> int:
    """Append (or replace if --number already exists) one wave snapshot entry."""
    story_root = Path(args.story_dir)
    try:
        story_dir = require_story_dir(story_root, args.story)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    tasks_file = story_dir / "tasks.yaml"
    data = _load(tasks_file)

    waves = data.setdefault("waves", []) or []
    if not isinstance(waves, list):
        print(f"[task] 'waves' is not a list in {tasks_file}", file=sys.stderr)
        return 2

    entry = {
        "number": args.number,
        "completed_at": now_iso(),
        "reviewer": args.reviewer or "",
        "commit": args.commit or "",
        "key_decisions": list(args.key_decision or []),
        "open_questions": list(args.open_question or []),
        "next_focus": args.next_focus or "",
    }

    existing_idx = next(
        (i for i, w in enumerate(waves) if isinstance(w, dict) and w.get("number") == args.number),
        None,
    )
    if existing_idx is not None:
        waves[existing_idx] = entry
        verb = "replaced"
    else:
        waves.append(entry)
        verb = "appended"

    data["waves"] = waves
    data["updated"] = today_date()
    dump_yaml(tasks_file, data)
    print(f"[task] wave {args.number} {verb} in {tasks_file}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="task",
        description="Hot-path edits for tasks.yaml (status / worker / commit / note / wave snapshot).",
    )
    parser.add_argument(
        "--story-dir", required=True,
        help="Resolved project stories directory.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser("update", help="Update one field on one task.")
    up.add_argument("--story", required=True, help="Story slug or <YYYY-MM-DD>-<slug>.")
    up.add_argument("--id", required=True, help="Task id, e.g. '01'.")
    up.add_argument("--status", help=f"New status ({'|'.join(sorted(VALID_STATUSES))}).")
    up.add_argument("--worker", help="Worker identifier.")
    up.add_argument("--note", help="Replace the notes field.")
    up.set_defaults(func=cmd_update)

    sh = sub.add_parser("show", help="Show one task or the story's task list.")
    sh.add_argument("--story", required=True, help="Story slug or <YYYY-MM-DD>-<slug>.")
    sh.add_argument("--id", help="Show only this task id (default: list all).")
    sh.set_defaults(func=cmd_show)

    wu = sub.add_parser(
        "wave-update",
        help="Append (or replace by --number) a wave snapshot at wave close.",
    )
    wu.add_argument("--story", required=True, help="Story slug or <YYYY-MM-DD>-<slug>.")
    wu.add_argument("--number", type=int, required=True, help="Wave number, e.g. 1.")
    wu.add_argument("--reviewer", help="Reviewer identifier for this wave's review.")
    wu.add_argument("--commit", help="Commit hash for this wave's single commit.")
    wu.add_argument(
        "--key-decision", action="append",
        help="Repeatable: a key decision made during this wave.",
    )
    wu.add_argument(
        "--open-question", action="append",
        help="Repeatable: an unresolved item handed to next wave or to the user.",
    )
    wu.add_argument("--next-focus", help="One-liner: what the next wave should prioritise.")
    wu.set_defaults(func=cmd_wave_update)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
