#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp container — Unified lifecycle for omp's resident containers.

Single source of truth for starting/stopping the resident containers under
``$OMP_HOME/docker/<name>/``. This is the ONLY entry point for container
lifecycle; per-tool CLIs (e.g. html-serve) own content operations, not up/down.

Two runtime backends, picked automatically: docker compose when ``docker`` is
on PATH, otherwise apple/container (macOS 26+). The apple backend has no
compose, so each supported container carries an explicit run spec that must
stay semantically identical to its compose.yaml.
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


def _docker_usable() -> bool:
    # PATH presence is not enough: on macOS the docker CLI often lingers while
    # Docker Desktop is stopped, and the compose plugin may be missing. Probe
    # the daemon so an unusable docker falls through to the apple backend.
    try:
        for argv in (
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            ["docker", "compose", "version"],
        ):
            probe = subprocess.run(
                argv, check=False, capture_output=True, text=True, timeout=10
            )
            if probe.returncode != 0:
                return False
        return True
    except subprocess.TimeoutExpired:
        return False


def _runtime() -> str:
    forced = os.environ.get("OMP_CONTAINER_RUNTIME", "")
    if forced in ("docker", "apple"):
        binary = "docker" if forced == "docker" else "container"
        if shutil.which(binary) is None:
            typer.echo(
                json.dumps({"status": "error",
                            "message": f"OMP_CONTAINER_RUNTIME={forced} but {binary} not on PATH"}),
                err=True,
            )
            raise typer.Exit(4)
        return forced
    if shutil.which("docker") and _docker_usable():
        return "docker"
    if shutil.which("container"):
        return "apple"
    typer.echo(
        json.dumps({"status": "error",
                    "message": "no usable container runtime (docker daemon down/absent, "
                               "container (apple) not found); set OMP_CONTAINER_RUNTIME to force"}),
        err=True,
    )
    raise typer.Exit(4)


def _run_compose(name: str, args: list[str]) -> dict[str, Any]:
    compose_dir = _compose_dir(name)
    if not compose_dir.is_dir():
        typer.echo(
            json.dumps({"status": "error", "message": f"compose dir not found: {compose_dir}"}),
            err=True,
        )
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


# apple/container has no compose; this spec mirrors docker/browser-container/
# compose.yaml and must be kept in sync with it.
_APPLE_SPECS: dict[str, dict[str, Any]] = {
    "browser": {
        "image": "omp-browser-container:local",
        "container": "omp-browser",
        "volume": ("omp-browser-profile", "/data/profile"),
        "tmpfs": "/data/downloads",
        "shm": "1g",
        "env_passthrough": ["OMP_BROWSER_TOKEN"],
        # (env var, default host port, container port)
        "ports": [
            ("REST_PORT", "8080", "8080"),
            ("MCP_PORT", "9223", "9223"),
            ("VNC_VIEWONLY_PORT", "6080", "6080"),
            ("VNC_INTERACTIVE_PORT", "6081", "6081"),
        ],
    },
}


def _env_or(name: str, default: str) -> str:
    # compose ${VAR:-default} semantics: empty counts as unset. A plain
    # environ.get would let BIND_ADDR="" publish password-less VNC on all
    # interfaces.
    return os.environ.get(name) or default


def _apple_run_argv(spec: dict[str, Any]) -> list[str]:
    bind = _env_or("BIND_ADDR", "127.0.0.1")
    volume_name, volume_path = spec["volume"]
    argv = [
        "container", "run", "-d",
        "--name", spec["container"],
        "--shm-size", spec["shm"],
        "-v", f"{volume_name}:{volume_path}",
        "--tmpfs", spec["tmpfs"],
    ]
    for env_name in spec["env_passthrough"]:
        argv += ["-e", f"{env_name}={os.environ.get(env_name, '')}"]
    for env_name, default, container_port in spec["ports"]:
        argv += ["-p", f"{bind}:{_env_or(env_name, default)}:{container_port}"]
    argv.append(spec["image"])
    return argv


def _apple_lifecycle(
    name: str, action: str, build: bool = True, tail: int | None = None
) -> dict[str, Any]:
    spec = _APPLE_SPECS.get(name)
    if spec is None:
        typer.echo(
            json.dumps(
                {"status": "error",
                 "message": f"{name} is not supported on the apple/container backend",
                 "supported": sorted(_APPLE_SPECS)},
                ensure_ascii=False,
            ),
            err=True,
        )
        raise typer.Exit(2)
    compose_dir = _compose_dir(name)
    if not compose_dir.is_dir():
        typer.echo(
            json.dumps({"status": "error", "message": f"container dir not found: {compose_dir}"}),
            err=True,
        )
        raise typer.Exit(4)

    # (argv, tolerate) — tolerate names the ONLY failure a step may swallow:
    # "exists" for volume create on an existing volume, "absent" for stop/rm
    # on a missing container. Any other failure aborts the step chain — an
    # operational volume-create error must not proceed to stop/rm and take a
    # working service offline.
    steps: list[tuple[list[str], bool | str]] = []
    if action in ("up", "restart"):
        if build and action == "up":
            steps.append((["container", "build", "-t", spec["image"], "."], False))
        steps.append((["container", "volume", "create", spec["volume"][0]], "exists"))
        steps.append((["container", "stop", spec["container"]], "absent"))
        steps.append((["container", "rm", spec["container"]], "absent"))
        steps.append((_apple_run_argv(spec), False))
    elif action == "down":
        # down on an absent container is a no-op success, matching
        # `docker compose down` semantics (and keeping restart sane).
        steps.append((["container", "stop", spec["container"]], "absent"))
        steps.append((["container", "rm", spec["container"]], "absent"))
    elif action == "logs":
        argv = ["container", "logs"]
        if tail is not None:
            argv += ["-n", str(tail)]
        steps.append((argv + [spec["container"]], False))
    elif action == "ps":
        steps.append((["container", "inspect", spec["container"]], False))

    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    returncode = 0
    for argv, tolerate in steps:
        result = subprocess.run(
            argv, cwd=compose_dir, check=False, capture_output=True, text=True
        )
        if result.stdout.strip():
            stdout_parts.append(result.stdout.strip())
        if result.returncode != 0:
            stderr_lower = result.stderr.lower()
            tolerated = (
                tolerate is True
                or (tolerate == "absent" and "notfound" in stderr_lower)
                or (tolerate == "exists" and "already exists" in stderr_lower)
            )
            if not tolerated:
                returncode = result.returncode
                if result.stderr.strip():
                    stderr_parts.append(result.stderr.strip())
                break
    return {
        "status": "ok" if returncode == 0 else "error",
        "returncode": returncode,
        "stdout": "\n".join(stdout_parts),
        "stderr": "\n".join(stderr_parts),
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
    if _runtime() == "apple":
        payload = _apple_lifecycle(name, "up", build=build)
    else:
        payload = _run_compose(name, ["up", "-d"] + (["--build"] if build else []))
    _print(payload)
    if payload["returncode"] != 0:
        raise typer.Exit(1)


@app.command("down")
def down(name: str = typer.Argument(..., help="Container name.")) -> None:
    """Stop and remove a container."""
    if _runtime() == "apple":
        payload = _apple_lifecycle(name, "down")
    else:
        payload = _run_compose(name, ["down"])
    _print(payload)
    if payload["returncode"] != 0:
        raise typer.Exit(1)


@app.command("restart")
def restart(name: str = typer.Argument(..., help="Container name.")) -> None:
    """Restart a container (down then up)."""
    if _runtime() == "apple":
        down_payload = _apple_lifecycle(name, "down")
        up_payload = _apple_lifecycle(name, "restart")
    else:
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
    if _runtime() == "apple":
        payload = _apple_lifecycle(name, "logs", tail=tail)
    else:
        payload = _run_compose(name, ["logs", "--tail", str(tail)])
    _print(payload)
    if payload["returncode"] != 0:
        raise typer.Exit(1)


@app.command("health")
def health(name: str = typer.Argument(..., help="Container name.")) -> None:
    """Report container health (compose ps + HTTP health probe when defined)."""
    if _runtime() == "apple":
        ps = _apple_lifecycle(name, "ps")
    else:
        ps = _run_compose(name, ["ps", "--format", "json"])
    health_url = REGISTRY[name]["health"]
    probe: dict[str, Any] | None = None
    if health_url:
        url = str(health_url).replace("{REST_PORT}", _env_or("REST_PORT", "8080"))
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
