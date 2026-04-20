#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer"]
# ///
"""omp coding-orchestrator — Story / task lifecycle helpers.

Domains:
  archive                 → move aged / legacy stories to stories/archives/
  handoff update          → write task-level handoff context for one story
  review create           → render a review prompt from story/task artifacts
  story summarize         → aggregate task usage by wave / role / model
  task update | show      → hot-path edits on tasks.yaml

The orchestrator is free to edit story artifacts directly. These commands
exist only to keep the high-frequency updates atomic and auditable.
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
handoff_app = typer.Typer(
    name="handoff",
    help="Task-level handoff context helpers.",
    no_args_is_help=True,
    add_completion=False,
)
review_app = typer.Typer(
    name="review",
    help="Review prompt generation helpers.",
    no_args_is_help=True,
    add_completion=False,
)
story_app = typer.Typer(
    name="story",
    help="Story-level reporting helpers.",
    no_args_is_help=True,
    add_completion=False,
)
task_app = typer.Typer(
    name="task",
    help="Hot-path edits on tasks.yaml.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(handoff_app, name="handoff")
app.add_typer(review_app, name="review")
app.add_typer(story_app, name="story")
app.add_typer(task_app, name="task")


def _run(script: str, args: list[str]) -> None:
    path = SCRIPTS / script
    sys.exit(subprocess.call(["uv", "run", str(path), *args]))


@handoff_app.command("update")
def handoff_update(
    story: str = typer.Option(..., "--story", help="Story slug or <YYYY-MM-DD>-<slug>."),
    task_id: str = typer.Option(..., "--task-id", help="Task id, e.g. '01'."),
    phase: str = typer.Option(..., "--phase", help="executing|reviewing|accepting|advancing."),
    next_action: str = typer.Option(..., "--next-action", help="One-line concrete next step."),
    worker_agent_id: str | None = typer.Option(None, "--worker-agent-id", help="Worker agent id."),
    reviewer_agent_id: str | None = typer.Option(None, "--reviewer-agent-id", help="Reviewer agent id."),
    commit: str | None = typer.Option(None, "--commit", help="Commit hash for the task."),
    deviation: str | None = typer.Option(None, "--deviation", help="Accepted deviation note."),
    story_dir: str = typer.Option(..., "--story-dir", help="Resolved project stories root."),
) -> None:
    """Write the structured `.handoff-context` for one story/task."""
    args = [
        "--story-dir", story_dir,
        "update",
        "--story", story,
        "--task-id", task_id,
        "--phase", phase,
        "--next-action", next_action,
    ]
    if worker_agent_id is not None:
        args += ["--worker-agent-id", worker_agent_id]
    if reviewer_agent_id is not None:
        args += ["--reviewer-agent-id", reviewer_agent_id]
    if commit is not None:
        args += ["--commit", commit]
    if deviation is not None:
        args += ["--deviation", deviation]
    _run("handoff.py", args)


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


@review_app.command("create")
def review_create(
    story: str = typer.Option(..., "--story", help="Story slug or <YYYY-MM-DD>-<slug>."),
    task_id: str = typer.Option(..., "--task-id", help="Task id, e.g. '01'."),
    additional: str | None = typer.Option(None, "--additional", help="Extra task-specific review instructions."),
    out: str | None = typer.Option(None, "--out", help="Output path for the rendered review prompt."),
    story_dir: str = typer.Option(..., "--story-dir", help="Resolved project stories root."),
) -> None:
    """Render a task context fragment for code review dispatch."""
    args = [
        "--story-dir", story_dir,
        "create",
        "--story", story,
        "--task-id", task_id,
    ]
    if additional is not None:
        args += ["--additional", additional]
    if out is not None:
        args += ["--out", out]
    _run("review.py", args)


@story_app.command("summarize")
def story_summarize(
    story: str = typer.Argument(..., help="Story slug or <YYYY-MM-DD>-<slug>."),
    story_dir: str = typer.Option(..., "--story-dir", help="Resolved project stories root."),
) -> None:
    """Aggregate task usage by wave, role, and model."""
    _run("story.py", ["--story-dir", story_dir, "summarize", "--story", story])


@task_app.command("update")
def task_update(
    story: str = typer.Option(..., "--story", help="Story slug or <YYYY-MM-DD>-<slug>."),
    id: str = typer.Option(..., "--id", help="Task id, e.g. '01'."),
    status: str | None = typer.Option(None, "--status", help="pending|executing|reviewing|testing|completed|blocked."),
    worker: str | None = typer.Option(None, "--worker", help="Worker identifier."),
    reviewer: str | None = typer.Option(None, "--reviewer", help="Reviewer identifier."),
    commit: str | None = typer.Option(None, "--commit", help="Commit hash to append."),
    note: str | None = typer.Option(None, "--note", help="Replace the notes field."),
    usage_kind: str | None = typer.Option(None, "--usage-kind", help="worker|reviewer."),
    model: str | None = typer.Option(None, "--model", help="Model name for usage metrics."),
    tokens: int | None = typer.Option(None, "--tokens", help="Total tokens for the run."),
    tool_uses: int | None = typer.Option(None, "--tool-uses", help="Tool call count for the run."),
    duration_ms: int | None = typer.Option(None, "--duration-ms", help="Duration in milliseconds."),
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
    if usage_kind is not None:
        args += ["--usage-kind", usage_kind]
    if model is not None:
        args += ["--model", model]
    if tokens is not None:
        args += ["--tokens", str(tokens)]
    if tool_uses is not None:
        args += ["--tool-uses", str(tool_uses)]
    if duration_ms is not None:
        args += ["--duration-ms", str(duration_ms)]
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


if __name__ == "__main__":
    app()
