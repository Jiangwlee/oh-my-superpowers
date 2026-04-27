"""Session-wait primitives with heartbeat + exit-code propagation."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import tmux
from .clean import strip_ansi


@dataclass
class WaitResult:
    """Outcome of waiting on a tmux session.

    Status semantics:
        completed — session ended naturally and worker exit code was 0 (or
                    the exit sidecar was missing, which we treat as success
                    so externally-spawned sessions don't false-fail).
        error    — session ended naturally and worker exit code was non-zero.
        timeout  — we killed the session after exceeding the timeout.
        pending  — wait_for_many `any`-mode survivor that wasn't waited for.
    """

    session_id: str
    status: str
    duration_secs: float
    output: str  # ANSI-stripped
    exit_code: int | None = None  # None when status is timeout/pending or sidecar missing


def _read_output(path: str) -> str:
    try:
        text = Path(path).read_text(errors="replace")
    except FileNotFoundError:
        return ""
    return strip_ansi(text)


def _file_size(path: str) -> int:
    try:
        return os.stat(path).st_size
    except FileNotFoundError:
        return 0


def _read_exit_code(session_id: str) -> int | None:
    """Read /tmp/{sid}.exit (written by the dispatch script under pipefail)."""
    try:
        raw = Path(f"/tmp/{session_id}.exit").read_text().strip()
    except FileNotFoundError:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _final_status(session_id: str) -> tuple[str, int | None]:
    """Map worker exit code to a status label after a session ends."""
    code = _read_exit_code(session_id)
    if code is None or code == 0:
        return "completed", code
    return "error", code


def wait_for_session(
    session_id: str,
    output_file: str,
    *,
    timeout: int = 300,
    poll_interval: int = 5,
    stall_threshold: int = 6,
    on_progress: Callable[[dict], None] | None = None,
) -> WaitResult:
    """Block until a tmux session ends, hits timeout, or vanishes."""
    start = time.time()
    elapsed = 0
    last_size = 0
    stall_count = 0

    while tmux.has_session(session_id):
        if elapsed >= timeout:
            tmux.kill_session(session_id)
            return WaitResult(
                session_id, "timeout", time.time() - start, _read_output(output_file)
            )

        curr_size = _file_size(output_file)
        if curr_size == last_size:
            stall_count += 1
        else:
            stall_count = 0
            last_size = curr_size

        if on_progress is not None:
            on_progress(
                {
                    "elapsed": elapsed,
                    "size": curr_size,
                    "stalled": stall_count >= stall_threshold,
                }
            )

        time.sleep(poll_interval)
        elapsed += poll_interval

    status, exit_code = _final_status(session_id)
    return WaitResult(
        session_id, status, time.time() - start, _read_output(output_file), exit_code=exit_code
    )


def wait_for_many(
    session_ids: list[str],
    output_files: dict[str, str],
    *,
    mode: str = "all",
    timeout: int = 300,
    poll_interval: int = 5,
) -> list[WaitResult]:
    """Wait on multiple sessions with `all` or `any` semantics."""
    if mode not in ("all", "any"):
        raise ValueError(f"mode must be 'all' or 'any', got {mode!r}")
    if not session_ids:
        return []

    start = time.time()
    elapsed = 0
    finished: dict[str, WaitResult] = {}

    while True:
        for sid in session_ids:
            if sid in finished:
                continue
            if not tmux.has_session(sid):
                status, exit_code = _final_status(sid)
                finished[sid] = WaitResult(
                    sid,
                    status,
                    time.time() - start,
                    _read_output(output_files[sid]),
                    exit_code=exit_code,
                )

        if mode == "any" and finished:
            results: list[WaitResult] = []
            for sid in session_ids:
                if sid in finished:
                    results.append(finished[sid])
                else:
                    results.append(WaitResult(sid, "pending", time.time() - start, ""))
            return results

        if mode == "all" and len(finished) == len(session_ids):
            return [finished[sid] for sid in session_ids]

        if elapsed >= timeout:
            for sid in session_ids:
                if sid in finished:
                    continue
                tmux.kill_session(sid)
                finished[sid] = WaitResult(
                    sid, "timeout", time.time() - start, _read_output(output_files[sid])
                )
            return [finished[sid] for sid in session_ids]

        time.sleep(poll_interval)
        elapsed += poll_interval
