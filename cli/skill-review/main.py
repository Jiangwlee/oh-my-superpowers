#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp skill-review — Run mechanical consistency checks on a skill directory."""

import subprocess
import sys
from pathlib import Path
import os

import typer

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))
SCRIPT = OMP_HOME / "skills" / "skill-review" / "scripts" / "consistency_check.py"

app = typer.Typer(
    name="skill-review",
    help="Mechanical consistency checks for a skill directory.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def check(
    skill_dir: str = typer.Option(..., "--skill-dir", help="Path to the skill directory."),
    output: str = typer.Option("text", "--output", help="Output format: text | json."),
) -> None:
    """Run mechanical consistency checks on a skill directory.

    Example:
        omp skill-review --skill-dir skills/my-skill
        omp skill-review --skill-dir skills/my-skill --output json
    """
    if not SCRIPT.is_file():
        typer.echo(f"Error: consistency_check.py not found at {SCRIPT}", err=True)
        raise typer.Exit(1)

    cmd = [sys.executable, str(SCRIPT), "--skill-dir", skill_dir]
    if output == "json":
        cmd += ["--output", "json"]

    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    app()
