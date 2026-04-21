#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Story-level reporting helpers for coding-orchestrator."""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from common import load_yaml, require_story_dir, today_date

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
MEMORY_PLACEHOLDER = (
    "# Story Memory\n\n"
    "## Patterns\n\n"
    "## Gotchas\n\n"
    "## Known False Positives\n"
)


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


def _render_story_md(slug: str, design_doc: str | None) -> str:
    text = (TEMPLATES_DIR / "story.md").read_text(encoding="utf-8").replace(
        "<story-name>", slug, 1
    )
    if not design_doc:
        return text
    lines = text.splitlines(keepends=True)
    insert_at = 1
    while insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1
    lines.insert(insert_at, f"\n> Design: {design_doc}\n")
    return "".join(lines)


def _render_tasks_yaml(slug: str, date: str) -> str:
    src = (TEMPLATES_DIR / "tasks.yaml").read_text(encoding="utf-8")
    src = src.replace("<story-slug>", slug).replace("<YYYY-MM-DD>", date)
    out: list[str] = []
    for line in src.splitlines(keepends=True):
        if line.startswith("tasks:"):
            out.append("tasks: []\n")
            break
        out.append(line)
    return "".join(out)


def cmd_init(args: argparse.Namespace) -> int:
    slug = args.slug
    if DATE_PREFIX_RE.match(slug):
        print(
            f"[story] --slug must not include date prefix; got '{slug}' "
            "(date is added automatically)",
            file=sys.stderr,
        )
        return 2
    if not SLUG_RE.match(slug):
        print(
            f"[story] --slug must be kebab-case lowercase a-z0-9-; got '{slug}'",
            file=sys.stderr,
        )
        return 2

    date = args.date or today_date()
    if not DATE_RE.match(date):
        print(f"[story] --date must be YYYY-MM-DD; got '{date}'", file=sys.stderr)
        return 2

    story_root = Path(args.story_dir)
    story_root.mkdir(parents=True, exist_ok=True)

    story_dir = story_root / f"{date}-{slug}"
    if story_dir.exists():
        if not args.force:
            print(
                f"[story] story dir already exists: {story_dir} "
                "(use --force to recreate into an empty dir)",
                file=sys.stderr,
            )
            return 2
        if any(story_dir.iterdir()):
            print(
                f"[story] --force refused: {story_dir} is not empty",
                file=sys.stderr,
            )
            return 2

    (story_dir / "tasks").mkdir(parents=True, exist_ok=True)
    (story_dir / "story.md").write_text(
        _render_story_md(slug, args.design_doc), encoding="utf-8"
    )
    (story_dir / "tasks.yaml").write_text(
        _render_tasks_yaml(slug, date), encoding="utf-8"
    )
    (story_dir / "story-memory.md").write_text(MEMORY_PLACEHOLDER, encoding="utf-8")

    print(str(story_dir))
    return 0


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

    init = sub.add_parser("init", help="Create a new story directory from templates.")
    init.add_argument("--slug", required=True, help="Kebab-case slug, no date prefix.")
    init.add_argument("--date", help="YYYY-MM-DD; defaults to today.")
    init.add_argument("--design-doc", help="Optional design doc path; inserted as backlink.")
    init.add_argument("--force", action="store_true", help="Allow init when dir exists but is empty.")
    init.set_defaults(func=cmd_init)

    summarize = sub.add_parser("summarize", help="Summarize story usage metrics.")
    summarize.add_argument("--story", required=True, help="Story slug or <YYYY-MM-DD>-<slug>.")
    summarize.set_defaults(func=cmd_summarize)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
