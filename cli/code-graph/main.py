#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp code-graph — Lightweight project code graph indexing and search."""

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

SCRIPTS_DIR = OMP_HOME / "skills" / "code-graph" / "scripts"

app = typer.Typer(
    name="code-graph",
    help="Lightweight project code graph indexing and search.",
    no_args_is_help=True,
    add_completion=False,
)


def _run(args: list[str]) -> None:
    """Forward CLI args to the code-graph implementation script."""

    script = SCRIPTS_DIR / "code_graph.py"
    sys.exit(subprocess.call([sys.executable, str(script), *args]))


@app.command()
def index(
    repo: str = typer.Argument(..., help="Repository path to index."),
    project: str | None = typer.Option(None, "--project", "-p", help="Project name."),
) -> None:
    """Index or rebuild one project."""

    args = ["index", repo]
    if project:
        args += ["--project", project]
    _run(args)


@app.command()
def projects(
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """List indexed projects."""

    args = ["projects"]
    if json_output:
        args.append("--json")
    _run(args)


@app.command()
def status(
    project: str = typer.Option(..., "--project", "-p", help="Project name."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Show index freshness for one project."""

    args = ["status", "--project", project]
    if json_output:
        args.append("--json")
    _run(args)


@app.command()
def search(
    query: str = typer.Argument(..., help="Name substring to search."),
    project: str | None = typer.Option(None, "--project", "-p", help="Project name."),
    kind: str | None = typer.Option(None, "--kind", "-k", help="Node kind filter."),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum results."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Search indexed symbols by name."""

    args = ["search", query, "--limit", str(limit)]
    if project:
        args += ["--project", project]
    if kind:
        args += ["--kind", kind]
    if json_output:
        args.append("--json")
    _run(args)


@app.command()
def callers(
    symbol: str = typer.Argument(..., help="Function or qualified name."),
    project: str = typer.Option(..., "--project", "-p", help="Project name."),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum results."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Show functions that call a symbol."""

    args = ["callers", symbol, "--project", project, "--limit", str(limit)]
    if json_output:
        args.append("--json")
    _run(args)


@app.command()
def callees(
    symbol: str = typer.Argument(..., help="Function or qualified name."),
    project: str = typer.Option(..., "--project", "-p", help="Project name."),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum results."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Show functions called by a symbol."""

    args = ["callees", symbol, "--project", project, "--limit", str(limit)]
    if json_output:
        args.append("--json")
    _run(args)


@app.command()
def snippet(
    qname: str = typer.Argument(..., help="Qualified name from search results."),
    project: str = typer.Option(..., "--project", "-p", help="Project name."),
    context: int = typer.Option(0, "--context", "-C", help="Context lines around symbol."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Read the source snippet for a symbol."""

    args = ["snippet", qname, "--project", project, "--context", str(context)]
    if json_output:
        args.append("--json")
    _run(args)


if __name__ == "__main__":
    app()
