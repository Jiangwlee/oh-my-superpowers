#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer"]
# ///
"""omp kickoff — Story / journal lifecycle helpers for the kickoff skill.

Domains:
  archive     → move aged / legacy stories to stories/archives/
  story init  → create a new story directory with story.md + journal.md skeleton
  status      → report current state of a story (task statuses, Evidence,
                open ISSUE, Phase 3 ready)

These commands keep high-frequency operations atomic and auditable. Free-form
journal updates are made directly by the developer; only state queries and
bootstrap go through the CLI.
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
    help="Story / journal lifecycle helpers for the kickoff skill.",
    no_args_is_help=True,
    add_completion=False,
)
story_app = typer.Typer(
    name="story",
    help="Story directory bootstrap.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(story_app, name="story")


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


@app.command()
def status(
    story_dir: str = typer.Option(..., "--story-dir", help="Resolved project stories root."),
    story: str | None = typer.Option(
        None, "--story",
        help="Story slug or '<YYYY-MM-DD>-<slug>'. Omit to use the most recent active story.",
    ),
) -> None:
    """Report the current state of a story.

    Prints task list with current state, Evidence completeness for the active
    in_progress task, open ISSUE list, uncommitted git changes, and a Phase 3
    ready judgment.
    """
    args = ["--story-dir", story_dir]
    if story is not None:
        args += ["--story", story]
    _run("status.py", args)


if __name__ == "__main__":
    app()
