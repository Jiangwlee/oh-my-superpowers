#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Render task context fragments for code review dispatch."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import load_yaml, require_story_dir


def _extract_section(markdown: str, heading: str) -> str:
    marker = f"## {heading}"
    lines = markdown.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == marker:
            start = idx + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for idx in range(start, len(lines)):
        if lines[idx].startswith("## "):
            end = idx
            break
    return "\n".join(lines[start:end]).strip()


def _extract_title(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _task_spec_path(story_dir: Path, task: dict) -> Path:
    spec = task.get("spec")
    if not spec:
        raise SystemExit(f"[review] task {task.get('id')} has no spec path")
    spec_path = story_dir / str(spec)
    if not spec_path.is_file():
        raise SystemExit(f"[review] task spec not found: {spec_path}")
    return spec_path


def cmd_create(args: argparse.Namespace) -> int:
    try:
        story_dir = require_story_dir(Path(args.story_dir), args.story)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    tasks_data = load_yaml(story_dir / "tasks.yaml")
    tasks = tasks_data.get("tasks")
    if not isinstance(tasks, list):
        print(f"[review] tasks list missing in {story_dir / 'tasks.yaml'}", file=sys.stderr)
        return 2

    task = next((item for item in tasks if str(item.get("id")) == args.task_id), None)
    if task is None:
        print(f"[review] task id not found: {args.task_id}", file=sys.stderr)
        return 2

    spec_path = _task_spec_path(story_dir, task)
    spec_text = spec_path.read_text(encoding="utf-8")
    title = _extract_title(spec_text)
    objective = _extract_section(spec_text, "Objective") or "_Missing Objective section_"
    file_scope = _extract_section(spec_text, "File Scope") or "_Missing File Scope section_"
    acceptance = _extract_section(spec_text, "Acceptance Criteria") or "_Missing Acceptance Criteria section_"

    commits = task.get("commits") or []
    commits_line = " ".join(commits) if commits else "none"
    git_cmds = "\n".join(f"  git show {sha} --stat" for sha in commits) if commits else "  (no commits yet)"

    additional = (args.additional or "").strip() or "None."

    lines = [
        "# Review Context",
        f"Task: {story_dir.name}/{args.task_id}" + (f" — {title}" if title else ""),
        "",
        "## Objective",
        objective,
        "",
        "## Acceptance Criteria",
        acceptance,
        "",
        "## File Scope",
        file_scope,
        "",
        f"## Commits: {commits_line}",
        "Git preview commands:",
        git_cmds,
        "",
        "## Additional",
        additional,
    ]
    rendered = "\n".join(lines)

    out_path = Path(args.out) if args.out else Path(f"/tmp/orchestrator-review-{args.task_id}.md")
    out_path.write_text(rendered, encoding="utf-8")
    print(str(out_path))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="review",
        description="Render task context fragment for review dispatch.",
    )
    parser.add_argument("--story-dir", required=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    create = sub.add_parser("create", help="Create a task context fragment for review dispatch.")
    create.add_argument("--story", required=True, help="Story slug or <YYYY-MM-DD>-<slug>.")
    create.add_argument("--task-id", required=True, help="Task id, e.g. '01'.")
    create.add_argument("--additional", help="Additional task-specific review instructions.")
    create.add_argument("--out", help="Output path for the rendered fragment.")
    create.set_defaults(func=cmd_create)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
