#!/usr/bin/env python3
"""Shared helpers for agent-roundtable scripts."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
from typing import Any

SESSION_NAME_MAX_LEN = 64
SKILL_BASE_NAME = "agent-roundtable"


def utc_now() -> str:
    """Return current UTC time in RFC3339 without microseconds."""
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_layout(memory_root: str) -> dict[str, pathlib.Path]:
    """Create required directory layout and return paths."""
    root = pathlib.Path(memory_root).expanduser().resolve()
    # Accept both ".memory" and ".memory/agent-roundtable" as memory_root.
    if root.name == SKILL_BASE_NAME:
        base = root
    else:
        base = root / SKILL_BASE_NAME
    paths = {
        "base": base,
        "sessions": base / "sessions",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def slugify_topic(topic: str) -> str:
    """Generate filesystem-safe topic slug."""
    cleaned = topic.strip().lower()
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"[^a-z0-9\-]+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    if not cleaned:
        cleaned = "discussion"
    return cleaned[:SESSION_NAME_MAX_LEN]


def session_dir(memory_root: str, session_id: str) -> pathlib.Path:
    """Return path to a session directory."""
    layout = ensure_layout(memory_root)
    return layout["sessions"] / session_id


def session_paths(memory_root: str, session_id: str) -> dict[str, pathlib.Path]:
    """Return all relevant paths for a session."""
    root = session_dir(memory_root, session_id)
    return {
        "root": root,
        "meta": root / "meta.json",
        "jsonl": root / "session.jsonl",
        "cursors": root / "cursors",
    }


def load_meta(meta_path: pathlib.Path) -> dict[str, Any]:
    """Load session meta or raise ValueError for invalid content."""
    if not meta_path.exists():
        raise ValueError(f"meta file not found: {meta_path}")
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid meta json: {meta_path}") from exc


def read_jsonl(jsonl_path: pathlib.Path) -> list[dict[str, Any]]:
    """Read JSONL file, skipping empty lines."""
    if not jsonl_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            events.append(obj)
    return events


def append_jsonl(jsonl_path: pathlib.Path, obj: dict[str, Any]) -> None:
    """Append one JSON object line."""
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(obj, ensure_ascii=False) + "\n")


def next_index(jsonl_path: pathlib.Path) -> int:
    """Return next index based on last valid entry."""
    events = read_jsonl(jsonl_path)
    if not events:
        return 0
    last = events[-1]
    if isinstance(last.get("index"), int):
        return int(last["index"]) + 1
    return len(events)


def parse_csv(text: str) -> list[str]:
    """Parse comma-separated values into unique ordered list."""
    values: list[str] = []
    seen: set[str] = set()
    for part in text.split(","):
        value = part.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        values.append(value)
    return values
