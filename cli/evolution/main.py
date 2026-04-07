#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp evolution — Scan sessions and view evolution history."""

import os
import subprocess
import sys
from pathlib import Path
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

SCRIPTS_DIR = OMP_HOME / "skills" / "evolution" / "scripts"

app = typer.Typer(
    name="evolution",
    help="Scan sessions for skill usage data and view evolution history.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def scan(
    source: str = typer.Option(
        str(Path.home() / "Projects"), "--source", help="Directory to scan for project sessions."
    ),
    days: int = typer.Option(30, "--days", help="Scan last N days."),
    project_root: str | None = typer.Option(
        None, "--project-root", help="Current project root (default: auto-detect)."
    ),
) -> None:
    """Scan sessions for skill usage data and mechanical signals.

    Example:
        omp evolution scan
        omp evolution scan --days 7 --source ~/Projects
    """
    cmd = [sys.executable, str(SCRIPTS_DIR / "scan.py")]
    cmd += ["--source", source, "--days", str(days)]
    if project_root:
        cmd += ["--project-root", project_root]
    sys.exit(subprocess.call(cmd))


@app.command()
def history(
    limit: int = typer.Option(20, "--limit", "-l", help="Show last N records."),
    project_root: str | None = typer.Option(
        None, "--project-root", help="Current project root (default: auto-detect)."
    ),
) -> None:
    """View evolution history for current project.

    Example:
        omp evolution history
        omp evolution history --limit 10
    """
    cmd = [sys.executable, str(SCRIPTS_DIR / "history.py")]
    cmd += ["--limit", str(limit)]
    if project_root:
        cmd += ["--project-root", project_root]
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    app()
