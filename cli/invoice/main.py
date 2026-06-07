#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer"]
# ///
"""omp invoice — Manage a unified invoice registry from configured local sources."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import typer

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))
SCRIPT = OMP_HOME / "skills" / "invoice" / "scripts" / "invoice.py"

app = typer.Typer(
    name="invoice",
    help="Manage a unified invoice registry from configured local sources.",
    no_args_is_help=True,
    add_completion=False,
)


def _run(args: list[str]) -> None:
    sys.exit(subprocess.call(["uv", "run", str(SCRIPT), *args]))


@app.command()
def init(
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Preview by default; use --apply to write."),
) -> None:
    """Create invoice data directories and config templates."""
    args: list[str] = ["init"]
    if dry_run:
        args.append("--dry-run")
    _run(args)


@app.command()
def scan(
    source: str | None = typer.Option(None, "--source", help="Configured source id to scan; defaults to all."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum new files to import."),
) -> None:
    """Scan configured local directory sources and copy new files into pending."""
    args = ["scan"]
    if source:
        args += ["--source", source]
    if limit is not None:
        args += ["--limit", str(limit)]
    _run(args)


@app.command()
def add(
    file: str = typer.Argument(..., help="Invoice file to copy into pending."),
    owner: str = typer.Option(..., "--owner", help="Invoice owner."),
    source_id: str = typer.Option("manual", "--source-id", help="Audit source id for manual/external adds."),
) -> None:
    """Manually copy one invoice file into pending."""
    _run(["add", file, "--owner", owner, "--source-id", source_id])


@app.command("pending")
def pending() -> None:
    """List pending imported files awaiting agent extraction."""
    _run(["pending"])


@app.command()
def submit(
    id: str = typer.Option(..., "--id", help="Pending invoice id."),
    fields: str = typer.Option(..., "--fields", help="Extracted invoice fields as a JSON object string."),
    purpose: str = typer.Option(..., "--purpose", help="claim or substitute."),
) -> None:
    """Finalize one pending file into the invoice registry."""
    _run(["submit", "--id", id, "--fields", fields, "--purpose", purpose])


@app.command()
def discard(
    id: str = typer.Option(..., "--id", help="Pending invoice id."),
    reason: str = typer.Option(..., "--reason", help="Why this pending item should be discarded."),
) -> None:
    """Discard one pending file without touching the original source file."""
    _run(["discard", "--id", id, "--reason", reason])


@app.command("list")
def list_invoices(
    owner: str | None = typer.Option(None, "--owner", help="Filter by owner."),
    purpose: str | None = typer.Option(None, "--purpose", help="Filter by claim or substitute."),
    status: str | None = typer.Option("available", "--status", help="Filter by status; use 'all' for non-archived records."),
    since: str | None = typer.Option(None, "--since", help="Invoice date on/after YYYY-MM-DD."),
    until: str | None = typer.Option(None, "--until", help="Invoice date on/before YYYY-MM-DD."),
    include_archived: bool = typer.Option(False, "--include-archived", help="Include archived invoices in list output."),
) -> None:
    """List registered invoices."""
    args = ["list"]
    for key, value in {
        "--owner": owner,
        "--purpose": purpose,
        "--status": status,
        "--since": since,
        "--until": until,
    }.items():
        if value:
            args += [key, value]
    if include_archived:
        args.append("--include-archived")
    _run(args)


@app.command("mark-used")
def mark_used(
    invoice_number: str = typer.Option(..., "--invoice-number", help="Invoice number."),
    reason: str | None = typer.Option(None, "--reason", help="Usage reason or reimbursement reference."),
) -> None:
    """Mark an available invoice as used."""
    args = ["mark-used", "--invoice-number", invoice_number]
    if reason:
        args += ["--reason", reason]
    _run(args)


@app.command()
def archive(
    invoice_number: str = typer.Option(..., "--invoice-number", help="Invoice number."),
    reason: str | None = typer.Option(None, "--reason", help="Archive reason."),
) -> None:
    """Mark an invoice archived so default lists hide it."""
    args = ["archive", "--invoice-number", invoice_number]
    if reason:
        args += ["--reason", reason]
    _run(args)


@app.command()
def status() -> None:
    """Report registry readiness and counts."""
    _run(["status"])


if __name__ == "__main__":
    app()
