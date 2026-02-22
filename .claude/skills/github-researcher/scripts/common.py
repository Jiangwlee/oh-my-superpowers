#!/usr/bin/env python3
"""Shared helpers for github-researcher scripts."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import tempfile
from typing import Any


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def ensure_layout(memory_root: str) -> dict[str, pathlib.Path]:
    base = pathlib.Path(memory_root).expanduser().resolve() / "github-researcher"
    paths = {
        "base": base,
        "briefs_daily": base / "briefs" / "daily",
        "indexes": base / "indexes",
        "watchlist": base / "watchlist",
        "projects": base / "projects",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)

    watchlist_file = paths["watchlist"] / "watchlist.json"
    if not watchlist_file.exists():
        watchlist_file.write_text(json.dumps({"repos": []}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    index_file = paths["indexes"] / "project-index.jsonl"
    if not index_file.exists():
        index_file.touch()

    return paths


def slug_from_repo(repo: str) -> str:
    return repo.replace("/", "__")


def read_watchlist(path: pathlib.Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    repos = data.get("repos", [])
    return sorted({r.strip() for r in repos if isinstance(r, str) and "/" in r})


def write_watchlist(path: pathlib.Path, repos: list[str]) -> None:
    path.write_text(json.dumps({"repos": sorted(set(repos))}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
        except json.JSONDecodeError:
            continue
        repo = obj.get("repo")
        if repo:
            entries[repo] = obj
    return entries


def save_index(index_path: pathlib.Path, entries: dict[str, dict[str, Any]]) -> None:
    lines = [json.dumps(v, ensure_ascii=False) for _, v in sorted(entries.items(), key=lambda kv: kv[0])]
    index_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def gh_available() -> bool:
    return shutil.which("gh") is not None


def run_cmd(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return proc.stdout.strip()


def gh_api(path: str, jq: str | None = None) -> Any:
    cmd = ["gh", "api", path]
    if jq:
        cmd.extend(["--jq", jq])
    out = run_cmd(cmd)
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


def git_shallow_clone(repo: str) -> pathlib.Path:
    workdir = pathlib.Path(tempfile.mkdtemp(prefix="github-researcher-"))
    target = workdir / repo.split("/", 1)[1]
    run_cmd(["git", "clone", "--depth", "1", f"https://github.com/{repo}.git", str(target)])
    return target


def scan_local_repo(clone_dir: pathlib.Path) -> dict[str, Any]:
    top_dirs = sorted([p.name for p in clone_dir.iterdir() if p.is_dir() and p.name != ".git"])[:20]
    markers = {
        "package.json": "node",
        "pyproject.toml": "python",
        "requirements.txt": "python",
        "go.mod": "go",
        "Cargo.toml": "rust",
        "pom.xml": "java",
        "build.gradle": "java",
    }
    tech = sorted({v for k, v in markers.items() if (clone_dir / k).exists()})
    head_sha = run_cmd(["git", "-C", str(clone_dir), "rev-parse", "HEAD"])
    head_date = run_cmd(["git", "-C", str(clone_dir), "show", "-s", "--format=%cI", "HEAD"])
    branch = run_cmd(["git", "-C", str(clone_dir), "rev-parse", "--abbrev-ref", "HEAD"])
    return {
        "top_directories": top_dirs,
        "tech_signals": tech,
        "default_branch": branch,
        "latest_commit": head_sha,
        "latest_commit_date": head_date,
    }
