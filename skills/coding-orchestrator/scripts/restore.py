#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""PostCompact hook: build .handoff-context from the latest handoff.md.

Reads the most recent handoff.md and writes a consolidated recovery file
to ./stories/.handoff-context for quick orientation after compaction.

Usage:
    uv run scripts/restore.py --story-dir ./stories
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


def find_latest_handoff(story_dir: Path) -> tuple[Path, str] | None:
    """Find the most recently modified handoff.md across all stories.

    Args:
        story_dir: Root stories directory.

    Returns:
        Tuple of (handoff_path, story_name), or None if not found.
    """
    latest: tuple[Path, str, float] | None = None

    for child in story_dir.iterdir():
        if not child.is_dir() or child.name.startswith("."):
            continue
        handoff = child / "handoff.md"
        if handoff.is_file():
            mtime = handoff.stat().st_mtime
            if latest is None or mtime > latest[2]:
                latest = (handoff, child.name, mtime)

    if latest is None:
        return None
    return latest[0], latest[1]


def parse_handoff_table(content: str) -> list[dict[str, str]]:
    """Parse the progress table from a handoff.md file.

    Args:
        content: Full handoff.md content.

    Returns:
        List of dicts with keys: task, status, title.
    """
    tasks: list[dict[str, str]] = []
    in_table = False
    for line in content.splitlines():
        if line.startswith("| Task"):
            in_table = True
            continue
        if line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 3:
                tasks.append({
                    "task": cells[0],
                    "status": cells[1],
                    "title": cells[2],
                })
        elif in_table and not line.startswith("|"):
            in_table = False
    return tasks


def extract_section(content: str, heading: str) -> str:
    """Extract content under a specific ## heading.

    Args:
        content: Full markdown content.
        heading: The heading text (without ##).

    Returns:
        The section content, or empty string.
    """
    pattern = rf"^## {re.escape(heading)}\s*$"
    lines = content.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            start = i + 1
            continue
        if start is not None and line.startswith("## "):
            return "\n".join(lines[start:i]).strip()
    if start is not None:
        return "\n".join(lines[start:]).strip()
    return ""


def build_recovery_context(story_name: str, handoff_content: str) -> str:
    """Build .handoff-context from a handoff.md file.

    Args:
        story_name: Name of the story.
        handoff_content: Content of the handoff.md file.

    Returns:
        Markdown content for the recovery file.
    """
    now = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    tasks = parse_handoff_table(handoff_content)

    total = len(tasks)
    completed = sum(1 for t in tasks if t["status"] == "completed")
    in_progress_tasks = [t for t in tasks if t["status"] in {"executing", "reviewing", "testing"}]
    pending = total - completed - len(in_progress_tasks)

    lines: list[str] = [
        "# Coding Orchestrator — Recovery Context",
        "",
        f"**Story**: {story_name}",
        f"**Last updated**: {now}",
        f"**Source**: ./stories/{story_name}/handoff.md",
        "",
        "## Quick Status",
        "",
        f"- Total tasks: {total}",
        f"- Completed: {completed}",
    ]

    if in_progress_tasks:
        ip_desc = ", ".join(f"{t['task']}: {t['status']}" for t in in_progress_tasks)
        lines.append(f"- In progress: {len(in_progress_tasks)} ({ip_desc})")
    else:
        lines.append("- In progress: 0")

    lines.append(f"- Pending: {pending}")

    # Resume from section
    lines.extend(["", "## Resume From", ""])
    if in_progress_tasks:
        active = in_progress_tasks[0]
        lines.extend([
            f"**Task**: {active['task']}",
            f"**Phase**: {active['status'].capitalize()}",
            f"**Action needed**: Continue {active['status']} of {active['title']}",
        ])
    else:
        # Find first pending task
        pending_tasks = [t for t in tasks if t["status"] not in {"completed"}]
        if pending_tasks:
            nxt = pending_tasks[0]
            lines.extend([
                f"**Task**: {nxt['task']}",
                f"**Phase**: Pending",
                f"**Action needed**: Dispatch {nxt['title']}",
            ])
        else:
            lines.append("All tasks completed. Verify acceptance criteria.")

    # Critical context — pass through from handoff if available
    active_section = extract_section(handoff_content, "Active Task")
    next_section = extract_section(handoff_content, "Next Steps")

    if active_section or next_section:
        lines.extend(["", "## Critical Context", ""])
        if active_section:
            lines.append(active_section)
            lines.append("")
        if next_section:
            lines.append("**Upcoming:**")
            lines.append(next_section)

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """Entry point for the PostCompact hook."""
    parser = argparse.ArgumentParser(
        description="PostCompact hook: build .handoff-context from latest handoff.md.",
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
        print(f"[restore] story-dir not found: {story_dir}", file=sys.stderr)
        return 0  # Not an error — skill may not be active

    result = find_latest_handoff(story_dir)
    if result is None:
        print("[restore] no handoff.md found", file=sys.stderr)
        return 0

    handoff_path, story_name = result
    handoff_content = handoff_path.read_text(encoding="utf-8")
    recovery = build_recovery_context(story_name, handoff_content)

    context_path = story_dir / ".handoff-context"
    context_path.write_text(recovery, encoding="utf-8")
    print(f"[restore] wrote {context_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
