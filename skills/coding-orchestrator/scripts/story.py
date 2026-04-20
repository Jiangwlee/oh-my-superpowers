#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Story-level reporting helpers for coding-orchestrator."""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from common import load_yaml, require_story_dir


def _format_table(headers: list[str], rows: list[list[object]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(str(cell)))

    def render(row: list[object]) -> str:
        return " | ".join(str(cell).ljust(widths[idx]) for idx, cell in enumerate(row))

    lines = [render(headers), "-+-".join("-" * width for width in widths)]
    lines.extend(render(row) for row in rows)
    return "\n".join(lines)


def _usage_rows(tasks: list[dict], key_fn) -> list[list[object]]:
    buckets: dict[object, dict[str, int]] = defaultdict(
        lambda: {"tasks": 0, "tokens": 0, "tool_uses": 0, "duration_ms": 0}
    )
    for task in tasks:
        usage = task.get("usage") or {}
        for kind, payload in usage.items():
            if not isinstance(payload, dict):
                continue
            key = key_fn(task, kind, payload)
            bucket = buckets[key]
            bucket["tasks"] += 1
            bucket["tokens"] += int(payload.get("total_tokens", 0) or 0)
            bucket["tool_uses"] += int(payload.get("tool_uses", 0) or 0)
            bucket["duration_ms"] += int(payload.get("duration_ms", 0) or 0)
    rows = []
    for key in sorted(buckets):
        bucket = buckets[key]
        rows.append(
            [
                key,
                bucket["tasks"],
                bucket["tokens"],
                bucket["tool_uses"],
                bucket["duration_ms"],
            ]
        )
    return rows


def cmd_summarize(args: argparse.Namespace) -> int:
    try:
        story_dir = require_story_dir(Path(args.story_dir), args.story)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    tasks_data = load_yaml(story_dir / "tasks.yaml")
    tasks = tasks_data.get("tasks")
    if not isinstance(tasks, list):
        print(f"[story] tasks list missing in {story_dir / 'tasks.yaml'}", file=sys.stderr)
        return 2

    sections = []
    by_wave = _usage_rows(tasks, lambda task, kind, payload: f"wave-{task.get('wave', '?')}")
    by_kind = _usage_rows(tasks, lambda task, kind, payload: kind)
    by_model = _usage_rows(tasks, lambda task, kind, payload: payload.get("model", "unknown"))

    if by_wave:
        sections.append("## By Wave\n" + _format_table(
            ["wave", "runs", "tokens", "tool_uses", "duration_ms"], by_wave
        ))
    if by_kind:
        sections.append("## By Kind\n" + _format_table(
            ["kind", "runs", "tokens", "tool_uses", "duration_ms"], by_kind
        ))
    if by_model:
        sections.append("## By Model\n" + _format_table(
            ["model", "runs", "tokens", "tool_uses", "duration_ms"], by_model
        ))

    if not sections:
        print(f"# Story Usage Summary: {story_dir.name}\n\nNo usage metrics recorded yet.")
        return 0

    print(f"# Story Usage Summary: {story_dir.name}\n")
    print("\n\n".join(sections))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="story",
        description="Story-level reporting helpers.",
    )
    parser.add_argument(
        "--story-dir",
        required=True,
        help="Resolved project stories directory.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    summarize = sub.add_parser("summarize", help="Summarize story usage metrics.")
    summarize.add_argument("--story", required=True, help="Story slug or <YYYY-MM-DD>-<slug>.")
    summarize.set_defaults(func=cmd_summarize)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
