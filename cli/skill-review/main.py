#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp skill-review — Skill review pipeline.

Subcommands:
  check            → run mechanical consistency checks (JSON output)
  emit-checklist   → produce a per-dimension scaffold for manual review
  validate         → reject filled reports that still have unfilled rows
"""

import os
import subprocess
import sys
from pathlib import Path

import typer

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))
SCRIPTS = OMP_HOME / "skills" / "skill-review" / "scripts"

CHECK_SCRIPT = SCRIPTS / "consistency_check.py"
EMIT_SCRIPT = SCRIPTS / "emit_checklist.py"
VALIDATE_SCRIPT = SCRIPTS / "validate_review.py"

app = typer.Typer(
    name="skill-review",
    help="Skill review pipeline (check / emit-checklist / validate).",
    invoke_without_command=True,
    add_completion=False,
)


def _run(script: Path, args: list[str]) -> None:
    if not script.is_file():
        typer.echo(f"Error: script not found at {script}", err=True)
        raise typer.Exit(1)
    sys.exit(subprocess.call([sys.executable, str(script), *args]))


def _run_check(skill_dir: str, output: str) -> None:
    _run(CHECK_SCRIPT, ["--skill-dir", skill_dir])


@app.callback()
def root(
    ctx: typer.Context,
    skill_dir: str | None = typer.Option(
        None, "--skill-dir",
        help="Legacy shorthand for `check --skill-dir <path>`.",
    ),
    output: str = typer.Option("text", "--output", help="Output format: text | json (legacy)."),
) -> None:
    """Skill review pipeline. Use a subcommand, or `--skill-dir` as a shortcut for `check`."""
    if ctx.invoked_subcommand is not None:
        return
    if skill_dir is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()
    _run_check(skill_dir, output)


@app.command()
def check(
    skill_dir: str = typer.Option(..., "--skill-dir", help="Path to the skill directory."),
    output: str = typer.Option("text", "--output", help="Output format: text | json."),
) -> None:
    """Run mechanical consistency checks on a skill directory.

    Example:
        omp skill-review check --skill-dir skills/my-skill
        omp skill-review check --skill-dir skills/my-skill --output json
    """
    _run_check(skill_dir, output)


@app.command("emit-checklist")
def emit_checklist(
    skill_dir: str = typer.Option(..., "--skill-dir", help="Path to the skill directory under review."),
    output: str = typer.Option(..., "--output", help="Path to write the scaffold Markdown."),
) -> None:
    """Generate a per-dimension review scaffold the agent must fill in.

    Example:
        omp skill-review emit-checklist --skill-dir skills/my-skill --output /tmp/review-my-skill.md
    """
    _run(EMIT_SCRIPT, ["--skill-dir", skill_dir, "--output", output])


@app.command()
def validate(
    report: str = typer.Argument(..., help="Path to the filled review report Markdown."),
) -> None:
    """Reject reports that still have unfilled checkboxes or scaffold placeholders.

    Example:
        omp skill-review validate /tmp/review-my-skill.md
    """
    _run(VALIDATE_SCRIPT, [report])


if __name__ == "__main__":
    prog_name = os.environ.get("OMP_TOOL_PROG_NAME")
    if prog_name:
        app(prog_name=prog_name)
    else:
        app()
