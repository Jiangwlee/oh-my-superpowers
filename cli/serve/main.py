#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp serve — Local project workbench for skill development.

Thin Python launcher. The HTTP+WS server, the file/tree/chat APIs, the
Generative UI streaming and the static web app all live in the TypeScript
full-stack app under this same directory:

    server/   node HTTP+WS server (prebuilt to server/dist/index.js)
    web/      vanilla TS browser app (prebuilt to web/dist/)
    pty_helper.py  PTY subprocess the node terminal WS bridges to

This module keeps only:
  * the typer CLI lifecycle (start/stop/restart, foreground/background),
  * PID file + port management, background spawn, signal handling,
  * build-if-stale (runs `node build.mjs` when the prebuilt JS is missing or
    older than any source under server/ or web/),
  * spawning `node server/dist/index.js`, passing host/port/model/workspace.

Paths resolve relative to this file (the tool dir), not cwd. PID/log/session
files live under <workspace>/.omp/serve/.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from contextlib import suppress
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

TOOL_DIR = Path(__file__).resolve().parent
SERVER_DIR = TOOL_DIR / "server"
WEB_DIR = TOOL_DIR / "web"
BUILD_SCRIPT = TOOL_DIR / "build.mjs"
SERVER_BUNDLE = SERVER_DIR / "dist" / "index.js"
WEB_BUNDLE = WEB_DIR / "dist" / "bundle.js"
NODE_MODULES = TOOL_DIR / "node_modules"

console = Console(stderr=True)
app = typer.Typer(
    name="serve",
    help="Local project workbench for skill development.",
    no_args_is_help=False,
    add_completion=False,
    invoke_without_command=True,
)


# --- port / pid helpers ----------------------------------------------------
def _pids_on_port(port: int) -> list[int]:
    if shutil.which("fuser"):
        proc = subprocess.run(
            ["fuser", "-n", "tcp", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        return sorted({int(pid) for pid in re.findall(r"\d+", proc.stdout) if int(pid) != port})
    if shutil.which("lsof"):
        proc = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        return sorted({int(pid) for pid in re.findall(r"\d+", proc.stdout) if int(pid) != port})
    return []


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _serve_dir(workspace: Path) -> Path:
    return workspace.resolve() / ".omp" / "serve"


def _pid_file(workspace: Path, port: int) -> Path:
    return _serve_dir(workspace) / f"serve-{port}.pid"


def _log_file(workspace: Path, port: int) -> Path:
    return _serve_dir(workspace) / f"serve-{port}.log"


def _write_pid(workspace: Path, port: int, pid: int) -> None:
    pid_file = _pid_file(workspace, port)
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(f"{pid}\n", encoding="utf-8")


def _remove_pid(workspace: Path, port: int) -> None:
    with suppress(OSError):
        _pid_file(workspace, port).unlink()


def _stop_port(port: int, quiet: bool = False) -> bool:
    pids = _pids_on_port(port)
    if not pids:
        if not quiet:
            console.print(f"[omp serve] no process listening on port [cyan]{port}[/cyan]")
        return False

    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.time() + 3
    while time.time() < deadline:
        alive = [pid for pid in pids if _pid_exists(pid)]
        if not alive:
            if not quiet:
                console.print(f"[omp serve] stopped port [cyan]{port}[/cyan] ({', '.join(map(str, pids))})")
            return True
        time.sleep(0.1)

    for pid in pids:
        if not _pid_exists(pid):
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if not quiet:
        console.print(f"[omp serve] force stopped port [cyan]{port}[/cyan] ({', '.join(map(str, pids))})")
    return True


# --- build-if-stale --------------------------------------------------------
def _newest_source_mtime() -> float:
    """Latest mtime across all TS/CSS/HTML sources under server/ and web/.

    dist/ output is excluded so a build never marks its own inputs stale.
    """
    newest = 0.0
    for base in (SERVER_DIR, WEB_DIR):
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if "dist" in path.parts or not path.is_file():
                continue
            if path.suffix.lower() not in {".ts", ".tsx", ".css", ".html", ".mjs"}:
                continue
            with suppress(OSError):
                newest = max(newest, path.stat().st_mtime)
    with suppress(OSError):
        newest = max(newest, BUILD_SCRIPT.stat().st_mtime)
    return newest


def _build_is_stale() -> bool:
    if not SERVER_BUNDLE.is_file() or not WEB_BUNDLE.is_file():
        return True
    try:
        build_mtime = min(SERVER_BUNDLE.stat().st_mtime, WEB_BUNDLE.stat().st_mtime)
    except OSError:
        return True
    return _newest_source_mtime() > build_mtime


def _ensure_deps() -> None:
    """Install node deps on first run (node_modules is gitignored, not shipped)."""
    if NODE_MODULES.is_dir():
        return
    npm = shutil.which("npm")
    if not npm:
        console.print("[red][omp serve] npm not found in PATH; cannot install the TS app deps.[/red]")
        raise typer.Exit(1)
    console.print("[omp serve] installing TS app deps ([cyan]npm install[/cyan])...")
    proc = subprocess.run([npm, "install"], cwd=TOOL_DIR, check=False)
    if proc.returncode != 0:
        console.print("[red][omp serve] npm install failed.[/red]")
        raise typer.Exit(proc.returncode or 1)


def _ensure_build() -> None:
    if not _build_is_stale():
        return
    node = shutil.which("node")
    if not node:
        console.print("[red][omp serve] node not found in PATH; cannot build the TS app.[/red]")
        raise typer.Exit(1)
    _ensure_deps()
    console.print("[omp serve] building TS app ([cyan]node build.mjs[/cyan])...")
    proc = subprocess.run([node, str(BUILD_SCRIPT)], cwd=TOOL_DIR, check=False)
    if proc.returncode != 0:
        console.print("[red][omp serve] build failed.[/red]")
        raise typer.Exit(proc.returncode or 1)


def _node_cmd(host: str, port: int, model: str, workspace: Path) -> list[str]:
    node = shutil.which("node")
    if not node:
        console.print("[red][omp serve] node not found in PATH.[/red]")
        raise typer.Exit(1)
    return [
        node,
        str(SERVER_BUNDLE),
        "--workspace",
        str(workspace),
        "--host",
        host,
        "--port",
        str(port),
        "--model",
        model,
    ]


def _banner(root: Path, host: str, port: int, model: str) -> None:
    url = f"http://{host}:{port}/"
    console.print(f"[omp serve] workspace: [cyan]{root}[/cyan]")
    console.print(f"[omp serve] url: [bold]{url}[/bold]")
    console.print(f"[omp serve] server: [cyan]node {SERVER_BUNDLE}[/cyan]")
    console.print(f"[omp serve] log: [cyan]{_log_file(root, port)}[/cyan]")
    console.print(
        f"[omp serve] pi: [cyan]pi -p --mode json --approve --extension cli/serve/extensions/render_ui.ts "
        f"--session .omp/serve/sessions/<page>.jsonl --model {model} <message>[/cyan]"
    )


# --- foreground / background -----------------------------------------------
def _serve_foreground(
    workspace: Path,
    host: str,
    port: int,
    model: str,
    open_browser: bool,
) -> None:
    root = workspace.resolve()
    if not root.is_dir():
        console.print(f"[red]workspace not found:[/red] {root}")
        raise typer.Exit(1)
    _ensure_build()
    _serve_dir(root).mkdir(parents=True, exist_ok=True)
    _banner(root, host, port, model)

    proc = subprocess.Popen(_node_cmd(host, port, model, root), cwd=root)
    _write_pid(root, port, proc.pid)
    stop_requested = threading.Event()

    def request_stop(signum: int, _frame: Any) -> None:
        stop_requested.set()
        with suppress(ProcessLookupError):
            proc.terminate()

    previous_sigterm = signal.getsignal(signal.SIGTERM)
    previous_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGTERM, request_stop)
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(f"http://{host}:{port}/")).start()
    try:
        proc.wait()
    except KeyboardInterrupt:
        stop_requested.set()
        with suppress(ProcessLookupError):
            proc.terminate()
        with suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=3)
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
        signal.signal(signal.SIGINT, previous_sigint)
        if proc.poll() is None:
            with suppress(ProcessLookupError):
                proc.terminate()
            with suppress(subprocess.TimeoutExpired):
                proc.wait(timeout=3)
            if proc.poll() is None:
                with suppress(ProcessLookupError):
                    proc.kill()
                proc.wait()
        if stop_requested.is_set():
            console.print("\n[omp serve] stopped")
        _remove_pid(root, port)
    # Surface node startup/runtime failures (e.g. port already bound) instead of
    # silently returning success. Only when the user did not request a stop.
    rc = proc.returncode
    if not stop_requested.is_set() and rc:
        raise typer.Exit(rc if rc and rc > 0 else 1)


def _serve_background(
    workspace: Path,
    host: str,
    port: int,
    model: str,
    open_browser: bool,
) -> None:
    root = workspace.resolve()
    if not root.is_dir():
        console.print(f"[red]workspace not found:[/red] {root}")
        raise typer.Exit(1)
    if _pids_on_port(port):
        console.print(f"[yellow][omp serve] port {port} already has a listener; use restart or stop first.[/yellow]")
        raise typer.Exit(1)

    # Build synchronously up-front so the detached child starts fast (no
    # transpile-on-start) and build errors surface to the foreground caller.
    _ensure_build()

    serve_dir = _serve_dir(root)
    serve_dir.mkdir(parents=True, exist_ok=True)
    log_path = _log_file(root, port)
    stdout = log_path.open("ab")
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--workspace",
        str(root),
        "--host",
        host,
        "--port",
        str(port),
        "--model",
        model,
        "--foreground",
    ]
    cmd.append("--open" if open_browser else "--no-open")
    proc = subprocess.Popen(
        cmd,
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=stdout,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    stdout.close()
    deadline = time.time() + 8
    while time.time() < deadline:
        if proc.poll() is not None:
            console.print(f"[red][omp serve] failed to start; see log:[/red] {log_path}")
            raise typer.Exit(proc.returncode or 1)
        if _pids_on_port(port):
            break
        time.sleep(0.1)
    else:
        console.print(f"[yellow][omp serve] process started but port {port} was not observed yet.[/yellow]")

    _pid_file(root, port).write_text(f"{proc.pid}\n", encoding="utf-8")
    console.print(f"[omp serve] started in background: [cyan]pid {proc.pid}[/cyan]")
    console.print(f"[omp serve] workspace: [cyan]{root}[/cyan]")
    console.print(f"[omp serve] url: [bold]http://{host}:{port}/[/bold]")
    console.print(f"[omp serve] log: [cyan]{log_path}[/cyan]")


# --- CLI -------------------------------------------------------------------
@app.callback()
def _main(
    ctx: typer.Context,
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Project workspace root."),
    host: str = typer.Option("0.0.0.0", "--host", help="HTTP host."),
    port: int = typer.Option(8765, "--port", "-p", help="HTTP port."),
    model: str = typer.Option(
        os.environ.get("OMP_DEFAULT_MODEL_PI", "openai-codex/gpt-5.4-mini"),
        "--model",
        "-m",
        help="Pi model.",
    ),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser after start."),
    foreground: bool = typer.Option(False, "--foreground", help="Run in the foreground instead of background."),
) -> None:
    """Start the local skill development workbench."""
    if ctx.invoked_subcommand is None:
        if foreground:
            _serve_foreground(workspace, host, port, model, open_browser)
        else:
            _serve_background(workspace, host, port, model, open_browser)


@app.command()
def start(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Project workspace root."),
    host: str = typer.Option("0.0.0.0", "--host", help="HTTP host."),
    port: int = typer.Option(8765, "--port", "-p", help="HTTP port."),
    model: str = typer.Option(
        os.environ.get("OMP_DEFAULT_MODEL_PI", "openai-codex/gpt-5.4-mini"),
        "--model",
        "-m",
        help="Pi model.",
    ),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser after start."),
    foreground: bool = typer.Option(False, "--foreground", help="Run in the foreground instead of background."),
) -> None:
    """Start the local skill development workbench."""
    if foreground:
        _serve_foreground(workspace, host, port, model, open_browser)
    else:
        _serve_background(workspace, host, port, model, open_browser)


@app.command()
def stop(
    port: int = typer.Option(8765, "--port", "-p", help="HTTP port."),
) -> None:
    """Stop the workbench process listening on the port."""
    _stop_port(port)


@app.command()
def restart(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Project workspace root."),
    host: str = typer.Option("0.0.0.0", "--host", help="HTTP host."),
    port: int = typer.Option(8765, "--port", "-p", help="HTTP port."),
    model: str = typer.Option(
        os.environ.get("OMP_DEFAULT_MODEL_PI", "openai-codex/gpt-5.4-mini"),
        "--model",
        "-m",
        help="Pi model.",
    ),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser after start."),
    foreground: bool = typer.Option(False, "--foreground", help="Run in the foreground instead of background."),
) -> None:
    """Restart the local skill development workbench."""
    _stop_port(port, quiet=True)
    if foreground:
        _serve_foreground(workspace, host, port, model, open_browser)
    else:
        _serve_background(workspace, host, port, model, open_browser)


@app.command()
def dev(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Project workspace root."),
    host: str = typer.Option("0.0.0.0", "--host", help="HTTP host."),
    port: int = typer.Option(8765, "--port", "-p", help="HTTP port."),
    model: str = typer.Option(
        os.environ.get("OMP_DEFAULT_MODEL_PI", "openai-codex/gpt-5.4-mini"),
        "--model",
        "-m",
        help="Pi model.",
    ),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser after start."),
) -> None:
    """Compatibility alias for `omp serve`."""
    console.print("[yellow][omp serve] dev is deprecated; use `omp serve`.[/yellow]")
    _serve_foreground(workspace, host, port, model, open_browser)


if __name__ == "__main__":
    app()
