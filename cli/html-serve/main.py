#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp html-serve — Publish static HTML artifacts to the local html-serve container."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import typer

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))

# Load $OMP_HOME/.env without overriding the shell environment.
_env_file = OMP_HOME / ".env"
if _env_file.is_file():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

sys.path.insert(0, str(OMP_HOME / "lib"))

from html_serve.core import (  # noqa: E402
    HtmlServeConfig,
    HtmlServeError,
    list_entries,
    publish_file,
    reindex_manifest,
    resolve_config,
    run_compose,
    status_metadata,
    url_metadata,
)

app = typer.Typer(
    name="html-serve",
    help="Publish static HTML artifacts to html-serve and return localhost + Tailscale URLs.",
    no_args_is_help=True,
    add_completion=False,
)


def _print_json(payload: dict[str, Any]) -> None:
    """Print machine-readable JSON to stdout."""

    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def _config(
    data_dir: str | None = None,
    localhost_base_url: str | None = None,
    tailscale_base_url: str | None = None,
    port: int | None = None,
) -> HtmlServeConfig:
    """Resolve config for a command."""

    return resolve_config(
        omp_home=OMP_HOME,
        data_dir=data_dir,
        localhost_base_url=localhost_base_url,
        tailscale_base_url=tailscale_base_url,
        port=port,
    )


def _fail(exc: HtmlServeError) -> None:
    """Render a CLI error and exit with the mapped code."""

    print(f"html-serve: {exc}", file=sys.stderr)
    raise typer.Exit(exc.exit_code)


@app.command()
def publish(
    input_html: str = typer.Argument(..., help="Local HTML file to publish."),
    to: str = typer.Option(..., "--to", help="Relative output path under HTML_SERVE_DATA_DIR, ending in .html."),
    data_dir: str | None = typer.Option(None, "--data-dir", help="Override HTML_SERVE_DATA_DIR."),
    localhost_base_url: str | None = typer.Option(None, "--localhost-base-url", help="Override localhost URL base."),
    tailscale_base_url: str | None = typer.Option(None, "--tailscale-base-url", help="Override Tailscale URL base."),
    port: int | None = typer.Option(None, "--port", help="Override HTML_SERVE_PORT for generated URLs."),
    overwrite: bool = typer.Option(True, "--overwrite/--no-overwrite", help="Overwrite an existing target file."),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Verify returned URLs with HTTP HEAD."),
    title: str | None = typer.Option(None, "--title", help="Manifest title; defaults to the HTML <title>."),
    tag: list[str] = typer.Option([], "--tag", help="Manifest tag; repeatable."),
    source: str | None = typer.Option(None, "--source", help="Manifest source name (e.g. the publishing skill)."),
) -> None:
    """Copy one HTML file into html-serve and print localhost + Tailscale URLs.

    Example:
        omp html-serve publish /tmp/report.html --to reports/2026-06-13.html
    """

    try:
        payload = publish_file(
            input_path=Path(input_html),
            config=_config(data_dir, localhost_base_url, tailscale_base_url, port),
            relative_path=to,
            overwrite=overwrite,
            verify=verify,
            title=title,
            tags=tag,
            source_name=source,
        )
    except HtmlServeError as exc:
        _fail(exc)
    _print_json(payload)


@app.command("url")
def build_url(
    relative_path: str = typer.Argument(..., help="Relative path under HTML_SERVE_DATA_DIR."),
    data_dir: str | None = typer.Option(None, "--data-dir", help="Override HTML_SERVE_DATA_DIR."),
    localhost_base_url: str | None = typer.Option(None, "--localhost-base-url", help="Override localhost URL base."),
    tailscale_base_url: str | None = typer.Option(None, "--tailscale-base-url", help="Override Tailscale URL base."),
    port: int | None = typer.Option(None, "--port", help="Override HTML_SERVE_PORT for generated URLs."),
    check: bool = typer.Option(False, "--check", help="Check whether the file exists under HTML_SERVE_DATA_DIR."),
    verify: bool = typer.Option(False, "--verify", help="Verify returned URLs with HTTP HEAD."),
) -> None:
    """Return localhost + Tailscale URLs for a published relative path.

    Example:
        omp html-serve url reports/2026-06-13.html --check
    """

    try:
        payload = url_metadata(
            config=_config(data_dir, localhost_base_url, tailscale_base_url, port),
            relative_path=relative_path,
            check=check,
            verify=verify,
        )
    except HtmlServeError as exc:
        _fail(exc)
    _print_json(payload)


@app.command("list")
def list_published(
    under: str | None = typer.Option(None, "--under", help="Only entries under this relative directory."),
    since: str | None = typer.Option(None, "--since", help="Only entries published on/after this date (YYYY-MM-DD)."),
    until: str | None = typer.Option(None, "--until", help="Only entries published on/before this date (YYYY-MM-DD)."),
    grep: str | None = typer.Option(None, "--grep", help="Case-insensitive regex matched against file content and title."),
    tag: list[str] = typer.Option([], "--tag", help="Only entries carrying any of these tags; repeatable."),
    data_dir: str | None = typer.Option(None, "--data-dir", help="Override HTML_SERVE_DATA_DIR."),
) -> None:
    """List published files with paths, URLs, and manifest metadata.

    Example:
        omp html-serve list --under ai-daily --since 2026-06-01 --grep 知识库
    """

    try:
        entries = list_entries(_config(data_dir), under=under, since=since, until=until, grep=grep, tags=tag)
    except HtmlServeError as exc:
        _fail(exc)
    _print_json({"status": "ok", "count": len(entries), "entries": entries})


@app.command()
def reindex(
    data_dir: str | None = typer.Option(None, "--data-dir", help="Override HTML_SERVE_DATA_DIR."),
) -> None:
    """Rebuild the manifest from files currently on disk, keeping known tags/sources.

    Example:
        omp html-serve reindex
    """

    try:
        payload = reindex_manifest(_config(data_dir))
    except HtmlServeError as exc:
        _fail(exc)
    _print_json(payload)


@app.command()
def status(
    data_dir: str | None = typer.Option(None, "--data-dir", help="Override HTML_SERVE_DATA_DIR."),
    localhost_base_url: str | None = typer.Option(None, "--localhost-base-url", help="Override localhost URL base."),
    tailscale_base_url: str | None = typer.Option(None, "--tailscale-base-url", help="Override Tailscale URL base."),
    port: int | None = typer.Option(None, "--port", help="Override HTML_SERVE_PORT for generated URLs."),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Verify service roots with HTTP HEAD."),
) -> None:
    """Inspect html-serve config, paths, and URL reachability.

    Example:
        omp html-serve status
    """

    _print_json(status_metadata(_config(data_dir, localhost_base_url, tailscale_base_url, port), verify=verify))


@app.command()
def start() -> None:
    """Start the docker/html-serve nginx container.

    Example:
        omp html-serve start
    """

    try:
        payload = run_compose(_config(), ["up", "-d"])
    except HtmlServeError as exc:
        _fail(exc)
    _print_json(payload)
    if payload["returncode"] != 0:
        raise typer.Exit(1)


@app.command()
def stop() -> None:
    """Stop the docker/html-serve nginx container.

    Example:
        omp html-serve stop
    """

    try:
        payload = run_compose(_config(), ["down"])
    except HtmlServeError as exc:
        _fail(exc)
    _print_json(payload)
    if payload["returncode"] != 0:
        raise typer.Exit(1)


@app.command()
def restart() -> None:
    """Restart the docker/html-serve nginx container.

    Example:
        omp html-serve restart
    """

    try:
        down = run_compose(_config(), ["down"])
        up = run_compose(_config(), ["up", "-d"])
    except HtmlServeError as exc:
        _fail(exc)
    payload = {"status": "ok" if down["returncode"] == 0 and up["returncode"] == 0 else "error", "down": down, "up": up}
    _print_json(payload)
    if payload["status"] != "ok":
        raise typer.Exit(1)


if __name__ == "__main__":
    prog_name = os.environ.get("OMP_TOOL_PROG_NAME")
    if prog_name:
        app(prog_name=prog_name)
    else:
        app()
