#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Move aged / legacy stories into stories/archives/.

Called before creating a new story to keep the active stories/ directory
free of context noise. Three archive rules (any match triggers a move):

  1. Legacy: directory name does NOT match ``^\\d{4}-\\d{2}-\\d{2}-``.
  2. Missing state: no tasks.yaml, OR tasks.yaml has no ``updated`` field.
  3. Aged: ``today - tasks.yaml.updated > --threshold-days``.

Usage:
    uv run scripts/archive.py --story-dir /repo/stories [--threshold-days 1] [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def _load_updated(tasks_file: Path) -> date | None:
    if not tasks_file.is_file():
        return None
    import yaml
    try:
        data = yaml.safe_load(tasks_file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None
    raw = data.get("updated")
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _should_archive(story_dir: Path, today: date, threshold: int) -> tuple[bool, str]:
    if not DATE_PREFIX.match(story_dir.name):
        return True, "legacy name (no YYYY-MM-DD prefix)"

    tasks_file = story_dir / "tasks.yaml"
    if not tasks_file.is_file():
        return True, "no tasks.yaml"

    updated = _load_updated(tasks_file)
    if updated is None:
        return True, "tasks.yaml missing 'updated'"

    age = (today - updated).days
    if age > threshold:
        return True, f"aged {age}d (> {threshold}d)"
    return False, f"fresh ({age}d)"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="archive",
        description="Move stale stories into stories/archives/.",
    )
    parser.add_argument(
        "--story-dir", required=True,
        help="Resolved project stories directory.",
    )
    parser.add_argument(
        "--threshold-days", type=int, default=1,
        help="Stories with updated older than this many days are archived (default: 1).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would be moved without touching files.",
    )
    args = parser.parse_args()

    story_root = Path(args.story_dir)
    if not story_root.is_dir():
        print(f"[archive] story-dir not found: {story_root}", file=sys.stderr)
        return 0

    archives = story_root / "archives"
    today = date.today()
    moved = 0

    for child in sorted(story_root.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name == "archives":
            continue
        should, reason = _should_archive(child, today, args.threshold_days)
        if not should:
            continue

        dest = archives / child.name
        if args.dry_run:
            print(f"[archive] DRY-RUN would move {child.name} → archives/ ({reason})")
        else:
            archives.mkdir(exist_ok=True)
            if dest.exists():
                print(f"[archive] skip {child.name}: destination exists", file=sys.stderr)
                continue
            shutil.move(str(child), str(dest))
            print(f"[archive] moved {child.name} → archives/ ({reason})", file=sys.stderr)
        moved += 1

    if moved == 0:
        print("[archive] nothing to archive", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
