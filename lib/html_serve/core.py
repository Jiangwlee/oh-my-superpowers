"""Core helpers for the html-serve CLI."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class HtmlServeConfig:
    """Resolved html-serve publishing configuration."""

    data_dir: Path | None
    port: int
    localhost_base_url: str
    tailscale_base_url: str | None
    compose_dir: Path
    warnings: tuple[str, ...] = ()


class HtmlServeError(RuntimeError):
    """Base error for html-serve operations."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _load_env_file(path: Path) -> dict[str, str]:
    """Read a simple KEY=VALUE env file."""

    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _env_value(key: str, env_file: dict[str, str]) -> str | None:
    """Return environment value, falling back to docker/html-serve/.env."""

    value = os.environ.get(key)
    if value:
        return value
    return env_file.get(key)


def _derive_tailscale_base_url(port: int) -> tuple[str | None, str | None]:
    """Best-effort derive a Tailscale URL for this host."""

    tailscale_bin = shutil.which("tailscale")
    if not tailscale_bin:
        return None, "tailscale command not found; set HTML_SERVE_TAILSCALE_BASE_URL"

    try:
        status = subprocess.run(
            [tailscale_bin, "status", "--json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if status.returncode == 0 and status.stdout.strip():
            data = json.loads(status.stdout)
            dns_name = (data.get("Self") or {}).get("DNSName")
            if dns_name:
                return f"http://{dns_name.rstrip('.')}:{port}", None
    except (json.JSONDecodeError, OSError, subprocess.TimeoutExpired):
        pass

    try:
        ip_result = subprocess.run(
            [tailscale_bin, "ip", "-4"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, "failed to query tailscale ip; set HTML_SERVE_TAILSCALE_BASE_URL"

    ip = ip_result.stdout.strip().splitlines()[0] if ip_result.stdout.strip() else ""
    if ip_result.returncode == 0 and ip:
        return f"http://{ip}:{port}", None
    return None, "failed to query tailscale ip; set HTML_SERVE_TAILSCALE_BASE_URL"


def resolve_config(
    omp_home: Path,
    data_dir: str | None = None,
    localhost_base_url: str | None = None,
    tailscale_base_url: str | None = None,
    port: int | None = None,
) -> HtmlServeConfig:
    """Resolve html-serve config from CLI arguments, env, and docker .env."""

    compose_dir = omp_home / "docker" / "html-serve"
    env_file = _load_env_file(compose_dir / ".env")
    resolved_port = port or int(_env_value("HTML_SERVE_PORT", env_file) or "8888")
    resolved_data_dir = data_dir or _env_value("HTML_SERVE_DATA_DIR", env_file)
    local_base = localhost_base_url or f"http://localhost:{resolved_port}"

    tail_base = tailscale_base_url or _env_value("HTML_SERVE_TAILSCALE_BASE_URL", env_file)
    warnings: list[str] = []
    if not tail_base:
        base_url = _env_value("HTML_SERVE_BASE_URL", env_file)
        if base_url and "localhost" not in base_url and "127.0.0.1" not in base_url:
            tail_base = base_url
    if not tail_base:
        tail_base, warning = _derive_tailscale_base_url(resolved_port)
        if warning:
            warnings.append(warning)

    return HtmlServeConfig(
        data_dir=Path(resolved_data_dir).expanduser().resolve() if resolved_data_dir else None,
        port=resolved_port,
        localhost_base_url=local_base.rstrip("/"),
        tailscale_base_url=tail_base.rstrip("/") if tail_base else None,
        compose_dir=compose_dir,
        warnings=tuple(warnings),
    )


def normalize_relative_path(relative_path: str, require_html: bool = True) -> str:
    """Validate and normalize a publish path under html-serve root."""

    if "\\" in relative_path:
        raise HtmlServeError("--to must use forward slashes, not backslashes", 2)
    path = PurePosixPath(relative_path)
    if path.is_absolute():
        raise HtmlServeError("--to must be a relative path under HTML_SERVE_DATA_DIR", 2)
    if not relative_path.strip() or str(path) in {".", ""}:
        raise HtmlServeError("--to must name an output file", 2)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise HtmlServeError("--to must not contain empty, '.', or '..' path segments", 2)
    if require_html and path.suffix.lower() != ".html":
        raise HtmlServeError("--to must end with .html", 2)
    return path.as_posix()


def build_url(base_url: str, relative_path: str) -> str:
    """Build a URL from a base URL and a normalized relative path."""

    return base_url.rstrip("/") + "/" + urllib.parse.quote(relative_path, safe="/")


def verify_url(url: str, timeout: float = 3.0) -> bool:
    """Return whether an HTTP HEAD request succeeds with a 2xx/3xx status."""

    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 400
    except (OSError, urllib.error.URLError, urllib.error.HTTPError):
        return False


def publish_file(
    input_path: Path,
    config: HtmlServeConfig,
    relative_path: str,
    overwrite: bool = True,
    verify: bool = True,
) -> dict[str, object]:
    """Publish an HTML file under html-serve and return URL metadata."""

    if config.data_dir is None:
        raise HtmlServeError(
            "HTML_SERVE_DATA_DIR is not configured; set it in docker/html-serve/.env or the environment",
            4,
        )
    if not config.data_dir.is_dir():
        raise HtmlServeError(f"HTML_SERVE_DATA_DIR does not exist or is not a directory: {config.data_dir}", 4)
    if not os.access(config.data_dir, os.W_OK):
        raise HtmlServeError(f"HTML_SERVE_DATA_DIR is not writable: {config.data_dir}", 4)

    source = input_path.expanduser().resolve()
    if not source.is_file():
        raise HtmlServeError(f"input HTML file not found: {source}", 2)

    normalized = normalize_relative_path(relative_path)
    target = (config.data_dir / normalized).resolve()
    try:
        target.relative_to(config.data_dir)
    except ValueError as exc:
        raise HtmlServeError("resolved output path escaped HTML_SERVE_DATA_DIR", 2) from exc

    if target.exists() and not overwrite:
        raise HtmlServeError(f"target already exists: {target}", 1)

    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        shutil.copyfile(source, tmp_path)
        os.replace(tmp_path, target)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    localhost_url = build_url(config.localhost_base_url, normalized)
    tailscale_url = build_url(config.tailscale_base_url, normalized) if config.tailscale_base_url else ""
    verified = {
        "localhost": verify_url(localhost_url) if verify else None,
        "tailscale": verify_url(tailscale_url) if verify and tailscale_url else None,
    }

    return {
        "status": "ok",
        "html_path": str(target),
        "relative_path": normalized,
        "localhost_url": localhost_url,
        "tailscale_url": tailscale_url,
        "urls": {"localhost": localhost_url, "tailscale": tailscale_url},
        "verified": verified,
        "warnings": list(config.warnings),
    }


def url_metadata(config: HtmlServeConfig, relative_path: str, check: bool = False, verify: bool = False) -> dict[str, object]:
    """Return URL metadata for a path that may already be published."""

    normalized = normalize_relative_path(relative_path)
    localhost_url = build_url(config.localhost_base_url, normalized)
    tailscale_url = build_url(config.tailscale_base_url, normalized) if config.tailscale_base_url else ""
    exists = None
    if check:
        exists = bool(config.data_dir and (config.data_dir / normalized).is_file())
    return {
        "relative_path": normalized,
        "localhost_url": localhost_url,
        "tailscale_url": tailscale_url,
        "urls": {"localhost": localhost_url, "tailscale": tailscale_url},
        "exists": exists,
        "verified": {
            "localhost": verify_url(localhost_url) if verify else None,
            "tailscale": verify_url(tailscale_url) if verify and tailscale_url else None,
        },
        "warnings": list(config.warnings),
    }


def status_metadata(config: HtmlServeConfig, verify: bool = True) -> dict[str, object]:
    """Return current html-serve environment status."""

    local_root = config.localhost_base_url + "/"
    tail_root = config.tailscale_base_url + "/" if config.tailscale_base_url else ""
    return {
        "data_dir": str(config.data_dir) if config.data_dir else "",
        "data_dir_exists": bool(config.data_dir and config.data_dir.is_dir()),
        "data_dir_writable": bool(config.data_dir and config.data_dir.is_dir() and os.access(config.data_dir, os.W_OK)),
        "port": config.port,
        "localhost_url": local_root,
        "tailscale_url": tail_root,
        "urls": {"localhost": local_root, "tailscale": tail_root},
        "verified": {
            "localhost": verify_url(local_root) if verify else None,
            "tailscale": verify_url(tail_root) if verify and tail_root else None,
        },
        "compose_dir": str(config.compose_dir),
        "compose_dir_exists": config.compose_dir.is_dir(),
        "host": socket.gethostname(),
        "warnings": list(config.warnings),
    }


def run_compose(config: HtmlServeConfig, args: list[str]) -> dict[str, object]:
    """Run docker compose for the html-serve service."""

    if not config.compose_dir.is_dir():
        raise HtmlServeError(f"docker/html-serve directory not found: {config.compose_dir}", 4)
    if shutil.which("docker") is None:
        raise HtmlServeError("docker command not found", 4)
    result = subprocess.run(
        ["docker", "compose", *args],
        cwd=config.compose_dir,
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
