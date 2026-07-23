#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp web-operator — Browser automation, search, and content extraction."""

import os
import subprocess
import sys
import time
from pathlib import Path

import typer

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))

# 加载 .env
_env_file = OMP_HOME / ".env"
if _env_file.is_file():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

SKILL_DIR = OMP_HOME / "skills" / "web-operator"
SCRIPTS_DIR = SKILL_DIR / "scripts"
SITES_DIR = SCRIPTS_DIR / "sites"

app = typer.Typer(
    name="web-operator",
    help="Browser automation, search, and content extraction.",
    no_args_is_help=True,
    add_completion=False,
)


# ---------------------------------------------------------------------------
# page (CDP)
# ---------------------------------------------------------------------------


@app.command(
    "page",
    context_settings={
        "allow_extra_args": True,
        "allow_interspersed_args": False,
        "ignore_unknown_options": True,
    },
)
def page(ctx: typer.Context) -> None:
    """Interact with browser pages via CDP (list, nav, eval, snap, shot, html, click, scroll, type, open, stop...).

    Example:
        omp web-operator page list
        omp web-operator page nav "https://example.com"
        omp web-operator page snap
    """
    sys.exit(subprocess.call(["node", str(SCRIPTS_DIR / "cdp.mjs")] + ctx.args))


# ---------------------------------------------------------------------------
# up / ensure (browser bootstrap)
# ---------------------------------------------------------------------------
#
# The browser lifecycle's source of truth is an OS service (a systemd user unit
# by default). `up` never spawns Chrome itself — it only probes health and nudges
# that service — so the unit file stays the single owner of how Chrome launches
# (profile, proxy, GL, DISPLAY). Launcher backend and service name are config,
# not hard-coded, leaving a clean extension point for launchd/other hosts.

WEB_OPERATOR_SERVICE = os.environ.get("WEB_OPERATOR_SERVICE", "chrome-cdp.service")
WEB_OPERATOR_LAUNCHER = os.environ.get("WEB_OPERATOR_LAUNCHER", "systemd")


def _cdp_health() -> bool:
    """True if the browser CDP endpoint accepts a real connection."""
    return subprocess.call(
        ["node", str(SCRIPTS_DIR / "cdp.mjs"), "health"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) == 0


class _SystemdLauncher:
    """Defers Chrome lifecycle to a systemd --user unit (the SoT)."""

    def __init__(self, unit: str) -> None:
        self.unit = unit

    def _run(self, action: str) -> int:
        return subprocess.call(["systemctl", "--user", action, self.unit])

    def start(self) -> int:
        return self._run("start")

    def restart(self) -> int:
        return self._run("restart")


def _make_launcher():
    if WEB_OPERATOR_LAUNCHER == "systemd":
        return _SystemdLauncher(WEB_OPERATOR_SERVICE)
    # Extension point: 'launchd' (macOS), 'spawn' (raw) backends go here.
    raise typer.BadParameter(
        f"Unsupported WEB_OPERATOR_LAUNCHER={WEB_OPERATOR_LAUNCHER!r} (supported: systemd)"
    )


def _up_impl(restart: bool, timeout: int) -> None:
    launcher = _make_launcher()

    if restart:
        typer.echo(f"Restarting {WEB_OPERATOR_SERVICE} ...")
        launcher.restart()
    elif _cdp_health():
        typer.echo("Browser ready.")
        raise typer.Exit(0)
    else:
        typer.echo(f"Browser down — starting {WEB_OPERATOR_SERVICE} ...")
        rc = launcher.start()
        if rc != 0:
            typer.echo(
                "Launcher failed. If 'systemctl --user' has no session bus over "
                "SSH, enable lingering: loginctl enable-linger \"$USER\"",
                err=True,
            )
            raise typer.Exit(rc)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _cdp_health():
            typer.echo("Browser ready.")
            raise typer.Exit(0)
        time.sleep(1)

    typer.echo(
        f"Browser still unreachable after {timeout}s. "
        f"Try: omp web-operator up --restart",
        err=True,
    )
    raise typer.Exit(1)


@app.command("up")
def up(
    restart: bool = typer.Option(
        False, "--restart", help="Force-restart the service instead of only starting it when down."
    ),
    timeout: int = typer.Option(20, "--timeout", help="Seconds to wait for the browser to become ready."),
) -> None:
    """Ensure the CDP browser is running, starting its service if needed."""
    _up_impl(restart, timeout)


@app.command("ensure", hidden=True)
def ensure(
    restart: bool = typer.Option(False, "--restart"),
    timeout: int = typer.Option(20, "--timeout"),
) -> None:
    """Alias for `up`."""
    _up_impl(restart, timeout)


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

SEARCH_SITES = [
    "baidu", "duckduckgo", "github", "google", "reddit",
    "taoguba", "weixin-sogou", "x", "xueqiu",
]


@app.command()
def search(
    site: str = typer.Argument(..., help=f"Search platform ({', '.join(SEARCH_SITES)})."),
    query: str = typer.Argument(..., help="Search query."),
    limit: str | None = typer.Argument(None, help="Max results."),
    target: str | None = typer.Option(None, "--target", help="CDP target (page URL or index)."),
) -> None:
    """Search a platform (returns JSON array).

    Example:
        omp web-operator search google "AI agents" 10
        omp web-operator search x "Claude Code" --target 0
    """
    script = SITES_DIR / site / "search.sh"
    if not script.is_file():
        typer.echo(f"error: unknown search site '{site}'", err=True)
        raise typer.Exit(2)
    cmd = ["bash", str(script), query]
    if limit:
        cmd.append(limit)
    if target:
        cmd.append(target)
    sys.exit(subprocess.call(cmd))


@app.command(
    "search-multi",
    context_settings={
        "allow_extra_args": True,
        "allow_interspersed_args": False,
        "ignore_unknown_options": True,
    },
)
def search_multi(ctx: typer.Context) -> None:
    """Multi-platform parallel search.

    Example:
        omp web-operator search-multi --google "AI agents" --baidu "AI 智能体" --limit 5
    """
    sys.exit(subprocess.call(["bash", str(SCRIPTS_DIR / "search-multi.sh")] + ctx.args))


# ---------------------------------------------------------------------------
# generate-image
# ---------------------------------------------------------------------------

GENERATE_IMAGE_SITES = ["chatgpt"]


@app.command("generate-image")
def generate_image(
    site: str = typer.Argument(..., help=f"Image generation site ({', '.join(GENERATE_IMAGE_SITES)})."),
    prompt: str = typer.Argument(..., help="Image generation prompt."),
    out: str | None = typer.Option(None, "--out", help="Output image path; default ~/Downloads/chatgpt-image-<timestamp>.png."),
    target: str | None = typer.Option(None, "--target", help="CDP target prefix; auto-opens chatgpt.com/images if omitted."),
    timeout: int = typer.Option(180, "--timeout", help="Max seconds to wait for image generation."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite the output file if it exists."),
    json_output: bool = typer.Option(False, "--json", help="Output structured JSON."),
) -> None:
    """Generate an image on a supported site and save it locally.

    Example:
        omp web-operator generate-image chatgpt "a blue circle on white background" --out ./circle.png --json
    """
    script = SITES_DIR / site / "generate-image.sh"
    if not script.is_file():
        typer.echo(f"error: unknown image generation site '{site}'", err=True)
        raise typer.Exit(2)
    cmd = ["bash", str(script), prompt, "--timeout", str(timeout)]
    if out:
        cmd += ["--out", out]
    if target:
        cmd += ["--target", target]
    if overwrite:
        cmd.append("--overwrite")
    if json_output:
        cmd.append("--json")
    sys.exit(subprocess.call(cmd))


# ---------------------------------------------------------------------------
# image-serve
# ---------------------------------------------------------------------------


@app.command("image-serve")
def image_serve(
    port: int = typer.Option(8320, "--port", help="Listen port."),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address."),
    out_dir: str | None = typer.Option(None, "--out-dir", help="Directory for generated images; default $OMP_HOME/data/chatgpt-images."),
) -> None:
    """Run a local FastAPI service that queues image-generation jobs serially.

    Jobs run one at a time over the host Chrome CDP. Endpoints: POST /jobs,
    GET /jobs, GET /jobs/{id}, DELETE /jobs/{id}, GET /jobs/{id}/image, /health.

    Example:
        omp web-operator image-serve --port 8320
    """
    cmd = ["uv", "run", "--script", str(SCRIPTS_DIR / "image_service.py"), "--port", str(port), "--host", host]
    if out_dir:
        cmd += ["--out-dir", out_dir]
    sys.exit(subprocess.call(cmd))


# ---------------------------------------------------------------------------
# read-url
# ---------------------------------------------------------------------------


@app.command("read-url")
def read_url(
    url: str = typer.Argument(..., help="URL to read."),
    limit: int | None = typer.Option(None, "--limit", "-l", help="Max content length."),
    comments: int | None = typer.Option(None, "--comments", help="Max comments (0 = all)."),
    json_output: bool = typer.Option(False, "--json", help="Output structured JSON."),
) -> None:
    """Read URL content as Markdown or structured JSON.

    Example:
        omp web-operator read-url "https://example.com" --limit 5000
        omp web-operator read-url "https://example.com" --json
    """
    cmd = ["bash", str(SCRIPTS_DIR / "read-url.sh"), url]
    if limit is not None:
        cmd += ["--limit", str(limit)]
    if comments is not None:
        cmd += ["--comments", str(comments)]
    if json_output:
        cmd.append("--json")
    sys.exit(subprocess.call(cmd))


# ---------------------------------------------------------------------------
# open-post
# ---------------------------------------------------------------------------

OPEN_POST_SITES = ["reddit", "x", "xueqiu", "taoguba"]


@app.command("open-post")
def open_post(
    site: str = typer.Argument(..., help=f"Platform ({', '.join(OPEN_POST_SITES)})."),
    url: str = typer.Argument(..., help="Post URL."),
    comment_limit: str | None = typer.Argument(None, help="Max comments (0 = all)."),
    target: str | None = typer.Option(None, "--target", help="CDP target (page URL or index)."),
) -> None:
    """Open and extract a post with comments (returns JSON).

    Example:
        omp web-operator open-post x "https://x.com/user/status/123"
        omp web-operator open-post reddit "https://reddit.com/r/..." 50 --target 0
    """
    script = SITES_DIR / site / "open-post.sh"
    if not script.is_file():
        typer.echo(f"error: unknown open-post site '{site}'", err=True)
        raise typer.Exit(2)
    cmd = ["bash", str(script), url]
    if comment_limit:
        cmd.append(comment_limit)
    if target:
        cmd.append(target)
    sys.exit(subprocess.call(cmd))


# ---------------------------------------------------------------------------
# taoguba
# ---------------------------------------------------------------------------

taoguba_app = typer.Typer(
    name="taoguba",
    help="Taoguba workflows.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(taoguba_app, name="taoguba")


@taoguba_app.command()
def jinghua(
    hours: str | None = typer.Option(None, "--hours", help="Hours to look back."),
    limit: str | None = typer.Option(None, "--limit", help="Max results."),
    target: str | None = typer.Option(None, "--target", help="CDP target (page URL or index)."),
) -> None:
    """Fetch jinghua (精华) posts.

    Example:
        omp web-operator taoguba jinghua --hours 24 --limit 10
    """
    cmd = ["bash", str(SITES_DIR / "taoguba" / "jinghua.sh")]
    for arg in [hours, limit, target]:
        if arg:
            cmd.append(arg)
    sys.exit(subprocess.call(cmd))


@taoguba_app.command()
def following(
    hours: str | None = typer.Option(None, "--hours", help="Hours to look back."),
    limit: str | None = typer.Option(None, "--limit", help="Max results."),
    target: str | None = typer.Option(None, "--target", help="CDP target (page URL or index)."),
) -> None:
    """Fetch posts from followed users.

    Example:
        omp web-operator taoguba following --hours 12 --limit 20
    """
    cmd = ["bash", str(SITES_DIR / "taoguba" / "following.sh")]
    for arg in [hours, limit, target]:
        if arg:
            cmd.append(arg)
    sys.exit(subprocess.call(cmd))


# ---------------------------------------------------------------------------
# kdocs
# ---------------------------------------------------------------------------

kdocs_app = typer.Typer(
    name="kdocs",
    help="KDocs (365.kdocs.cn) workflows.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(kdocs_app, name="kdocs")


@kdocs_app.command("search")
def kdocs_search(
    query: str = typer.Argument(..., help="Search query."),
    limit: str | None = typer.Argument(None, help="Max results."),
    target: str | None = typer.Option(None, "--target", help="CDP target (page URL or index)."),
) -> None:
    """Search KDocs documents.

    Example:
        omp web-operator kdocs search "quarterly report" --target 0
    """
    cmd = ["bash", str(SITES_DIR / "kdocs" / "search.sh"), query]
    if limit:
        cmd.append(limit)
    if target:
        cmd.append(target)
    sys.exit(subprocess.call(cmd))


@kdocs_app.command("open-doc")
def kdocs_open_doc(
    file_key: str = typer.Argument(..., help="Document file key."),
    main_target: str | None = typer.Argument(None, help="CDP main target."),
) -> None:
    """Open a KDocs document.

    Example:
        omp web-operator kdocs open-doc abc123
    """
    cmd = ["bash", str(SITES_DIR / "kdocs" / "open-doc.sh"), file_key]
    if main_target:
        cmd.append(main_target)
    sys.exit(subprocess.call(cmd))


@kdocs_app.command("find-in-doc")
def kdocs_find_in_doc(
    keyword: str = typer.Argument(..., help="Keyword to find."),
    target: str | None = typer.Argument(None, help="CDP target."),
) -> None:
    """Find keyword in current KDocs document.

    Example:
        omp web-operator kdocs find-in-doc "revenue"
    """
    cmd = ["bash", str(SITES_DIR / "kdocs" / "find-in-doc.sh"), keyword]
    if target:
        cmd.append(target)
    sys.exit(subprocess.call(cmd))


@kdocs_app.command("ask-ai")
def kdocs_ask_ai(
    question: str = typer.Argument(..., help="Question to ask AI."),
    target: str | None = typer.Argument(None, help="CDP target."),
) -> None:
    """Ask AI a question about the current document.

    Example:
        omp web-operator kdocs ask-ai "summarize this document"
    """
    cmd = ["bash", str(SITES_DIR / "kdocs" / "ask-ai.sh"), question]
    if target:
        cmd.append(target)
    sys.exit(subprocess.call(cmd))


@kdocs_app.command("close-doc")
def kdocs_close_doc(
    target: str | None = typer.Argument(None, help="CDP target."),
) -> None:
    """Close current KDocs document.

    Example:
        omp web-operator kdocs close-doc
    """
    cmd = ["bash", str(SITES_DIR / "kdocs" / "close-doc.sh")]
    if target:
        cmd.append(target)
    sys.exit(subprocess.call(cmd))


# ---------------------------------------------------------------------------
# xueqiu
# ---------------------------------------------------------------------------

xueqiu_app = typer.Typer(
    name="xueqiu",
    help="Xueqiu (雪球) workflows.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(xueqiu_app, name="xueqiu")


@xueqiu_app.command()
def hot(
    limit: str | None = typer.Argument(None, help="Max results."),
    target: str | None = typer.Option(None, "--target", help="CDP target (page URL or index)."),
) -> None:
    """Fetch hot topics on Xueqiu.

    Example:
        omp web-operator xueqiu hot 20 --target 0
    """
    cmd = ["bash", str(SITES_DIR / "xueqiu" / "hot.sh")]
    if limit:
        cmd.append(limit)
    if target:
        cmd.append(target)
    sys.exit(subprocess.call(cmd))


@xueqiu_app.command("stock-info")
def stock_info(
    symbol_or_url: str = typer.Argument(..., help="Stock symbol or URL."),
    limit: str | None = typer.Argument(None, help="Max results."),
    target: str | None = typer.Option(None, "--target", help="CDP target (page URL or index)."),
) -> None:
    """Get stock information from Xueqiu.

    Example:
        omp web-operator xueqiu stock-info SH600519 --target 0
    """
    cmd = ["bash", str(SITES_DIR / "xueqiu" / "stock-info.sh"), symbol_or_url]
    if limit:
        cmd.append(limit)
    if target:
        cmd.append(target)
    sys.exit(subprocess.call(cmd))


# ---------------------------------------------------------------------------
# x (x.com)
# ---------------------------------------------------------------------------

x_app = typer.Typer(
    name="x",
    help="X (x.com) workflows.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(x_app, name="x")


@x_app.command("for-you")
def x_for_you(
    limit: str | None = typer.Argument(None, help="Max results."),
    target: str | None = typer.Option(None, "--target", help="CDP target (page URL or index)."),
) -> None:
    """Fetch For You feed from X.

    Example:
        omp web-operator x for-you 20 --target 0
    """
    cmd = ["bash", str(SITES_DIR / "x" / "for-you.sh")]
    if limit:
        cmd.append(limit)
    if target:
        cmd.append(target)
    sys.exit(subprocess.call(cmd))


# ---------------------------------------------------------------------------
# feishu (admin backend)
# ---------------------------------------------------------------------------

feishu_app = typer.Typer(
    name="feishu",
    help="Feishu admin backend workflows.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(feishu_app, name="feishu")

feishu_approval_app = typer.Typer(
    name="approval",
    help="Feishu approval admin workflows.",
    no_args_is_help=True,
    add_completion=False,
)
feishu_app.add_typer(feishu_approval_app, name="approval")


@feishu_approval_app.command("export")
def feishu_approval_export(
    start: str = typer.Option(..., "--start", help="Submit-time start date (YYYY-MM-DD)."),
    end: str = typer.Option(..., "--end", help="Submit-time end date (YYYY-MM-DD); span <= 90 days."),
    extract_to: str | None = typer.Option(None, "--extract-to", help="Where to unzip; default ~/Downloads/<zip-basename>/."),
    target: str | None = typer.Option(None, "--target", help="CDP target prefix; auto-discovered if omitted."),
    timeout: int = typer.Option(300, "--timeout", help="Max seconds to wait for export completion."),
) -> None:
    """Export approval data from Feishu admin backend to ZIP/Excel.

    Pre-requisite: open https://www.feishu.cn/approval/admin/dataExportV2/dataQuery
    in Chrome, sign in as administrator, and set the Submit-time range to the
    same --start..--end window before running.

    Example:
        omp web-operator feishu approval export --start 2026-04-01 --end 2026-04-26
    """
    cmd = [
        "bash",
        str(SITES_DIR / "feishu" / "approval-export.sh"),
        "--start", start,
        "--end", end,
        "--timeout", str(timeout),
    ]
    if extract_to:
        cmd += ["--extract-to", extract_to]
    if target:
        cmd += ["--target", target]
    sys.exit(subprocess.call(cmd))


feishu_attendance_app = typer.Typer(
    name="attendance",
    help="Feishu attendance admin workflows.",
    no_args_is_help=True,
    add_completion=False,
)
feishu_app.add_typer(feishu_attendance_app, name="attendance")


@feishu_attendance_app.command("export")
def feishu_attendance_export(
    start: str = typer.Option(..., "--start", help="Report start date (YYYY-MM-DD)."),
    end: str = typer.Option(..., "--end", help="Report end date (YYYY-MM-DD); span <= 31 days."),
    out_dir: str | None = typer.Option(None, "--out-dir", help="Where to save the xlsx; default ~/Downloads/."),
    target: str | None = typer.Option(None, "--target", help="CDP target prefix; auto-discovered if omitted."),
    timeout: int = typer.Option(300, "--timeout", help="Max seconds to wait for export completion."),
) -> None:
    """Export the Monthly-report attendance data from Feishu admin backend to xlsx.

    Pre-requisite: signed in to oa.feishu.cn as an attendance administrator on
    any Chrome tab; the script reuses an oa.feishu.cn tab or opens one.

    Example:
        omp web-operator feishu attendance export --start 2026-04-01 --end 2026-04-27
    """
    cmd = [
        "bash",
        str(SITES_DIR / "feishu" / "attendance-export.sh"),
        "--start", start,
        "--end", end,
        "--timeout", str(timeout),
    ]
    if out_dir:
        cmd += ["--out-dir", out_dir]
    if target:
        cmd += ["--target", target]
    sys.exit(subprocess.call(cmd))


# ---------------------------------------------------------------------------
# test
# ---------------------------------------------------------------------------


@app.command(
    "test",
    context_settings={
        "allow_extra_args": True,
        "allow_interspersed_args": False,
        "ignore_unknown_options": True,
    },
)
def test(ctx: typer.Context) -> None:
    """Run web-operator tests (list, core, site <name>, all).

    Example:
        omp web-operator test list
        omp web-operator test core
        omp web-operator test site google
    """
    sys.exit(subprocess.call(["node", str(SCRIPTS_DIR / "test.mjs")] + ctx.args))


if __name__ == "__main__":
    app()
