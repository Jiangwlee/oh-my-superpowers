#!/usr/bin/env python3
"""Shared helpers for OpenClaw GitHub tracker skill scripts."""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import urllib.parse
import urllib.request
from typing import Any


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def today_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def ensure_layout(memory_root: str) -> dict[str, pathlib.Path]:
    base = pathlib.Path(memory_root).expanduser().resolve() / "github-tracker"
    paths = {
        "base": base,
        "briefs_daily": base / "briefs" / "daily",
        "indexes": base / "indexes",
        "trending_raw": base / "trending" / "raw",
        "watchlist": base / "watchlist",
        "projects": base / "projects",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)

    watchlist_file = paths["watchlist"] / "watchlist.json"
    if not watchlist_file.exists():
        watchlist_file.write_text(
            json.dumps({"repos": []}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    index_file = paths["indexes"] / "project-index.jsonl"
    if not index_file.exists():
        index_file.touch()

    return paths


def slug_from_repo(repo: str) -> str:
    return repo.replace("/", "__")


def default_config_path() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent / "config.json"


def load_runtime_config(config_path: str = "") -> dict[str, Any]:
    cfg_path = (
        pathlib.Path(config_path).expanduser().resolve()
        if config_path
        else default_config_path()
    )
    if not cfg_path.exists():
        return {}
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    apply_proxy_from_config(cfg)
    return cfg


def apply_proxy_from_config(cfg: dict[str, Any]) -> None:
    http_proxy = str(cfg.get("http_proxy", "")).strip()
    https_proxy = str(cfg.get("https_proxy", "")).strip()
    no_proxy = str(cfg.get("no_proxy", "")).strip()
    if http_proxy:
        os.environ["http_proxy"] = http_proxy
        os.environ["HTTP_PROXY"] = http_proxy
    if https_proxy:
        os.environ["https_proxy"] = https_proxy
        os.environ["HTTPS_PROXY"] = https_proxy
    if no_proxy:
        os.environ["no_proxy"] = no_proxy
        os.environ["NO_PROXY"] = no_proxy


def gh_available() -> bool:
    return shutil.which("gh") is not None


def _gh_api_request(
    path: str, token: str | None = None, query: dict[str, str] | None = None
) -> Any:
    endpoint = path
    if query:
        endpoint = f"{endpoint}?{urllib.parse.urlencode(query)}"
    cmd = ["gh", "api", endpoint]
    env = os.environ.copy()
    if token:
        env["GH_TOKEN"] = token
        env["GITHUB_TOKEN"] = token
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
    return json.loads(proc.stdout)


def _json_request(url: str, token: str | None = None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "openclaw-github-tracker",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _text_request(url: str, token: str | None = None) -> str:
    headers = {"User-Agent": "openclaw-github-tracker"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def gh_api(
    path: str, token: str | None = None, query: dict[str, str] | None = None
) -> Any:
    if gh_available():
        try:
            return _gh_api_request(path, token=token, query=query)
        except Exception:
            # Fall back to urllib API requests when gh is not authenticated or unavailable.
            pass
    query_str = ""
    if query:
        query_str = "?" + urllib.parse.urlencode(query)
    return _json_request(f"https://api.github.com{path}{query_str}", token=token)


def gh_web_text(path: str, query: dict[str, str] | None = None) -> str:
    query_str = ""
    if query:
        query_str = "?" + urllib.parse.urlencode(query)
    return _text_request(f"https://github.com{path}{query_str}")


def gh_repo_clone_shallow(
    repo: str, dest_dir: pathlib.Path, token: str | None = None
) -> bool:
    if not gh_available():
        return False
    cmd = ["gh", "repo", "clone", repo, str(dest_dir), "--", "--depth", "1"]
    env = os.environ.copy()
    if token:
        env["GH_TOKEN"] = token
        env["GITHUB_TOKEN"] = token
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
        return True
    except Exception:
        return False


def decode_readme(content_b64: str) -> str:
    try:
        return base64.b64decode(content_b64).decode("utf-8", errors="replace")
    except Exception:
        return ""


def read_watchlist(path: pathlib.Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    repos = data.get("repos", [])
    return sorted({r.strip() for r in repos if isinstance(r, str) and "/" in r})


def write_watchlist(path: pathlib.Path, repos: list[str]) -> None:
    path.write_text(
        json.dumps({"repos": sorted(set(repos))}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_index(index_path: pathlib.Path) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    if not index_path.exists():
        return entries
    for line in index_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            repo = obj.get("repo")
            if repo:
                entries[repo] = obj
        except json.JSONDecodeError:
            continue
    return entries


def save_index(index_path: pathlib.Path, entries: dict[str, dict[str, Any]]) -> None:
    lines = [
        json.dumps(v, ensure_ascii=False)
        for _, v in sorted(entries.items(), key=lambda kv: kv[0])
    ]
    index_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
