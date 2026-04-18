#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer"]
# ///
"""omp coding-orchestrator — Story / task lifecycle helpers.

Three domains:
  handoff / restore      → PreCompact and PostCompact hook entry points
  archive                → move aged / legacy stories to stories/archives/
  task update | show     → hot-path edits on tasks.yaml (status, worker, commits)

The orchestrator is free to edit tasks.yaml directly. These commands exist
only to keep the high-frequency updates atomic and auditable.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import typer

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))
SCRIPTS = OMP_HOME / "skills" / "coding-orchestrator" / "scripts"

app = typer.Typer(
    name="coding-orchestrator",
    help="Story / task lifecycle helpers for the coding-orchestrator skill.",
    no_args_is_help=True,
    add_completion=False,
)
task_app = typer.Typer(
    name="task",
    help="Hot-path edits on tasks.yaml.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(task_app, name="task")


def _run(script: str, args: list[str]) -> None:
    path = SCRIPTS / script
    sys.exit(subprocess.call(["uv", "run", str(path), *args]))


@app.command()
def handoff(
    auto: bool = typer.Option(False, "--auto", help="Scan all active stories."),
    story: str | None = typer.Option(None, "--story", help="Process one story by name."),
    story_dir: str = typer.Option("./stories", "--story-dir", help="Stories root."),
) -> None:
    """PreCompact: write handoff.md for active stories."""
    args: list[str] = ["--story-dir", story_dir]
    if auto:
        args.append("--auto")
    if story:
        args += ["--story", story]
    _run("handoff.py", args)


@app.command()
def restore(
    story: str | None = typer.Option(None, "--story", help="Process one story by name."),
    story_dir: str = typer.Option("./stories", "--story-dir", help="Stories root."),
) -> None:
    """PostCompact: surface handoff.md so the orchestrator can resume."""
    args: list[str] = ["--story-dir", story_dir]
    if story:
        args += ["--story", story]
    _run("restore.py", args)


@app.command()
def archive(
    story_dir: str = typer.Option("./stories", "--story-dir", help="Stories root."),
    threshold_days: int = typer.Option(1, "--threshold-days", help="Age cutoff in days."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Report without moving."),
) -> None:
    """Move aged / legacy stories into stories/archives/."""
    args: list[str] = ["--story-dir", story_dir, "--threshold-days", str(threshold_days)]
    if dry_run:
        args.append("--dry-run")
    _run("archive.py", args)


@task_app.command("update")
def task_update(
    story: str = typer.Option(..., "--story", help="Story slug or <YYYY-MM-DD>-<slug>."),
    id: str = typer.Option(..., "--id", help="Task id, e.g. '01'."),
    status: str | None = typer.Option(None, "--status", help="pending|executing|reviewing|testing|completed|blocked."),
    worker: str | None = typer.Option(None, "--worker", help="Worker identifier."),
    reviewer: str | None = typer.Option(None, "--reviewer", help="Reviewer identifier."),
    commit: str | None = typer.Option(None, "--commit", help="Commit hash to append."),
    note: str | None = typer.Option(None, "--note", help="Replace the notes field."),
    story_dir: str = typer.Option("./stories", "--story-dir", help="Stories root."),
) -> None:
    """Flip status, attach a commit, set worker/reviewer, or leave a note."""
    args = ["--story-dir", story_dir, "update", "--story", story, "--id", id]
    if status is not None:
        args += ["--status", status]
    if worker is not None:
        args += ["--worker", worker]
    if reviewer is not None:
        args += ["--reviewer", reviewer]
    if commit is not None:
        args += ["--commit", commit]
    if note is not None:
        args += ["--note", note]
    _run("task.py", args)


@task_app.command("show")
def task_show(
    story: str = typer.Option(..., "--story", help="Story slug or <YYYY-MM-DD>-<slug>."),
    id: str | None = typer.Option(None, "--id", help="Show one task; omit to list all."),
    story_dir: str = typer.Option("./stories", "--story-dir", help="Stories root."),
) -> None:
    """List tasks for a story, or show one task's full record."""
    args = ["--story-dir", story_dir, "show", "--story", story]
    if id is not None:
        args += ["--id", id]
    _run("task.py", args)


if __name__ == "__main__":
    app()
