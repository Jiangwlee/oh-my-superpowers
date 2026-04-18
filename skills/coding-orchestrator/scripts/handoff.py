#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""PreCompact hook: extract story state into handoff.md.

Scans the story directory for active stories, reads ``tasks.yaml`` to
determine progress, and writes a handoff.md file for each active story.

Usage:
    uv run scripts/handoff.py --auto --story-dir ./stories
    uv run scripts/handoff.py --story <name> --story-dir ./stories
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


def scan_tasks(story_dir: Path) -> list[dict[str, object]]:
    """Read tasks.yaml for a story and return task metadata.

    Args:
        story_dir: Path to the story directory.

    Returns:
        Ordered list of task dicts (id, title, status, depends_on).
        Empty list if tasks.yaml is missing or malformed.
    """
    import yaml  # lazy — keep --help fast when pyyaml missing

    tasks_file = story_dir / "tasks.yaml"
    if not tasks_file.is_file():
        return []

    try:
        data = yaml.safe_load(tasks_file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        print(f"[handoff] malformed {tasks_file}: {e}", file=sys.stderr)
        return []

    raw_tasks = data.get("tasks") or []
    tasks: list[dict[str, object]] = []
    for t in raw_tasks:
        if not isinstance(t, dict):
            continue
        tasks.append({
            "id": str(t.get("id", "")).strip(),
            "title": str(t.get("title", "untitled")).strip(),
            "status": str(t.get("status", "pending")).strip(),
            "depends_on": t.get("depends_on", []) or [],
        })
    return tasks


def find_active_task(tasks: list[dict[str, object]]) -> dict[str, object] | None:
    """Find the first task with non-terminal status.

    Args:
        tasks: List of task metadata dicts.

    Returns:
        The active task dict, or None.
    """
    active_statuses = {"executing", "reviewing", "testing"}
    for task in tasks:
        if task["status"] in active_statuses:
            return task
    return None


def build_handoff(story_name: str, story_dir: Path) -> str:
    """Build handoff.md content for a single story.

    Args:
        story_name: Name of the story.
        story_dir: Path to the story directory.

    Returns:
        Markdown content for the handoff file.
    """
    tasks = scan_tasks(story_dir)
    now = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")

    lines: list[str] = [
        f"# Handoff: {story_name}",
        "",
        f"**Timestamp**: {now}",
        "",
        "## Story Progress",
        "",
        "| Task | Status | Title |",
        "|------|--------|-------|",
    ]

    for t in tasks:
        lines.append(f"| task-{t['id']} | {t['status']} | {t['title']} |")

    # Summary counts
    completed = sum(1 for t in tasks if t["status"] == "completed")
    in_progress = sum(1 for t in tasks if t["status"] in {"executing", "reviewing", "testing"})
    pending = sum(1 for t in tasks if t["status"] in {"pending", "blocked"})

    lines.extend([
        "",
        "## Summary",
        "",
        f"- Total tasks: {len(tasks)}",
        f"- Completed: {completed}",
        f"- In progress: {in_progress}",
        f"- Pending: {pending}",
    ])

    # Active task details
    active = find_active_task(tasks)
    if active:
        lines.extend([
            "",
            "## Active Task",
            "",
            f"**Task**: task-{active['id']} — {active['title']}",
            f"**Phase**: {active['status'].capitalize()}",
            f"**Depends on**: {active['depends_on']}",
        ])

    # Next steps: list pending tasks in order
    pending_tasks = [t for t in tasks if t["status"] == "pending"]
    if pending_tasks:
        lines.extend([
            "",
            "## Next Steps",
            "",
        ])
        for i, t in enumerate(pending_tasks[:5], 1):
            lines.append(f"{i}. task-{t['id']}: {t['title']}")

    lines.append("")
    return "\n".join(lines)


def find_active_stories(story_dir: Path) -> list[Path]:
    """Find story directories that have at least one non-completed task.

    Args:
        story_dir: Root stories directory.

    Returns:
        List of story directory paths.
    """
    if not story_dir.is_dir():
        return []

    active: list[Path] = []
    for child in sorted(story_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        tasks = scan_tasks(child)
        if any(t["status"] != "completed" for t in tasks):
            active.append(child)
    return active


def main() -> int:
    """Entry point for the PreCompact hook."""
    parser = argparse.ArgumentParser(
        description="PreCompact hook: extract story state into handoff.md.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Scan all stories and write handoff for active ones.",
    )
    parser.add_argument(
        "--story",
        type=str,
        help="Process a specific story by name.",
    )
    parser.add_argument(
        "--story-dir",
        type=str,
        default="./stories",
        help="Root stories directory (default: ./stories).",
    )
    args = parser.parse_args()
    story_dir = Path(args.story_dir)

    if not story_dir.is_dir():
        print(f"[handoff] story-dir not found: {story_dir}", file=sys.stderr)
        return 0  # Not an error — skill may not be active

    if args.story:
        targets = [story_dir / args.story]
        targets = [t for t in targets if t.is_dir()]
    elif args.auto:
        targets = find_active_stories(story_dir)
    else:
        parser.print_help()
        return 1

    if not targets:
        print("[handoff] no active stories found", file=sys.stderr)
        return 0

    for target in targets:
        story_name = target.name
        content = build_handoff(story_name, target)
        handoff_path = target / "handoff.md"
        handoff_path.write_text(content, encoding="utf-8")
        print(f"[handoff] wrote {handoff_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
