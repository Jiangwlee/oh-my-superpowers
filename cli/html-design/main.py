#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp html-design — Design HTML page prototypes with DESIGN.md references."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import typer

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))
SKILL_DIR = OMP_HOME / "skills" / "html-design"
SCRIPTS_DIR = SKILL_DIR / "scripts"

app = typer.Typer(
    name="html-design",
    help="Design HTML page prototypes with DESIGN.md references.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command("compile")
def compile_index(
    source: Path = typer.Option(
        Path("~/Github/open-design/plugins/_official/design-systems").expanduser(),
        "--source",
        "-s",
        help="Directory containing design-system DESIGN.md files.",
    ),
    output: Path = typer.Option(
        SKILL_DIR / "assets" / "design-index.json",
        "--output",
        "-o",
        help="Output JSON index file.",
    ),
) -> None:
    """Compile DESIGN.md files into a searchable index."""
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "design_index.py"),
        "compile",
        "--source",
        str(source),
        "--output",
        str(output),
    ]
    raise typer.Exit(subprocess.call(cmd))


@app.command("search")
def search_index(
    query: list[str] = typer.Argument(..., help="Search keywords."),
    index: Path = typer.Option(
        SKILL_DIR / "assets" / "design-index.json",
        "--index",
        "-i",
        help="Compiled design index JSON file.",
    ),
    limit: int = typer.Option(5, "--limit", "-n", min=1, help="Maximum results."),
) -> None:
    """Search the compiled DESIGN.md index."""
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "design_index.py"),
        "search",
        "--index",
        str(index),
        "--limit",
        str(limit),
        *query,
    ]
    raise typer.Exit(subprocess.call(cmd))


@app.command("init")
def init_workspace(
    slug: str = typer.Option("html-design", "--slug", help="Task slug for directory naming."),
    root: Path = typer.Option(
        Path(os.environ.get("HTML_DESIGN_WORK_DIR", "/tmp")),
        "--root",
        help="Parent directory for temporary design workspaces.",
    ),
) -> None:
    """Create a temporary workspace for one HTML design task."""
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "workspace.py"),
        "init",
        "--slug",
        slug,
        "--root",
        str(root),
    ]
    raise typer.Exit(subprocess.call(cmd))


if __name__ == "__main__":
    app()
