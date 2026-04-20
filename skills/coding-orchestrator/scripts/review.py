#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Render review prompts from a story's task artifacts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import load_yaml, require_story_dir

TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "templates"
VALID_TEMPLATES = {"default", "strict", "minimal"}


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


def _task_spec_path(story_dir: Path, task: dict) -> Path:
    spec = task.get("spec")
    if not spec:
        raise SystemExit(f"[review] task {task.get('id')} has no spec path")
    spec_path = story_dir / str(spec)
    if not spec_path.is_file():
        raise SystemExit(f"[review] task spec not found: {spec_path}")
    return spec_path


def _render_changes(task: dict) -> str:
    commits = task.get("commits") or []
    if not commits:
        return "- No commits recorded yet.\n"
    lines = []
    for sha in commits:
        lines.append(f"- Commit: `{sha}`")
        lines.append(f"  - Diff command: `git show {sha} --stat`")
    return "\n".join(lines)


def _load_template(story_dir: Path, template_name: str) -> str:
    override = story_dir / ".review-template.md"
    if override.is_file():
        return override.read_text(encoding="utf-8")
    template_path = TEMPLATE_ROOT / f"review-rubric-{template_name}.md"
    if not template_path.is_file():
        raise SystemExit(f"[review] template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def cmd_create(args: argparse.Namespace) -> int:
    if args.template not in VALID_TEMPLATES:
        print(
            f"[review] invalid template '{args.template}'. Valid: {sorted(VALID_TEMPLATES)}",
            file=sys.stderr,
        )
        return 2

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
    objective = _extract_section(spec_text, "Objective") or "_Missing Objective section_"
    file_scope = _extract_section(spec_text, "File Scope") or "_Missing File Scope section_"
    acceptance = _extract_section(spec_text, "Acceptance Criteria") or "_Missing Acceptance Criteria section_"
    template = _load_template(story_dir, args.template)
    rendered = template.format(
        task_id=args.task_id,
        story_name=story_dir.name,
        spec_path=spec_path,
        objective=objective,
        file_scope=file_scope,
        acceptance=acceptance,
        changes=_render_changes(task),
        additional=(args.additional or "").strip() or "None.",
    )

    out_path = Path(args.out) if args.out else Path(f"/tmp/orchestrator-review-{args.task_id}.md")
    out_path.write_text(rendered, encoding="utf-8")
    print(str(out_path))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="review",
        description="Render review prompts from story/task artifacts.",
    )
    parser.add_argument(
        "--story-dir",
        default="./stories",
        help="Root stories directory (default: ./stories).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    create = sub.add_parser("create", help="Create a review prompt.")
    create.add_argument("--story", required=True, help="Story slug or <YYYY-MM-DD>-<slug>.")
    create.add_argument("--task-id", required=True, help="Task id, e.g. '01'.")
    create.add_argument("--template", default="default", help="default|strict|minimal.")
    create.add_argument("--additional", help="Additional task-specific review instructions.")
    create.add_argument("--out", help="Output path for the rendered prompt.")
    create.set_defaults(func=cmd_create)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
