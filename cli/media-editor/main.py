#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp media-editor — Archive, query, and promote media items."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))

# 加载 .env
_env_file = OMP_HOME / ".env"
if _env_file.is_file():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

SCRIPTS_DIR = OMP_HOME / "skills" / "media-editor" / "scripts"

app = typer.Typer(
    name="media-editor",
    help="Archive, query, and promote media items.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def init() -> None:
    """Initialize data directory and SQLite schema (idempotent).

    Example:
        omp media-editor init
    """
    sys.exit(subprocess.call([sys.executable, str(SCRIPTS_DIR / "init.py")]))


@app.command()
def save(
    json_data: str = typer.Option(..., "--json", help="Media item as JSON string."),
) -> None:
    """Save one media item to daily archive and SQLite index.

    Example:
        omp media-editor save --json '{"url":"https://...","title":"..."}'
    """
    sys.exit(subprocess.call([sys.executable, str(SCRIPTS_DIR / "save.py"), "--json", json_data]))


@app.command()
def query(
    l1: Optional[str] = typer.Option(None, "--l1", help="L1 category filter."),
    date: Optional[str] = typer.Option(None, "--date", help="Date filter (YYYY-MM-DD)."),
    source: Optional[str] = typer.Option(None, "--source", help="Source filter (e.g. x.com)."),
    limit: int = typer.Option(20, "--limit", "-l", help="Max results to return."),
) -> None:
    """Query the media archive.

    Example:
        omp media-editor query --l1 "Claude Code" --limit 10
        omp media-editor query --date 2026-04-07
    """
    cmd = [sys.executable, str(SCRIPTS_DIR / "query.py")]
    if l1:
        cmd += ["--l1", l1]
    if date:
        cmd += ["--date", date]
    if source:
        cmd += ["--source", source]
    cmd += ["--limit", str(limit)]
    sys.exit(subprocess.call(cmd))


@app.command()
def promote(
    url: str = typer.Option(..., "--url", help="URL of the item to promote."),
) -> None:
    """Promote an item from daily archive to root-archive.

    Example:
        omp media-editor promote --url "https://x.com/..."
    """
    sys.exit(subprocess.call([sys.executable, str(SCRIPTS_DIR / "promote.py"), "--url", url]))


if __name__ == "__main__":
    app()
