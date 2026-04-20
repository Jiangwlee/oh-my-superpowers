#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Convenience CLI for the hot-path edits of tasks.yaml.

Covers status flips, worker/reviewer assignment, commit pinning, and
free-form notes — the fields an orchestrator touches many times per
story. Adding, removing, or reordering tasks is NOT the hot path; edit
tasks.yaml directly for those (orchestrator retains full authoring freedom).

Auto-maintains:
  - tasks[*].started    (first time status becomes executing)
  - tasks[*].completed  (status becomes completed)
  - story.updated       (any successful update)

Invoke via: `omp coding-orchestrator task update|show ...`
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import dump_yaml, load_yaml, now_iso, require_story_dir, today_date

VALID_STATUSES = {
    "pending", "executing", "reviewing", "testing", "completed", "blocked",
}

USAGE_KINDS = {"worker", "reviewer"}


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

    if args.reviewer is not None:
        target["reviewer"] = args.reviewer
        changed = True

    if args.commit:
        commits = target.setdefault("commits", [])
        if args.commit not in commits:
            commits.append(args.commit)
            changed = True

    if args.note is not None:
        target["notes"] = args.note
        changed = True

    usage_kind = getattr(args, "usage_kind", None)
    model = getattr(args, "model", None)
    tokens = getattr(args, "tokens", None)
    tool_uses = getattr(args, "tool_uses", None)
    duration_ms = getattr(args, "duration_ms", None)
    usage_fields = [model, tokens, tool_uses, duration_ms]
    if usage_kind is not None or any(value is not None for value in usage_fields):
        if usage_kind not in USAGE_KINDS:
            print(
                f"[task] --usage-kind must be one of {sorted(USAGE_KINDS)}",
                file=sys.stderr,
            )
            return 2
        usage = target.setdefault("usage", {})
        bucket = usage.setdefault(usage_kind, {})
        if model is not None:
            bucket["model"] = model
        if tokens is not None:
            bucket["total_tokens"] = tokens
        if tool_uses is not None:
            bucket["tool_uses"] = tool_uses
        if duration_ms is not None:
            bucket["duration_ms"] = duration_ms
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


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="task",
        description="Hot-path edits for tasks.yaml (status / worker / commit / note).",
    )
    parser.add_argument(
        "--story-dir", default="./stories",
        help="Root stories directory (default: ./stories).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser("update", help="Update one field on one task.")
    up.add_argument("--story", required=True, help="Story slug or <YYYY-MM-DD>-<slug>.")
    up.add_argument("--id", required=True, help="Task id, e.g. '01'.")
    up.add_argument("--status", help=f"New status ({'|'.join(sorted(VALID_STATUSES))}).")
    up.add_argument("--worker", help="Worker identifier.")
    up.add_argument("--reviewer", help="Reviewer identifier.")
    up.add_argument("--commit", help="Commit hash to append.")
    up.add_argument("--note", help="Replace the notes field.")
    up.add_argument("--usage-kind", help="Usage role (worker|reviewer).")
    up.add_argument("--model", help="Model name used by the sub-agent.")
    up.add_argument("--tokens", type=int, help="Total token count for the run.")
    up.add_argument("--tool-uses", type=int, help="Tool call count for the run.")
    up.add_argument("--duration-ms", type=int, help="Run duration in milliseconds.")
    up.set_defaults(func=cmd_update)

    sh = sub.add_parser("show", help="Show one task or the story's task list.")
    sh.add_argument("--story", required=True, help="Story slug or <YYYY-MM-DD>-<slug>.")
    sh.add_argument("--id", help="Show only this task id (default: list all).")
    sh.set_defaults(func=cmd_show)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
