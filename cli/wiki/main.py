#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp wiki — Karpathy-style markdown wiki management."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import typer


OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))

_env_file = OMP_HOME / ".env"
if _env_file.is_file():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

SCRIPTS_DIR = OMP_HOME / "skills" / "llm-wiki" / "scripts"

app = typer.Typer(
    name="wiki",
    help="Karpathy-style markdown wiki management.",
    no_args_is_help=True,
    add_completion=False,
)


def _run(script_name: str, args: list[str]) -> None:
    """Forward CLI args to a skill implementation script."""

    script = SCRIPTS_DIR / script_name
    sys.exit(subprocess.call([sys.executable, str(script), *args]))


@app.command()
def init(
    wiki_home: str | None = typer.Option(None, "--wiki-home", help="Override global wiki home."),
) -> None:
    """Initialize the global wiki home."""

    args: list[str] = []
    if wiki_home:
        args += ["--wiki-home", wiki_home]
    _run("init.py", args)


@app.command()
def ingest(
    source: str | None = typer.Argument(None, help="Source URL or local file."),
    text: bool = typer.Option(False, "--text", help="Read markdown/text from stdin."),
    title: str | None = typer.Option(None, "--title", help="Explicit title for text ingest."),
    project: str | None = typer.Option(None, "--project", help="Optional project metadata."),
    wiki_home: str | None = typer.Option(None, "--wiki-home", help="Override global wiki home."),
) -> None:
    """Ingest URL, file, or stdin text into raw/."""

    args: list[str] = []
    if source:
        args.append(source)
    if text:
        args.append("--text")
    if title:
        args += ["--title", title]
    if project:
        args += ["--project", project]
    if wiki_home:
        args += ["--wiki-home", wiki_home]
    _run("ingest.py", args)


@app.command()
def nav(
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    wiki_home: str | None = typer.Option(None, "--wiki-home", help="Override global wiki home."),
) -> None:
    """Show wiki status and entrypoints."""

    args: list[str] = []
    if json_output:
        args.append("--json")
    if wiki_home:
        args += ["--wiki-home", wiki_home]
    _run("nav.py", args)


@app.command()
def lint(
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    wiki_home: str | None = typer.Option(None, "--wiki-home", help="Override global wiki home."),
) -> None:
    """Lint compiled wiki pages and report issues."""

    args: list[str] = []
    if json_output:
        args.append("--json")
    if wiki_home:
        args += ["--wiki-home", wiki_home]
    _run("lint.py", args)


if __name__ == "__main__":
    app()
