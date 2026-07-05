#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp container — Unified lifecycle for omp's docker containers.

Single source of truth for starting/stopping the resident containers under
``$OMP_HOME/docker/<name>/``. This is the ONLY entry point for container
lifecycle; per-tool CLIs (e.g. html-serve) own content operations, not up/down.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import typer

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))

# Registry: container name -> (compose dir under $OMP_HOME, optional health URL).
# health_url is checked by `omp container health <name>` when present.
REGISTRY: dict[str, dict[str, str | None]] = {
    "html-serve": {"dir": "docker/html-serve", "health": None},
    "browser": {
        "dir": "docker/browser-container",
        "health": "http://127.0.0.1:{REST_PORT}/health",
    },
}

app = typer.Typer(
    name="container",
    help="Unified lifecycle for omp docker containers (html-serve, browser).",
    no_args_is_help=True,
    add_completion=False,
)


def _print(payload: Any) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def _compose_dir(name: str) -> Path:
    if name not in REGISTRY:
        typer.echo(
            json.dumps(
                {"status": "error", "message": f"unknown container: {name}",
                 "known": sorted(REGISTRY)},
                ensure_ascii=False,
            ),
            err=True,
        )
        raise typer.Exit(2)
    return OMP_HOME / str(REGISTRY[name]["dir"])


def _run_compose(name: str, args: list[str]) -> dict[str, Any]:
    compose_dir = _compose_dir(name)
    if not compose_dir.is_dir():
        typer.echo(
            json.dumps({"status": "error", "message": f"compose dir not found: {compose_dir}"}),
            err=True,
        )
        raise typer.Exit(4)
    if shutil.which("docker") is None:
        typer.echo(json.dumps({"status": "error", "message": "docker command not found"}), err=True)
        raise typer.Exit(4)
    result = subprocess.run(
        ["docker", "compose", *args],
        cwd=compose_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "status": "ok" if result.returncode == 0 else "error",
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


@app.command("ls")
def ls() -> None:
    """List managed containers and whether their compose dir exists."""
    rows = []
    for name, meta in sorted(REGISTRY.items()):
        compose_dir = OMP_HOME / str(meta["dir"])
        rows.append({"name": name, "dir": str(compose_dir), "exists": compose_dir.is_dir()})
    _print(rows)


@app.command("up")
def up(
    name: str = typer.Argument(..., help="Container name (html-serve | browser)."),
    build: bool = typer.Option(True, "--build/--no-build", help="Build the image before starting."),
) -> None:
    """Start a container (building its image first by default)."""
    args = ["up", "-d"] + (["--build"] if build else [])
    payload = _run_compose(name, args)
    _print(payload)
    if payload["returncode"] != 0:
        raise typer.Exit(1)


@app.command("down")
def down(name: str = typer.Argument(..., help="Container name.")) -> None:
    """Stop and remove a container."""
    payload = _run_compose(name, ["down"])
    _print(payload)
    if payload["returncode"] != 0:
        raise typer.Exit(1)


@app.command("restart")
def restart(name: str = typer.Argument(..., help="Container name.")) -> None:
    """Restart a container (down then up)."""
    down_payload = _run_compose(name, ["down"])
    up_payload = _run_compose(name, ["up", "-d"])
    ok = down_payload["returncode"] == 0 and up_payload["returncode"] == 0
    _print({"status": "ok" if ok else "error", "down": down_payload, "up": up_payload})
    if not ok:
        raise typer.Exit(1)


@app.command("logs")
def logs(
    name: str = typer.Argument(..., help="Container name."),
    tail: int = typer.Option(100, "--tail", help="Number of trailing lines."),
) -> None:
    """Show recent container logs."""
    payload = _run_compose(name, ["logs", "--tail", str(tail)])
    _print(payload)
    if payload["returncode"] != 0:
        raise typer.Exit(1)


@app.command("health")
def health(name: str = typer.Argument(..., help="Container name.")) -> None:
    """Report container health (compose ps + HTTP health probe when defined)."""
    ps = _run_compose(name, ["ps", "--format", "json"])
    health_url = REGISTRY[name]["health"]
    probe: dict[str, Any] | None = None
    if health_url:
        url = str(health_url).replace("{REST_PORT}", os.environ.get("REST_PORT", "8080"))
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310 (localhost)
                probe = {"url": url, "status": resp.status, "body": json.loads(resp.read())}
        except (urllib.error.URLError, OSError, ValueError) as exc:
            probe = {"url": url, "status": "unreachable", "error": str(exc)}
    _print({"name": name, "ps": ps, "probe": probe})


if __name__ == "__main__":
    prog_name = os.environ.get("OMP_TOOL_PROG_NAME")
    if prog_name:
        app(prog_name=prog_name)
    else:
        app()
