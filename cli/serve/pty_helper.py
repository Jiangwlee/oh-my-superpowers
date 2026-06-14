#!/usr/bin/env python3
"""PTY helper for omp-serve terminal.

Spawned by the node server (server/pi/terminal.ts). Owns a real PTY running
`pi --approve --session <path> --model <model>` and bridges it to its parent
over a simple newline-delimited JSON protocol on stdin/stdout.

Protocol (parent <-> helper), one JSON object per line:
  parent -> helper (on this process's stdin):
    {"type": "input",  "data": "<utf-8 text>"}
    {"type": "resize", "rows": <int>, "cols": <int>}
  helper -> parent (on this process's stdout):
    {"type": "output", "data": "<utf-8 text>"}
    {"type": "exit",   "returncode": <int>}

The PTY logic (openpty, TIOCSWINSZ resize, select loop, process-group
teardown) is ported from main.py's _run_terminal_socket.

Args: --session <path> --model <model> [--cwd <dir>]
"""

from __future__ import annotations

import fcntl
import json
import os
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import termios
from contextlib import suppress


def _set_pty_size(fd: int, rows: int, cols: int) -> None:
    rows = max(1, min(int(rows or 24), 200))
    cols = max(1, min(int(cols or 80), 400))
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def _emit(obj: dict) -> None:
    try:
        sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except (BrokenPipeError, ValueError):
        pass


def _parse_args(argv: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    i = 0
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            out[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            i += 1
    return out


def _install_signal_handlers() -> None:
    # The node side terminates this helper with SIGTERM when the terminal
    # WebSocket closes. Python's default SIGTERM action exits the interpreter
    # immediately, skipping the finally block that kills pi's process group and
    # leaving an orphaned interactive pi process. Translate SIGTERM/SIGINT into
    # KeyboardInterrupt so the finally cleanup (killpg) always runs.
    def _raise(_signum, _frame):
        raise KeyboardInterrupt

    with suppress(ValueError, OSError):
        signal.signal(signal.SIGTERM, _raise)
        signal.signal(signal.SIGINT, _raise)


def main() -> int:
    _install_signal_handlers()
    args = _parse_args(sys.argv[1:])
    session = args.get("session")
    model = args.get("model")
    cwd = args.get("cwd") or os.getcwd()
    if not session or not model:
        _emit({"type": "output", "data": "session and model are required\r\n"})
        _emit({"type": "exit", "returncode": 1})
        return 1
    if not shutil.which("pi"):
        _emit({"type": "output", "data": "pi binary not found in PATH\r\n"})
        _emit({"type": "exit", "returncode": 1})
        return 1

    os.makedirs(os.path.dirname(session), exist_ok=True)

    master_fd: int | None = None
    proc: subprocess.Popen[bytes] | None = None
    stdin_fd = sys.stdin.fileno()
    in_buf = b""
    try:
        master_fd, slave_fd = pty.openpty()
        _set_pty_size(master_fd, 24, 80)
        env = os.environ.copy()
        env.update({"TERM": "xterm-256color", "COLORTERM": "truecolor"})
        cmd = ["pi", "--approve", "--session", session, "--model", model]
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            preexec_fn=os.setsid,
            close_fds=True,
        )
        os.close(slave_fd)

        while proc.poll() is None:
            readable, _, _ = select.select([master_fd, stdin_fd], [], [], 0.1)
            if master_fd in readable:
                try:
                    data = os.read(master_fd, 65536)
                except OSError:
                    break
                if data:
                    _emit({"type": "output", "data": data.decode("utf-8", errors="replace")})
            if stdin_fd in readable:
                try:
                    chunk = os.read(stdin_fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                in_buf += chunk
                while b"\n" in in_buf:
                    line, in_buf = in_buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    etype = event.get("type")
                    if etype == "input":
                        os.write(master_fd, str(event.get("data") or "").encode("utf-8"))
                    elif etype == "resize":
                        _set_pty_size(
                            master_fd,
                            int(event.get("rows") or 24),
                            int(event.get("cols") or 80),
                        )
        rc = proc.poll()
        if rc is not None:
            _emit({"type": "output", "data": f"\r\n[pi exited with {rc}]\r\n"})
    finally:
        if proc and proc.poll() is None:
            with suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                with suppress(ProcessLookupError):
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
        if master_fd is not None:
            with suppress(OSError):
                os.close(master_fd)
        _emit({"type": "exit", "returncode": (proc.returncode if proc else 1) or 0})
    return 0


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        sys.exit(main())
