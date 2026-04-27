"""omp dispatch — Project-level primitive for tmux-based runtime dispatch.

Public API:

    from dispatch import spawn, wait, wait_many, run, tail, status, kill, strip_ansi

    handle = spawn("codex", prompt="explain this code", cwd="/path/to/repo")
    for chunk in tail(handle.session_id, output_file=handle.output_file, follow=True):
        print(chunk, end="")
    result = wait(handle, timeout=600)
    print(result.output)

Used by `omp dispatch` CLI and may be imported by other `cli/<tool>/main.py` modules.
"""

from .clean import strip_ansi
from .core import (
    SessionHandle,
    WaitResult,
    kill,
    run,
    spawn,
    status,
    tail,
    wait,
    wait_many,
)
from .runtime import VALID_RUNTIMES, build_runtime_command

__all__ = [
    "SessionHandle",
    "VALID_RUNTIMES",
    "WaitResult",
    "build_runtime_command",
    "kill",
    "run",
    "spawn",
    "status",
    "strip_ansi",
    "tail",
    "wait",
    "wait_many",
]
