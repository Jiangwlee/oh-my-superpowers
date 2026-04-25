#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Move aged / legacy stories into stories/archives/.

Called before creating a new story to keep the active stories/ directory
free of context noise. Three archive rules (any match triggers a move):

  1. Legacy: directory name does NOT match ``^\\d{4}-\\d{2}-\\d{2}-``.
  2. Missing skeleton: no ``story.md``.
  3. Aged: latest mtime of any file in the story dir is older than
     ``--threshold-days`` days.

Usage:
    uv run scripts/archive.py --story-dir /repo/stories [--threshold-days 1] [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def _latest_mtime(story_dir: Path) -> date | None:
    """Return the most recent file mtime under story_dir, as a local date."""
    mtimes = [f.stat().st_mtime for f in story_dir.rglob("*") if f.is_file()]
    if not mtimes:
        return None
    return datetime.fromtimestamp(max(mtimes)).date()


def _should_archive(story_dir: Path, today: date, threshold: int) -> tuple[bool, str]:
    if not DATE_PREFIX.match(story_dir.name):
        return True, "legacy name (no YYYY-MM-DD prefix)"

    if not (story_dir / "story.md").is_file():
        return True, "no story.md"

    latest = _latest_mtime(story_dir)
    if latest is None:
        return True, "empty story dir"

    age = (today - latest).days
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
        help="Stories whose latest file mtime is older than this many days are archived (default: 1).",
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
