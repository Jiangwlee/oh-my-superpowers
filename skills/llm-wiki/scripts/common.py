"""Shared helpers for the llm-wiki skill."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_WIKI_HOME = Path.home() / ".local" / "share" / "oh-my-superpowers" / "wiki"


def resolve_wiki_home(explicit: str | None = None) -> Path:
    """Resolve the global wiki home from CLI override, env, or default."""

    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("WIKI_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return DEFAULT_WIKI_HOME


def raw_dir(wiki_home: Path) -> Path:
    """Return the raw input directory."""

    return wiki_home / "raw"


def wiki_dir(wiki_home: Path) -> Path:
    """Return the compiled wiki directory."""

    return wiki_home / "wiki"


def state_path(wiki_home: Path) -> Path:
    """Return the JSON state file."""

    return wiki_home / "state.json"


def now_iso() -> str:
    """Return an ISO timestamp in UTC."""

    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def today_utc() -> str:
    """Return the current UTC date in YYYY-MM-DD format."""

    return datetime.now(tz=UTC).strftime("%Y-%m-%d")


def ensure_parent(path: Path) -> None:
    """Create parent directories when needed."""

    path.parent.mkdir(parents=True, exist_ok=True)


def write_text_atomic(path: Path, content: str) -> None:
    """Write a text file atomically using a sibling temp file."""

    ensure_parent(path)
    tmp = path.parent / f".{path.name}.tmp.{os.getpid()}"
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def load_json(path: Path, default: Any) -> Any:
    """Load JSON from disk, returning default when absent."""

    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    """Write JSON with stable formatting."""

    write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def slugify(value: str) -> str:
    """Convert free text into a filesystem-safe slug."""

    cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value.strip().lower()).strip("-")
    return cleaned or "untitled"


def title_from_body(body: str) -> str | None:
    """Extract the first markdown heading from a body."""

    match = re.search(r"^#{1,6}\s+(.+)$", body, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def title_from_plain_text(body: str, max_words: int = 10) -> str | None:
    """Derive a readable title from the opening sentence of plain text."""

    text = re.sub(r"\s+", " ", body).strip()
    if not text:
        return None
    first_sentence = re.split(r"(?<=[.!?。！？])\s+", text, maxsplit=1)[0].strip()
    words = first_sentence.split()
    candidate = " ".join(words[:max_words]).strip(" -:;,.")
    return candidate or None


def strip_leading_title_heading(body: str, title: str) -> str:
    """Remove an initial markdown heading when it matches the chosen title."""

    lines = body.splitlines()
    if not lines:
        return body.strip()
    first = lines[0].strip()
    if re.fullmatch(r"#{1,6}\s+" + re.escape(title.strip()), first):
        return "\n".join(lines[1:]).lstrip()
    return body.strip()


def detect_project_name() -> str | None:
    """Infer the current git repo name for ingest metadata."""

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            text=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    repo_root = Path(result.stdout.strip())
    return repo_root.name if repo_root.name else None


def infer_project(explicit: str | None) -> str | None:
    """Resolve project metadata from CLI or current git repo."""

    return explicit or detect_project_name()


def list_markdown_files(directory: Path) -> list[Path]:
    """Return markdown files in a directory sorted by name."""

    if not directory.exists():
        return []
    return sorted(path for path in directory.iterdir() if path.is_file() and path.suffix == ".md")
