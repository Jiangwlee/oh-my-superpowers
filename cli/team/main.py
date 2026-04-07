#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp team — One-shot tmux agent orchestration."""

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

SCRIPTS_DIR = OMP_HOME / "skills" / "team" / "scripts"

app = typer.Typer(
    name="team",
    help="One-shot tmux agent orchestration (spawn → wait → output).",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def run(
    runtime: str = typer.Argument(..., help="Agent runtime (claude|codex|pi)."),
    prompt: Optional[str] = typer.Argument(None, help="Inline prompt text."),
    prompt_file: Optional[str] = typer.Option(None, "--prompt-file", help="Read prompt from file."),
    model: Optional[str] = typer.Option(None, "--model", help="Override default model."),
    timeout: int = typer.Option(300, "--timeout", help="Timeout in seconds."),
    output_file: Optional[str] = typer.Option(None, "--output-file", help="Write output to file."),
    cwd: Optional[str] = typer.Option(None, "--cwd", help="Worker working directory (default: $PWD)."),
) -> None:
    """Spawn an agent, wait for completion, and return output.

    Example:
        omp team run codex "implement user login"
        omp team run claude --prompt-file design.md
        omp team run codex --prompt-file task.md --cwd ./project --timeout 600
    """
    cmd = ["bash", str(SCRIPTS_DIR / "run.sh"), runtime]
    if prompt:
        cmd.append(prompt)
    if prompt_file:
        cmd += ["--prompt-file", prompt_file]
    if model:
        cmd += ["--model", model]
    cmd += ["--timeout", str(timeout)]
    if output_file:
        cmd += ["--output-file", output_file]
    if cwd:
        cmd += ["--cwd", cwd]
    sys.exit(subprocess.call(cmd))


@app.command()
def status(
    session_name: Optional[str] = typer.Argument(None, help="Specific tmux session name."),
) -> None:
    """Query tmux session status.

    Example:
        omp team status
        omp team status my-session
    """
    cmd = ["bash", str(SCRIPTS_DIR / "status.sh")]
    if session_name:
        cmd.append(session_name)
    sys.exit(subprocess.call(cmd))


@app.command()
def clean(
    file: str = typer.Argument(..., help="File to strip ANSI escape sequences from."),
) -> None:
    """Strip ANSI escape sequences and normalize output.

    Example:
        omp team clean /tmp/codex-output.txt
    """
    sys.exit(subprocess.call(["bash", str(SCRIPTS_DIR / "clean.sh"), file]))


if __name__ == "__main__":
    app()
