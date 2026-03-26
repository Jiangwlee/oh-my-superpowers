"""Shared helpers for the deep-research skill."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "oh-my-superpowers" / "deep-research"


@dataclass(slots=True)
class WorkspacePaths:
    """Resolved workspace file paths."""

    workspace: Path
    raw_dir: Path
    notes_dir: Path
    reports_dir: Path
    state_file: Path
    rounds_file: Path


def data_dir() -> Path:
    """Return the root data directory for deep-research."""

    return Path.home().joinpath(".local", "share", "oh-my-superpowers", "deep-research").expanduser() \
        if "DEEP_RESEARCH_DATA_DIR" not in __import__("os").environ \
        else Path(__import__("os").environ["DEEP_RESEARCH_DATA_DIR"]).expanduser()


def slugify(value: str) -> str:
    """Convert a topic string into a filesystem-friendly slug."""

    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "research"


def timestamp_prefix(now: datetime | None = None) -> str:
    """Return the workspace timestamp prefix."""

    now = now or datetime.now()
    return now.strftime("%Y-%m-%dT%H-%M")


def workspace_paths(workspace: Path) -> WorkspacePaths:
    """Return canonical paths inside a workspace."""

    return WorkspacePaths(
        workspace=workspace,
        raw_dir=workspace / "raw",
        notes_dir=workspace / "notes",
        reports_dir=workspace / "reports",
        state_file=workspace / "state.json",
        rounds_file=workspace / "rounds.jsonl",
    )


def ensure_workspace_dirs(workspace: Path) -> WorkspacePaths:
    """Create required workspace directories and return canonical paths."""

    paths = workspace_paths(workspace)
    paths.raw_dir.mkdir(parents=True, exist_ok=True)
    paths.notes_dir.mkdir(parents=True, exist_ok=True)
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    return paths


def load_json(path: Path, default: Any) -> Any:
    """Load JSON from disk, returning default when the file is absent."""

    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    """Write JSON to disk with stable formatting."""

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def next_source_id(state: dict[str, Any]) -> str:
    """Allocate the next source id from the current state."""

    items = state.get("source_index", [])
    return f"S{len(items) + 1:03d}"


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    """Append one JSON object line to a JSONL file."""

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def resolve_workspace(path_str: str) -> Path:
    """Resolve and validate a workspace path."""

    workspace = Path(path_str).expanduser().resolve()
    if not workspace.exists():
        raise FileNotFoundError(f"workspace not found: {workspace}")
    return workspace
