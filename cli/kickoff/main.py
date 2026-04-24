#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer"]
# ///
"""omp kickoff — Story / task lifecycle helpers for the kickoff skill.

Domains:
  archive            → move aged / legacy stories to stories/archives/
  story init         → create a new story directory from templates
  task update | show → hot-path edits on tasks.yaml (status / worker / commit / note)
  task wave-update   → append (or replace by --number) one wave snapshot at wave close

Kickoff is free to edit story artifacts directly. These commands exist
only to keep the high-frequency updates atomic and auditable.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import typer

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))
SCRIPTS = OMP_HOME / "skills" / "kickoff" / "scripts"

app = typer.Typer(
    name="kickoff",
    help="Story / task lifecycle helpers for the kickoff skill.",
    no_args_is_help=True,
    add_completion=False,
)
story_app = typer.Typer(
    name="story",
    help="Story directory bootstrap.",
    no_args_is_help=True,
    add_completion=False,
)
task_app = typer.Typer(
    name="task",
    help="Hot-path edits on tasks.yaml.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(story_app, name="story")
app.add_typer(task_app, name="task")


def _run(script: str, args: list[str]) -> None:
    path = SCRIPTS / script
    sys.exit(subprocess.call(["uv", "run", str(path), *args]))


@app.command()
def archive(
    story_dir: str = typer.Option(..., "--story-dir", help="Resolved project stories root."),
    threshold_days: int = typer.Option(1, "--threshold-days", help="Age cutoff in days."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Report without moving."),
) -> None:
    """Move aged / legacy stories into stories/archives/."""
    args: list[str] = ["--story-dir", story_dir, "--threshold-days", str(threshold_days)]
    if dry_run:
        args.append("--dry-run")
    _run("archive.py", args)


@story_app.command("init")
def story_init(
    slug: str = typer.Option(..., "--slug", help="Kebab-case slug; no date prefix."),
    date: str | None = typer.Option(None, "--date", help="YYYY-MM-DD; defaults to today."),
    design_doc: str | None = typer.Option(
        None, "--design-doc", help="Optional design doc path; inserted as backlink."
    ),
    force: bool = typer.Option(False, "--force", help="Allow init when dir exists but is empty."),
    story_dir: str = typer.Option(..., "--story-dir", help="Resolved project stories root."),
) -> None:
    """Create a new story directory under <story-dir>/<YYYY-MM-DD>-<slug>/."""
    args = ["--story-dir", story_dir, "init", "--slug", slug]
    if date is not None:
        args += ["--date", date]
    if design_doc is not None:
        args += ["--design-doc", design_doc]
    if force:
        args.append("--force")
    _run("story.py", args)


@task_app.command("update")
def task_update(
    story: str = typer.Option(..., "--story", help="Story slug or <YYYY-MM-DD>-<slug>."),
    id: str = typer.Option(..., "--id", help="Task id, e.g. '01'."),
    status: str | None = typer.Option(None, "--status", help="pending|executing|completed|blocked."),
    worker: str | None = typer.Option(None, "--worker", help="Worker identifier ('inline' or sub-agent id)."),
    reviewer: str | None = typer.Option(None, "--reviewer", help="Reviewer identifier."),
    commit: str | None = typer.Option(None, "--commit", help="Commit hash to append."),
    note: str | None = typer.Option(None, "--note", help="Replace the notes field."),
    story_dir: str = typer.Option(..., "--story-dir", help="Resolved project stories root."),
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
    story_dir: str = typer.Option(..., "--story-dir", help="Resolved project stories root."),
) -> None:
    """List tasks for a story, or show one task's full record."""
    args = ["--story-dir", story_dir, "show", "--story", story]
    if id is not None:
        args += ["--id", id]
    _run("task.py", args)


@task_app.command("wave-update")
def task_wave_update(
    story: str = typer.Option(..., "--story", help="Story slug or <YYYY-MM-DD>-<slug>."),
    number: int = typer.Option(..., "--number", help="Wave number, e.g. 1."),
    key_decision: list[str] = typer.Option(
        None, "--key-decision",
        help="Repeatable: a key decision made during this wave.",
    ),
    open_question: list[str] = typer.Option(
        None, "--open-question",
        help="Repeatable: an unresolved item handed to next wave or to the user.",
    ),
    next_focus: str | None = typer.Option(
        None, "--next-focus", help="One-liner: what the next wave should prioritise."
    ),
    story_dir: str = typer.Option(..., "--story-dir", help="Resolved project stories root."),
) -> None:
    """Append (or replace by --number) a wave snapshot at wave close."""
    args = [
        "--story-dir", story_dir,
        "wave-update", "--story", story, "--number", str(number),
    ]
    for d in key_decision or []:
        args += ["--key-decision", d]
    for q in open_question or []:
        args += ["--open-question", q]
    if next_focus is not None:
        args += ["--next-focus", next_focus]
    _run("task.py", args)


if __name__ == "__main__":
    app()
