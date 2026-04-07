#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp insight — Extract memories from AI conversations and distill insights."""

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

CLI_SCRIPT = OMP_HOME / "skills" / "insight" / "scripts" / "cli.py"

app = typer.Typer(
    name="insight",
    help="Extract memories from AI conversations and distill insights.",
    no_args_is_help=True,
    add_completion=False,
)

_default_model = os.environ.get("OMP_DEFAULT_MODEL_PI", "openai-codex/gpt-5.4-mini")


def _run(args: list[str]) -> None:
    """Forward to the implementation script."""
    sys.exit(subprocess.call([sys.executable, str(CLI_SCRIPT)] + args))


@app.command()
def capture(
    source: Optional[str] = typer.Option(None, "--source", help="Project directory (default: cwd)."),
    session: Optional[str] = typer.Option(None, "--session", help="Process only this session ID."),
    since: Optional[str] = typer.Option(None, "--since", help="Only process sessions from last N days (e.g. 7d)."),
    min_messages: int = typer.Option(10, "--min-messages", help="Skip sessions with fewer messages."),
    force: bool = typer.Option(False, "--force", help="Ignore processed markers, force reprocess."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Analyze only, do not write."),
    model: str = typer.Option(_default_model, "--model", help="LLM model."),
    if_no_compact: bool = typer.Option(False, "--if-no-compact", help="Only run if PostCompact not yet triggered."),
) -> None:
    """Extract memories from AI conversations.

    Example:
        omp insight capture --source $PWD --since 1d
        omp insight capture --session abc123 --dry-run
    """
    cmd = ["capture"]
    if source:
        cmd += ["--source", source]
    if session:
        cmd += ["--session", session]
    if since:
        cmd += ["--since", since]
    cmd += ["--min-messages", str(min_messages)]
    if force:
        cmd.append("--force")
    if dry_run:
        cmd.append("--dry-run")
    cmd += ["--model", model]
    if if_no_compact:
        cmd.append("--if-no-compact")
    _run(cmd)


@app.command()
def recall(
    source: Optional[str] = typer.Option(None, "--source", help="Project directory (default: cwd)."),
    format: str = typer.Option("md", "--format", help="Output format (json|md)."),
    budget: int = typer.Option(4096, "--budget", help="Token budget."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not record hit_logs."),
    hook: bool = typer.Option(False, "--hook", help="Hook mode: output hookSpecificOutput JSON."),
) -> None:
    """Recall memories and insights for current project.

    Example:
        omp insight recall --source $PWD
        omp insight recall --budget 2048 --format json
    """
    cmd = ["recall"]
    if source:
        cmd += ["--source", source]
    cmd += ["--format", format, "--budget", str(budget)]
    if dry_run:
        cmd.append("--dry-run")
    if hook:
        cmd.append("--hook")
    _run(cmd)


@app.command()
def evaluate(
    source: Optional[str] = typer.Option(None, "--source", help="Project directory (default: cwd)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Output candidates only, do not write."),
    prompt_file: Optional[str] = typer.Option(None, "--prompt-file", help="External prompt template file."),
    model: str = typer.Option(_default_model, "--model", help="LLM model."),
) -> None:
    """Distill insights from accumulated memories.

    Example:
        omp insight evaluate --source $PWD
        omp insight evaluate --dry-run
    """
    cmd = ["evaluate"]
    if source:
        cmd += ["--source", source]
    if dry_run:
        cmd.append("--dry-run")
    if prompt_file:
        cmd += ["--prompt-file", prompt_file]
    cmd += ["--model", model]
    _run(cmd)


@app.command("list")
def list_items(
    source: Optional[str] = typer.Option(None, "--source", help="Project directory (default: cwd)."),
    type: Optional[str] = typer.Option(None, "--type", help="Filter by type (memory|insight)."),
) -> None:
    """List memories and/or insights.

    Example:
        omp insight list --source $PWD
        omp insight list --type insight
    """
    cmd = ["list"]
    if source:
        cmd += ["--source", source]
    if type:
        cmd += ["--type", type]
    _run(cmd)


@app.command()
def promote(
    id: str = typer.Argument(..., help="Memory ID (mem_ prefix)."),
    reason: Optional[str] = typer.Option(None, "--reason", help="Promotion reason."),
    source: Optional[str] = typer.Option(None, "--source", help="Project directory (default: cwd)."),
) -> None:
    """Promote a memory to insight.

    Example:
        omp insight promote mem_abc123 --reason "repeated pattern"
    """
    cmd = ["promote", id]
    if reason:
        cmd += ["--reason", reason]
    if source:
        cmd += ["--source", source]
    _run(cmd)


@app.command()
def degrade(
    id: str = typer.Argument(..., help="Insight ID (ins_ prefix)."),
    reason: Optional[str] = typer.Option(None, "--reason", help="Degradation reason."),
    source: Optional[str] = typer.Option(None, "--source", help="Project directory (default: cwd)."),
) -> None:
    """Degrade an insight back to memory.

    Example:
        omp insight degrade ins_abc123 --reason "no longer valid"
    """
    cmd = ["degrade", id]
    if reason:
        cmd += ["--reason", reason]
    if source:
        cmd += ["--source", source]
    _run(cmd)


@app.command()
def delete(
    id: str = typer.Argument(..., help="ID (mem_ or ins_ prefix)."),
    source: Optional[str] = typer.Option(None, "--source", help="Project directory (default: cwd)."),
) -> None:
    """Delete a memory or insight.

    Example:
        omp insight delete mem_abc123
    """
    cmd = ["delete", id]
    if source:
        cmd += ["--source", source]
    _run(cmd)


if __name__ == "__main__":
    app()
