#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer"]
# ///
"""omp mail-pipeline — Turn IMAP mailboxes into structured local outputs."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import typer

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))
SCRIPTS = OMP_HOME / "skills" / "mail-pipeline" / "scripts"

app = typer.Typer(
    name="mail-pipeline",
    help="Process IMAP mailboxes into JSONL events, files, and audit state.",
    no_args_is_help=True,
    add_completion=False,
)
accounts_app = typer.Typer(
    name="accounts",
    help="List and validate configured mailbox accounts.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(accounts_app, name="accounts")
mailbox_app = typer.Typer(
    name="mailbox",
    help="Explicit mailbox actions decided by the calling agent.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(mailbox_app, name="mailbox")


def _run(script: str, args: list[str]) -> None:
    path = SCRIPTS / script
    sys.exit(subprocess.call(["uv", "run", str(path), *args]))


@app.command()
def init(
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Preview by default; use --apply to write."),
) -> None:
    """Create the mail-pipeline data directory and config templates."""
    args: list[str] = []
    if dry_run:
        args.append("--dry-run")
    _run("init.py", args)


@accounts_app.command("list")
def accounts_list(
    account: str = typer.Option("all", "--account", help="Account id or 'all'."),
) -> None:
    """List configured account IDs without printing secrets."""
    _run("accounts.py", ["list", "--account", account])


@accounts_app.command("check")
def accounts_check(
    account: str = typer.Option("all", "--account", help="Account id or 'all'."),
) -> None:
    """Validate IMAP connectivity for configured accounts."""
    _run("accounts.py", ["check", "--account", account])


@app.command()
def run(
    account: str = typer.Option("all", "--account", help="Account id or 'all'."),
    processor: str = typer.Option("all", "--processor", help="Processor name or 'all'."),
    limit: int = typer.Option(50, "--limit", help="Maximum messages per account."),
    fixture_dir: str | None = typer.Option(None, "--fixture-dir", help="Read local .eml files instead of IMAP."),
    apply: bool = typer.Option(False, "--apply", help="Write files/state and allowed mailbox changes."),
    since: str | None = typer.Option(None, "--since", help="Only process messages dated on/after this day (YYYY-MM-DD)."),
) -> None:
    """Process messages through configured processors. Defaults to dry-run."""
    args = ["--account", account, "--processor", processor, "--limit", str(limit)]
    if fixture_dir:
        args += ["--fixture-dir", fixture_dir]
    if apply:
        args.append("--apply")
    if since:
        args += ["--since", since]
    _run("run.py", args)


@app.command()
def submit(
    id: str = typer.Option(..., "--id", help="Pending extraction id from `run` output or `status`."),
    fields: str | None = typer.Option(None, "--fields", help="Extracted invoice fields as a JSON object string."),
    invoice_file: str | None = typer.Option(None, "--invoice-file", help="Filename of the invoice PDF when multiple files were staged; it receives the clean rendered name."),
    discard: bool = typer.Option(False, "--discard", help="Drop this pending item instead of finalizing (e.g. duplicate delivery)."),
    reason: str | None = typer.Option(None, "--reason", help="Reason for --discard; recorded in the audit event."),
) -> None:
    """Submit agent-extracted fields for a pending message: validate, rename, finalize."""
    args = ["--id", id]
    if fields:
        args += ["--fields", fields]
    if invoice_file:
        args += ["--invoice-file", invoice_file]
    if discard:
        args.append("--discard")
    if reason:
        args += ["--reason", reason]
    _run("submit.py", args)


@mailbox_app.command("mark-read")
def mailbox_mark_read(
    account: str = typer.Option(..., "--account", help="Account id."),
    uid: list[str] = typer.Option(..., "--uid", help="IMAP uid in the account inbox (repeatable)."),
    reason: str | None = typer.Option(None, "--reason", help="Why the agent decided this; recorded in the audit event."),
) -> None:
    """Mark messages as read (\\Seen)."""
    args = ["mark-read", "--account", account]
    for value in uid:
        args += ["--uid", value]
    if reason:
        args += ["--reason", reason]
    _run("mailbox.py", args)


@mailbox_app.command("move")
def mailbox_move(
    account: str = typer.Option(..., "--account", help="Account id."),
    uid: list[str] = typer.Option(..., "--uid", help="IMAP uid in the account inbox (repeatable)."),
    to: str = typer.Option("trash", "--to", help="Logical target folder from the account folders map."),
    reason: str | None = typer.Option(None, "--reason", help="Why the agent decided this; recorded in the audit event."),
) -> None:
    """Move messages to a configured folder (e.g. trash)."""
    args = ["move", "--account", account, "--to", to]
    for value in uid:
        args += ["--uid", value]
    if reason:
        args += ["--reason", reason]
    _run("mailbox.py", args)


@app.command()
def status() -> None:
    """Report recent runs, output files, and state summary."""
    _run("status.py", [])


if __name__ == "__main__":
    app()
