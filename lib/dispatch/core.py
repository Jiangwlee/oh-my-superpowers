"""High-level orchestration: spawn / wait / run / tail / status / kill."""

from __future__ import annotations

import os
import re
import secrets
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import tmux
from .clean import strip_ansi
from .runtime import VALID_RUNTIMES, build_runtime_command
from .wait import WaitResult, wait_for_many, wait_for_session

SESSION_PREFIX = "omp-"
_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]")


@dataclass
class SessionHandle:
    """Reference to a spawned tmux session."""

    session_id: str
    runtime: str
    output_file: str
    prompt_file: str
    cwd: str
    started_at: float


@dataclass
class SessionStatus:
    """Snapshot of an active dispatch session."""

    session_id: str
    last_activity_epoch: int


def _generate_session_id(custom: str | None = None) -> str:
    if custom:
        clean = _SAFE_NAME.sub("-", custom).strip("-")
        if not clean:
            raise ValueError(f"session_name reduces to empty after sanitization: {custom!r}")
        return f"{SESSION_PREFIX}{clean}"
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rand = secrets.token_hex(2)
    return f"{SESSION_PREFIX}{ts}-{rand}"


def _default_paths(session_id: str) -> tuple[str, str]:
    return (
        f"/tmp/{session_id}-prompt.md",
        f"/tmp/{session_id}-output.txt",
    )


def spawn(
    runtime: str,
    *,
    prompt: str | None = None,
    prompt_file: str | None = None,
    model: str | None = None,
    cwd: str | None = None,
    session_name: str | None = None,
    output_file: str | None = None,
) -> SessionHandle:
    """Start a runtime in a detached tmux session and return immediately.

    Either `prompt` (inline) or `prompt_file` (path) must be provided.
    `session_name` becomes `omp-<sanitized>`; otherwise a timestamped id is used.
    """
    if runtime not in VALID_RUNTIMES:
        raise ValueError(f"unsupported runtime: {runtime!r}")
    if not prompt and not prompt_file:
        raise ValueError("must provide prompt or prompt_file")
    if prompt and prompt_file:
        raise ValueError("prompt and prompt_file are mutually exclusive")

    session_id = _generate_session_id(session_name)
    if tmux.has_session(session_id):
        raise RuntimeError(f"tmux session already exists: {session_id}")

    cwd = cwd or os.getcwd()
    default_prompt, default_output = _default_paths(session_id)

    if prompt:
        prompt_file = default_prompt
        Path(prompt_file).write_text(prompt)
    else:
        if not Path(prompt_file).is_file():
            raise FileNotFoundError(f"prompt_file not found: {prompt_file}")

    if not output_file:
        output_file = default_output
    Path(output_file).touch()

    cmd = build_runtime_command(
        runtime, prompt_file=prompt_file, output_file=output_file, model=model
    )
    tmux.new_session(session_id, cmd, cwd=cwd)

    return SessionHandle(
        session_id=session_id,
        runtime=runtime,
        output_file=output_file,
        prompt_file=prompt_file,
        cwd=cwd,
        started_at=time.time(),
    )


def wait(
    handle_or_id: SessionHandle | str,
    output_file: str | None = None,
    *,
    timeout: int = 300,
    poll_interval: int = 5,
    on_progress: Callable[[dict], None] | None = None,
) -> WaitResult:
    """Block until a session ends, hits timeout, or vanishes."""
    if isinstance(handle_or_id, SessionHandle):
        sid = handle_or_id.session_id
        path = handle_or_id.output_file
    else:
        sid = handle_or_id
        path = output_file or _default_paths(sid)[1]
    return wait_for_session(
        sid, path, timeout=timeout, poll_interval=poll_interval, on_progress=on_progress
    )


def wait_many(
    handles: list[SessionHandle],
    *,
    mode: str = "all",
    timeout: int = 300,
    poll_interval: int = 5,
) -> list[WaitResult]:
    """Wait on multiple handles with all/any semantics."""
    ids = [h.session_id for h in handles]
    files = {h.session_id: h.output_file for h in handles}
    return wait_for_many(ids, files, mode=mode, timeout=timeout, poll_interval=poll_interval)


def run(
    runtime: str,
    *,
    prompt: str | None = None,
    prompt_file: str | None = None,
    model: str | None = None,
    cwd: str | None = None,
    session_name: str | None = None,
    output_file: str | None = None,
    timeout: int = 300,
    on_progress: Callable[[dict], None] | None = None,
) -> WaitResult:
    """Sugar for spawn + wait."""
    handle = spawn(
        runtime,
        prompt=prompt,
        prompt_file=prompt_file,
        model=model,
        cwd=cwd,
        session_name=session_name,
        output_file=output_file,
    )
    return wait(handle, timeout=timeout, on_progress=on_progress)


def tail(
    session_id: str,
    output_file: str | None = None,
    *,
    follow: bool = False,
    poll_interval: float = 1.0,
) -> Iterator[str]:
    """Yield ANSI-stripped output as it appears in the session's tee file.

    With follow=True, blocks until the tmux session ends; otherwise yields
    whatever is already on disk and returns.
    """
    path = output_file or _default_paths(session_id)[1]
    pos = 0

    def _read_new() -> str:
        nonlocal pos
        try:
            with open(path, "rb") as f:
                f.seek(pos)
                data = f.read()
                pos = f.tell()
        except FileNotFoundError:
            return ""
        if not data:
            return ""
        return strip_ansi(data.decode("utf-8", errors="replace"))

    chunk = _read_new()
    if chunk:
        yield chunk
    if not follow:
        return

    while tmux.has_session(session_id):
        time.sleep(poll_interval)
        chunk = _read_new()
        if chunk:
            yield chunk

    final = _read_new()
    if final:
        yield final


def status(session_id: str | None = None) -> list[SessionStatus]:
    """Return active dispatch sessions (filtered by `omp-` prefix)."""
    if session_id:
        if tmux.has_session(session_id):
            for name, activity in tmux.list_sessions(prefix=""):
                if name == session_id:
                    return [SessionStatus(name, activity)]
        return []
    return [SessionStatus(name, ts) for name, ts in tmux.list_sessions(prefix=SESSION_PREFIX)]


def kill(session_id: str) -> bool:
    """Kill a session. Returns True if it existed and was killed."""
    return tmux.kill_session(session_id)
