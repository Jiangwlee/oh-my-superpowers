"""Shared helpers for coding-supervisor scripts."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def now_iso() -> str:
    """Return a timezone-aware ISO-like timestamp."""
    return datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def today_date() -> str:
    """Return the local calendar date."""
    return datetime.now().strftime("%Y-%m-%d")


def find_story_dir(story_root: Path, name: str) -> Path | None:
    """Resolve a story directory by slug or ``YYYY-MM-DD-slug``."""
    direct = story_root / name
    if direct.is_dir():
        return direct
    matches = sorted(
        child for child in story_root.iterdir()
        if child.is_dir() and child.name.endswith(f"-{name}")
    )
    if len(matches) == 1:
        return matches[0]
    return None


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file as a mapping."""
    import yaml

    if not path.is_file():
        raise SystemExit(f"[supervisor] yaml not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"[supervisor] expected mapping in yaml: {path}")
    return data


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    """Write a YAML mapping with stable key order."""
    import yaml

    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def require_story_dir(story_root: Path, story: str) -> Path:
    """Resolve a story directory or fail with exit 2 semantics."""
    story_dir = find_story_dir(story_root, story)
    if story_dir is None:
        raise SystemExit(f"[supervisor] story not found under {story_root}: {story}")
    return story_dir
