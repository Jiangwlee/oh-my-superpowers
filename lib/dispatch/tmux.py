"""Thin subprocess wrappers around tmux."""

from __future__ import annotations

import subprocess


def new_session(session_name: str, command: str, *, cwd: str | None = None) -> None:
    """Create a detached tmux session that runs `command` and exits."""
    args = ["tmux", "new-session", "-d", "-s", session_name]
    if cwd:
        args += ["-c", cwd]
    args.append(f"{command}; exit")
    subprocess.run(args, check=True)


def has_session(session_name: str) -> bool:
    """Check whether a tmux session exists."""
    return (
        subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
        ).returncode
        == 0
    )


def kill_session(session_name: str) -> bool:
    """Kill a tmux session. Returns True if the session existed and was killed."""
    return (
        subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            capture_output=True,
        ).returncode
        == 0
    )


def list_sessions(prefix: str = "omp-") -> list[tuple[str, int]]:
    """List active tmux sessions filtered by prefix.

    Returns a list of (session_name, last_activity_epoch) tuples. Returns
    an empty list when no sessions exist or tmux is not running.
    """
    proc = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name} #{session_activity}"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return []
    out: list[tuple[str, int]] = []
    for line in proc.stdout.splitlines():
        name, _, activity = line.partition(" ")
        if not name.startswith(prefix):
            continue
        try:
            out.append((name, int(activity)))
        except ValueError:
            out.append((name, 0))
    return out
