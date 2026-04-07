#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp deep-research — Initialize and build deep-research workspaces."""

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

SCRIPTS_DIR = OMP_HOME / "skills" / "deep-research" / "scripts"

app = typer.Typer(
    name="deep-research",
    help="Initialize and build deep-research workspaces.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def init(
    topic: str = typer.Option(..., "--topic", help="Research topic."),
    slug: str | None = typer.Option(None, "--slug", help="Optional explicit workspace slug."),
    mode: str = typer.Option(
        "default", "--mode", help="Research depth mode (quick|default|deep)."
    ),
) -> None:
    """Create a new research workspace.

    Example:
        omp deep-research init --topic "CLI metadata protocols"
        omp deep-research init --topic "AI memory" --mode deep --slug ai-mem
    """
    cmd = [sys.executable, str(SCRIPTS_DIR / "init.py"), "--topic", topic]
    if slug:
        cmd += ["--slug", slug]
    cmd += ["--mode", mode]
    sys.exit(subprocess.call(cmd))


@app.command("build-report")
def build_report(
    workspace: str = typer.Option(..., "--workspace", help="Workspace directory."),
    brief_file: str | None = typer.Option(None, "--brief-file", help="Markdown file for brief output."),
    full_report_file: str | None = typer.Option(
        None, "--full-report-file", help="Markdown file for full report output."
    ),
    brief: str | None = typer.Option(None, "--brief", help="Inline brief markdown."),
    full_report: str | None = typer.Option(None, "--full-report", help="Inline full report markdown."),
    sources_file: str | None = typer.Option(None, "--sources-file", help="JSON file containing sources array."),
) -> None:
    """Write reports and persist sources to workspace.

    Example:
        omp deep-research build-report --workspace /path/to/ws --brief-file brief.md --full-report-file report.md
    """
    cmd = [sys.executable, str(SCRIPTS_DIR / "build_report.py"), "--workspace", workspace]
    if brief_file:
        cmd += ["--brief-file", brief_file]
    if full_report_file:
        cmd += ["--full-report-file", full_report_file]
    if brief:
        cmd += ["--brief", brief]
    if full_report:
        cmd += ["--full-report", full_report]
    if sources_file:
        cmd += ["--sources-file", sources_file]
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    app()
