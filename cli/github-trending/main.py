#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer"]
# ///
"""omp github-trending — Fetch GitHub trending repos as enriched JSON."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import typer

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))
SCRIPT = OMP_HOME / "skills" / "github-trending" / "scripts" / "fetch_trending.py"

app = typer.Typer(
    name="github-trending",
    help="Fetch GitHub trending repos as enriched JSON.",
    no_args_is_help=True,
    add_completion=False,
)


def _run(args: list[str]) -> None:
    sys.exit(subprocess.call(["uv", "run", str(SCRIPT), *args]))


@app.callback()
def _main() -> None:
    """Fetch GitHub trending repos as enriched JSON."""


@app.command()
def fetch(
    since: str = typer.Option("daily", "--since", help="daily / weekly / monthly."),
    lang: str = typer.Option("", "--lang", help="Language filter, e.g. python. Default: all."),
    readme_chars: int = typer.Option(4000, "--readme-chars", help="README excerpt length; 0 to skip."),
    out: str = typer.Option("", "--out", help="Output file path; default stdout."),
) -> None:
    """Scrape github.com/trending and enrich each repo via the GitHub API."""
    args = ["--since", since, "--readme-chars", str(readme_chars)]
    if lang:
        args += ["--lang", lang]
    if out:
        args += ["--out", out]
    _run(args)


if __name__ == "__main__":
    app()
