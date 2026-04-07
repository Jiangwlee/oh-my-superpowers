#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp round-table — Multi-AI round table discussions."""

import os
import subprocess
import sys
from pathlib import Path

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

SCRIPTS_DIR = OMP_HOME / "skills" / "round-table" / "scripts"

app = typer.Typer(
    name="round-table",
    help="Multi-AI round table discussions.",
    no_args_is_help=True,
    add_completion=False,
)

# ---------------------------------------------------------------------------
# session 命名空间
# ---------------------------------------------------------------------------

session_app = typer.Typer(
    name="session",
    help="Session lifecycle management.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(session_app, name="session")


def _session(args: list[str]) -> None:
    sys.exit(subprocess.call(["bash", str(SCRIPTS_DIR / "session.sh")] + args))


@session_app.command()
def init(
    topic: str = typer.Argument(..., help="Discussion topic."),
    roles: str = typer.Option(..., "--roles", help="Comma-separated participant role IDs."),
    context: str | None = typer.Option(None, "--context", help="Context text or file path."),
) -> None:
    """Initialize a new round table session.

    Example:
        omp round-table session init "CLI architecture" --roles linus-torvalds,dhh,grace-hopper
    """
    cmd = ["init", topic, "--roles", roles]
    if context:
        cmd += ["--context", context]
    _session(cmd)


@session_app.command()
def status() -> None:
    """Show current session status.

    Example:
        omp round-table session status
    """
    _session(["status"])


@session_app.command()
def context(
    level: str = typer.Argument("brief", help="Detail level (brief|detail)."),
) -> None:
    """Get session context.

    Example:
        omp round-table session context brief
    """
    _session(["get-context", level])


@session_app.command()
def messages(
    msg_id: str | None = typer.Argument(None, help="Specific message ID."),
) -> None:
    """List session messages.

    Example:
        omp round-table session messages
    """
    cmd = ["get-messages"]
    if msg_id:
        cmd.append(msg_id)
    _session(cmd)


@session_app.command()
def end(
    output_dir: str = typer.Option(..., "--output-dir", help="Output directory for session record."),
) -> None:
    """End session and export record.

    Example:
        omp round-table session end --output-dir ./docs/round-table
    """
    _session(["end", "--output-dir", output_dir])


@session_app.command("post-message")
def post_message(
    role: str = typer.Argument(..., help="Participant role ID."),
    file: str = typer.Argument(..., help="Message file path."),
    round_num: int = typer.Option(..., "--round", help="Round number."),
    name: str = typer.Option(..., "--name", help="Participant display name."),
    action: str = typer.Option(..., "--action", help="Action type."),
    summary: str = typer.Option(..., "--summary", help="Message summary."),
) -> None:
    """Post a message to the session.

    Example:
        omp round-table session post-message linus-torvalds msg.md --round 1 --name "Linus" --action speak --summary "..."
    """
    _session([
        "post-message", role, file,
        "--round", str(round_num),
        "--name", name,
        "--action", action,
        "--summary", summary,
    ])


# ---------------------------------------------------------------------------
# round 命名空间
# ---------------------------------------------------------------------------

round_app = typer.Typer(
    name="round",
    help="Round-level operations (auto-detect current round).",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(round_app, name="round")


def _round(args: list[str]) -> None:
    sys.exit(subprocess.call(["bash", str(SCRIPTS_DIR / "round.sh")] + args))


@round_app.command()
def spawn() -> None:
    """Spawn participants for next round in parallel.

    Example:
        omp round-table round spawn
    """
    _round(["spawn"])


@round_app.command()
def collect() -> None:
    """Collect and parse current round responses.

    Example:
        omp round-table round collect
    """
    _round(["collect"])


@round_app.command()
def run() -> None:
    """Spawn + wait + collect in one step.

    Example:
        omp round-table round run
    """
    _round(["run"])


@round_app.command()
def watch(
    follow: bool = typer.Option(False, "-f", "--follow", help="Follow output in real-time."),
) -> None:
    """Watch participant output in real-time.

    Example:
        omp round-table round watch -f
    """
    cmd = ["watch"]
    if follow:
        cmd.append("-f")
    _round(cmd)


@round_app.command()
def attach() -> None:
    """Attach to the tmux session.

    Example:
        omp round-table round attach
    """
    _round(["attach"])


if __name__ == "__main__":
    app()
