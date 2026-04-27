"""Session-wait primitives with heartbeat stall detection."""

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
    """Outcome of waiting on a tmux session."""

    session_id: str
    status: str  # 'completed' | 'timeout' | 'pending' (wait_many any-mode survivors)
    duration_secs: float
    output: str  # ANSI-stripped


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


def wait_for_session(
    session_id: str,
    output_file: str,
    *,
    timeout: int = 300,
    poll_interval: int = 5,
    stall_threshold: int = 6,
    on_progress: Callable[[dict], None] | None = None,
) -> WaitResult:
    """Block until a tmux session ends, hits timeout, or vanishes.

    Args:
        session_id: tmux session name.
        output_file: path the worker tees its output to (used for heartbeat).
        timeout: seconds before the session is killed and a TIMEOUT result
            is returned.
        poll_interval: seconds between polls.
        stall_threshold: number of consecutive polls with no output growth
            before `on_progress` reports `stalled=True`.
        on_progress: optional callback invoked every poll with
            `{elapsed, size, stalled}`.
    """
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

    return WaitResult(session_id, "completed", time.time() - start, _read_output(output_file))


def wait_for_many(
    session_ids: list[str],
    output_files: dict[str, str],
    *,
    mode: str = "all",
    timeout: int = 300,
    poll_interval: int = 5,
) -> list[WaitResult]:
    """Wait on multiple sessions with `all` or `any` semantics.

    `all` blocks until every session ends or timeout fires (survivors are
    killed). `any` returns as soon as the first session ends; remaining
    sessions are left running and reported with status='pending'.
    """
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
                finished[sid] = WaitResult(
                    sid, "completed", time.time() - start, _read_output(output_files[sid])
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
