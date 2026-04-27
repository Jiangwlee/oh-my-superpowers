#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp dispatch — Project-level tmux dispatch primitive (claude/codex/pi)."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
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

sys.path.insert(0, str(OMP_HOME / "lib"))

from dispatch import (  # noqa: E402
    SessionHandle,
    VALID_RUNTIMES,
    WaitResult,
    kill as _kill,
    run as _run,
    spawn as _spawn,
    status as _status,
    strip_ansi,
    tail as _tail,
    wait as _wait,
)
from dispatch.wait import wait_for_many  # noqa: E402

app = typer.Typer(
    name="dispatch",
    help="Tmux dispatch primitive: spawn an AI runtime (claude/codex/pi) and observe it.",
    no_args_is_help=True,
    add_completion=False,
)


def _validate_runtime(runtime: str) -> None:
    if runtime not in VALID_RUNTIMES:
        typer.echo(
            f"error: runtime must be one of {', '.join(VALID_RUNTIMES)}, got '{runtime}'",
            err=True,
        )
        raise typer.Exit(2)


def _require_prompt(prompt: str | None, prompt_file: str | None) -> None:
    if not prompt and not prompt_file:
        typer.echo("error: provide either prompt or --prompt-file", err=True)
        raise typer.Exit(2)
    if prompt and prompt_file:
        typer.echo("error: prompt and --prompt-file are mutually exclusive", err=True)
        raise typer.Exit(2)


def _emit_progress(payload: dict) -> None:
    elapsed = payload.get("elapsed", 0)
    size = payload.get("size", 0)
    stalled = " STALLED" if payload.get("stalled") else ""
    typer.echo(f"[dispatch] elapsed={elapsed}s size={size}B{stalled}", err=True)


@app.command()
def run(
    runtime: str = typer.Argument(..., help="Runtime (claude|codex|pi)."),
    prompt: Optional[str] = typer.Argument(None, help="Inline prompt text."),
    prompt_file: Optional[str] = typer.Option(None, "--prompt-file", help="Read prompt from file."),
    model: Optional[str] = typer.Option(None, "--model", help="Override default model."),
    timeout: int = typer.Option(300, "--timeout", help="Seconds before kill."),
    cwd: Optional[str] = typer.Option(None, "--cwd", help="Worker working directory."),
    session_name: Optional[str] = typer.Option(
        None, "--session-name", help="Custom session name (will be prefixed with 'omp-')."
    ),
    output_file: Optional[str] = typer.Option(None, "--output-file", help="Write output to file."),
    progress: bool = typer.Option(False, "--progress", help="Emit heartbeat progress to stderr."),
) -> None:
    """Spawn → wait → return output (sugar for spawn + wait)."""
    _validate_runtime(runtime)
    _require_prompt(prompt, prompt_file)
    result = _run(
        runtime,
        prompt=prompt,
        prompt_file=prompt_file,
        model=model,
        cwd=cwd,
        session_name=session_name,
        output_file=output_file,
        timeout=timeout,
        on_progress=_emit_progress if progress else None,
    )
    typer.echo(result.output, nl=False)
    if result.status == "completed":
        raise typer.Exit(0)
    if result.status == "timeout":
        typer.echo(f"\n[dispatch] TIMEOUT after {timeout}s", err=True)
        raise typer.Exit(124)
    typer.echo(f"\n[dispatch] {result.status}", err=True)
    raise typer.Exit(1)


@app.command()
def spawn(
    runtime: str = typer.Argument(..., help="Runtime (claude|codex|pi)."),
    prompt: Optional[str] = typer.Argument(None, help="Inline prompt text."),
    prompt_file: Optional[str] = typer.Option(None, "--prompt-file", help="Read prompt from file."),
    model: Optional[str] = typer.Option(None, "--model", help="Override default model."),
    cwd: Optional[str] = typer.Option(None, "--cwd", help="Worker working directory."),
    session_name: Optional[str] = typer.Option(
        None, "--session-name", help="Custom session name (prefixed with 'omp-')."
    ),
    output_file: Optional[str] = typer.Option(None, "--output-file", help="Write output to file."),
    json_output: bool = typer.Option(False, "--json", help="Print handle as JSON instead of plain id."),
) -> None:
    """Spawn a session and return its id immediately (no wait)."""
    _validate_runtime(runtime)
    _require_prompt(prompt, prompt_file)
    handle = _spawn(
        runtime,
        prompt=prompt,
        prompt_file=prompt_file,
        model=model,
        cwd=cwd,
        session_name=session_name,
        output_file=output_file,
    )
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "session_id": handle.session_id,
                    "runtime": handle.runtime,
                    "output_file": handle.output_file,
                    "prompt_file": handle.prompt_file,
                    "cwd": handle.cwd,
                    "started_at": handle.started_at,
                }
            )
        )
    else:
        typer.echo(handle.session_id)


@app.command()
def wait(
    sessions: list[str] = typer.Argument(..., help="One or more session ids."),
    output_file: Optional[str] = typer.Option(
        None, "--output-file", help="Output file (single-session mode only)."
    ),
    mode: str = typer.Option("all", "--mode", help="Multi-session: 'all' or 'any'."),
    timeout: int = typer.Option(300, "--timeout", help="Seconds before kill."),
    progress: bool = typer.Option(False, "--progress", help="Emit heartbeat to stderr."),
    json_output: bool = typer.Option(False, "--json", help="Print results as JSON."),
) -> None:
    """Block until one or more sessions finish."""
    if mode not in ("all", "any"):
        typer.echo(f"error: --mode must be 'all' or 'any', got '{mode}'", err=True)
        raise typer.Exit(2)

    if len(sessions) == 1:
        result = _wait(
            sessions[0],
            output_file=output_file,
            timeout=timeout,
            on_progress=_emit_progress if progress else None,
        )
        results = [result]
    else:
        if output_file:
            typer.echo("error: --output-file only valid with a single session", err=True)
            raise typer.Exit(2)
        files = {sid: f"/tmp/{sid}-output.txt" for sid in sessions}
        results = wait_for_many(
            sessions, files, mode=mode, timeout=timeout, poll_interval=5
        )

    if json_output:
        typer.echo(
            json.dumps(
                [
                    {
                        "session_id": r.session_id,
                        "status": r.status,
                        "duration_secs": round(r.duration_secs, 2),
                        "output": r.output,
                    }
                    for r in results
                ]
            )
        )
    else:
        for r in results:
            if len(results) > 1:
                typer.echo(f"=== {r.session_id} [{r.status}] ===", err=True)
            typer.echo(r.output, nl=False)

    exit_code = 0
    for r in results:
        if r.status == "timeout":
            exit_code = max(exit_code, 124)
        elif r.status not in ("completed", "pending"):
            exit_code = max(exit_code, 1)
    raise typer.Exit(exit_code)


@app.command()
def tail(
    session: str = typer.Argument(..., help="Session id."),
    output_file: Optional[str] = typer.Option(None, "--output-file", help="Output file path."),
    follow: bool = typer.Option(False, "--follow", "-f", help="Stream until session ends."),
) -> None:
    """Print the session's output (use --follow to stream)."""
    for chunk in _tail(session, output_file=output_file, follow=follow):
        typer.echo(chunk, nl=False)


@app.command()
def status(
    session: Optional[str] = typer.Argument(None, help="Specific session id to query."),
    json_output: bool = typer.Option(False, "--json", help="Print as JSON."),
) -> None:
    """List active dispatch sessions (or query a specific one)."""
    rows = _status(session)
    if json_output:
        typer.echo(
            json.dumps(
                [
                    {"session_id": r.session_id, "last_activity": r.last_activity_epoch}
                    for r in rows
                ]
            )
        )
        raise typer.Exit(0 if rows else 1)
    if not rows:
        typer.echo("no active dispatch sessions" if not session else f"session '{session}' not found", err=True)
        raise typer.Exit(1)
    for r in rows:
        ts = datetime.fromtimestamp(r.last_activity_epoch).strftime("%Y-%m-%d %H:%M:%S")
        typer.echo(f"{r.session_id}\t{ts}")


@app.command()
def kill(
    session: str = typer.Argument(..., help="Session id to kill."),
) -> None:
    """Kill a dispatch session."""
    if _kill(session):
        typer.echo(f"killed: {session}")
    else:
        typer.echo(f"not found or already gone: {session}", err=True)
        raise typer.Exit(1)


@app.command()
def clean(
    file: str = typer.Argument(..., help="File to strip ANSI escape sequences from."),
) -> None:
    """Strip ANSI escape sequences from a file (writes to stdout)."""
    text = Path(file).read_text(errors="replace")
    typer.echo(strip_ansi(text), nl=False)


if __name__ == "__main__":
    app()
