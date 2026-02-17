#!/usr/bin/env python3
"""Analyze a repository with code download + LLM-first deep analysis."""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
from typing import Any

from common import (
    ensure_layout,
    gh_api,
    gh_available,
    load_index,
    save_index,
    scan_local_repo,
    slug_from_repo,
    utc_now,
)


def _run_cmd(cmd: list[str], timeout: int = 1800) -> str:
    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
        return (proc.stdout or "").strip()
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or str(exc)
        raise RuntimeError(f"command failed: {' '.join(cmd)}; detail: {detail}") from exc


def fetch_gh_metadata(repo: str) -> dict[str, Any]:
    if not gh_available():
        return {}
    try:
        repo_data = gh_api(f"repos/{repo}")
        languages = gh_api(f"repos/{repo}/languages") or {}
    except Exception:
        return {}
    if not isinstance(repo_data, dict):
        return {}
    if not isinstance(languages, dict):
        languages = {}

    return {
        "default_branch": repo_data.get("default_branch", ""),
        "description": repo_data.get("description") or "",
        "license_spdx": (repo_data.get("license") or {}).get("spdx_id", "NOASSERTION"),
        "stars": int(repo_data.get("stargazers_count", 0)),
        "forks": int(repo_data.get("forks_count", 0)),
        "open_issues": int(repo_data.get("open_issues_count", 0)),
        "watchers": int(repo_data.get("subscribers_count", repo_data.get("watchers_count", 0))),
        "pushed_at": repo_data.get("pushed_at", ""),
        "languages": dict(sorted(languages.items(), key=lambda kv: kv[1], reverse=True)),
    }


def ensure_repo_cache(repo: str, cache_root: pathlib.Path, refresh: bool = False) -> pathlib.Path:
    slug = slug_from_repo(repo)
    clone_dir = cache_root / slug
    clone_dir.parent.mkdir(parents=True, exist_ok=True)

    if clone_dir.exists() and refresh:
        shutil.rmtree(clone_dir, ignore_errors=True)

    if clone_dir.exists() and (clone_dir / ".git").exists():
        try:
            _run_cmd(["git", "-C", str(clone_dir), "fetch", "origin", "--depth", "1"])
            default_branch = _run_cmd(["git", "-C", str(clone_dir), "rev-parse", "--abbrev-ref", "HEAD"]) or "main"
            _run_cmd(["git", "-C", str(clone_dir), "reset", "--hard", f"origin/{default_branch}"])
        except Exception:
            # Keep existing cache if refresh fails.
            pass
        return clone_dir

    _run_cmd(["git", "clone", "--depth", "1", f"https://github.com/{repo}.git", str(clone_dir)])
    return clone_dir


def _build_directory_tree(root: pathlib.Path, max_depth: int = 3, max_entries_per_dir: int = 20) -> str:
    lines: list[str] = []

    def walk(dir_path: pathlib.Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return
        entries = sorted([p for p in dir_path.iterdir() if not p.name.startswith(".")], key=lambda p: (p.is_file(), p.name))
        entries = entries[:max_entries_per_dir]
        for idx, entry in enumerate(entries):
            connector = "└── " if idx == len(entries) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir() and depth < max_depth:
                child_prefix = f"{prefix}{'    ' if idx == len(entries) - 1 else '│   '}"
                walk(entry, child_prefix, depth + 1)

    lines.append(f"{root.name}/")
    walk(root, "", 1)
    return "\n".join(lines)


def _llm_prompt(
    repo: str,
    clone_dir: pathlib.Path,
    metadata: dict[str, Any],
    scanned: dict[str, Any],
    directory_tree: str,
) -> str:
    return f"""
You are a senior software architect. Analyze the repository code in this directory and write a deep project analysis report in Chinese.

Repository: {repo}
Local path: {clone_dir}
Known metadata (JSON): {json.dumps(metadata, ensure_ascii=False)}
Known code signals (JSON): {json.dumps(scanned, ensure_ascii=False)}
Directory tree (generated, depth-limited):
```text
{directory_tree}
```

Hard requirements:
1) Focus on real code understanding from the repository files, not generic guesses.
2) Cover all sections below:
- 项目定位与技术路径
- 架构分层（按代码目录给出）
- 功能模块拆解（模块职责+关键入口文件）
- 核心配置与工程化（构建、依赖、CI、测试、发布）
- 集成与部署方式（本地开发、容器化、云部署线索）
- 主要优势与风险
- 结论与建议（适用场景/不适用场景）
3) MUST include a layered architecture diagram using Mermaid.
4) MUST include a code directory structure diagram as a tree block (```text ... ```), based on real repository paths.
5) For every major conclusion, include concrete evidence as file paths in backticks.
6) Keep it concise but deep. Avoid fluff.

Output format:
- Markdown only
- Start with title: `# Deep Analysis: {repo}`
- Must include sections (in this order):
  - `## 分层架构图`
  - `## 代码目录结构图`
""".strip()


def claude_logged_in() -> bool:
    try:
        out = _run_cmd(["claude", "auth", "status"])
        status = json.loads(out)
        return bool(status.get("loggedIn"))
    except Exception:
        return False


def run_llm_analysis(repo: str, clone_dir: pathlib.Path, metadata: dict[str, Any], scanned: dict[str, Any]) -> tuple[str, str]:
    directory_tree = _build_directory_tree(clone_dir, max_depth=3, max_entries_per_dir=20)
    prompt = _llm_prompt(repo, clone_dir, metadata, scanned, directory_tree)
    claude_error = "claude not authenticated"
    if claude_logged_in():
        claude_cmd = [
            "claude",
            "-p",
            "--output-format",
            "text",
            "--dangerously-skip-permissions",
            "--add-dir",
            str(clone_dir),
            prompt,
        ]
        try:
            out = _run_cmd(claude_cmd, timeout=3600)
            if out:
                return "claude", out
            claude_error = "claude returned empty output"
        except Exception as exc:
            claude_error = str(exc)

    codex_cmd = [
        "codex",
        "exec",
        "--full-auto",
        "-C",
        str(clone_dir),
        prompt,
    ]
    try:
        out = _run_cmd(codex_cmd, timeout=3600)
    except Exception as exc:
        raise RuntimeError(f"claude_error={claude_error}; codex_error={exc}") from exc
    if not out:
        raise RuntimeError(f"claude_error={claude_error}; codex_error=codex returned empty analysis output")
    return "codex", out


def analyze_repo(repo: str, cache_root: pathlib.Path, deep: bool = True, refresh_clone: bool = False) -> dict[str, Any]:
    clone_dir = ensure_repo_cache(repo, cache_root=cache_root, refresh=refresh_clone)
    scanned = scan_local_repo(clone_dir)
    metadata = fetch_gh_metadata(repo)
    directory_tree = _build_directory_tree(clone_dir, max_depth=3, max_entries_per_dir=20)

    payload: dict[str, Any] = {
        "repo": repo,
        "analyzed_at": utc_now(),
        "source": "git+gh",
        "cache_path": str(clone_dir),
        "default_branch": metadata.get("default_branch") or scanned.get("default_branch", ""),
        "description": metadata.get("description", ""),
        "license_spdx": metadata.get("license_spdx", "NOASSERTION"),
        "stars": metadata.get("stars"),
        "forks": metadata.get("forks"),
        "open_issues": metadata.get("open_issues"),
        "watchers": metadata.get("watchers"),
        "pushed_at": metadata.get("pushed_at") or scanned.get("latest_commit_date", ""),
        "languages": metadata.get("languages", {}),
        "top_directories": scanned.get("top_directories", []),
        "tech_signals": scanned.get("tech_signals", []),
        "latest_commit": scanned.get("latest_commit", ""),
        "latest_commit_date": scanned.get("latest_commit_date", ""),
        "directory_tree": directory_tree,
    }

    if deep:
        llm_engine, report = run_llm_analysis(repo, clone_dir, metadata, scanned)
        payload["llm_engine"] = llm_engine
        payload["deep_report"] = report
    return payload


def render_profile(payload: dict[str, Any], deep_report_path: pathlib.Path | None = None) -> str:
    repo = payload["repo"]
    lines = [
        "---",
        "type: github_project_profile",
        f"repo: {repo}",
        f"analyzed_at: {payload['analyzed_at']}",
        f"source: {payload.get('source', 'unknown')}",
        f"llm_engine: {payload.get('llm_engine', 'none')}",
        "---",
        "",
        f"# {repo} Dossier",
        "",
        "## Summary",
        f"- Description: {payload.get('description') or 'N/A'}",
        f"- Local code cache: `{payload.get('cache_path', 'N/A')}`",
        f"- Deep analyzer: {payload.get('llm_engine', 'N/A')}",
        "",
        "## Baseline Metrics",
        f"- Stars: {payload.get('stars', 'N/A')}",
        f"- Forks: {payload.get('forks', 'N/A')}",
        f"- Open issues: {payload.get('open_issues', 'N/A')}",
        f"- Watchers: {payload.get('watchers', 'N/A')}",
        f"- Last pushed: {payload.get('pushed_at') or 'N/A'}",
        "",
        "## Codebase Signals",
    ]

    for d in payload.get("top_directories") or []:
        lines.append(f"- Top directory: `{d}`")
    for t in payload.get("tech_signals") or []:
        lines.append(f"- Tech signal: {t}")

    if deep_report_path is not None:
        lines.extend(["", "## Deep Analysis Report", f"- `{deep_report_path}`"])

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze one GitHub repository.")
    parser.add_argument("repo", help="owner/repo")
    parser.add_argument("--memory-root", default=".memory")
    parser.add_argument("--cache-root", default="", help="Optional clone cache root. Default: <memory-root>/github-researcher/cache")
    parser.add_argument("--refresh-clone", action="store_true", help="Force re-clone repository cache")
    parser.add_argument("--mode", choices=["deep", "quick"], default="deep")
    args = parser.parse_args()

    paths = ensure_layout(args.memory_root)
    cache_root = pathlib.Path(args.cache_root).expanduser().resolve() if args.cache_root else (paths["base"] / "cache")

    try:
        payload = analyze_repo(args.repo, cache_root=cache_root, deep=(args.mode == "deep"), refresh_clone=args.refresh_clone)
    except Exception as exc:
        raise SystemExit(
            "Repository analysis failed for "
            f"{args.repo}. Details: {exc}. "
            "Please verify network access to github.com and LLM CLI availability. "
            "If you are behind a restricted network, configure a local proxy and retry."
        )

    slug = slug_from_repo(args.repo)
    project_dir = paths["projects"] / slug
    snapshots_dir = project_dir / "snapshots"
    updates_dir = project_dir / "updates"
    project_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    updates_dir.mkdir(parents=True, exist_ok=True)

    report_path: pathlib.Path | None = None
    if args.mode == "deep" and payload.get("deep_report"):
        report_day = payload["analyzed_at"].split("T", 1)[0]
        report_path = updates_dir / f"{report_day}-deep-analysis.md"
        report_path.write_text(str(payload["deep_report"]).strip() + "\n", encoding="utf-8")

    profile_path = project_dir / "profile.md"
    profile_path.write_text(render_profile(payload, deep_report_path=report_path), encoding="utf-8")

    snapshot_path = snapshots_dir / f"{payload['analyzed_at'].replace(':', '-')}.json"
    snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    index_path = paths["indexes"] / "project-index.jsonl"
    index = load_index(index_path)
    prev = index.get(args.repo, {})
    index[args.repo] = {
        "repo": args.repo,
        "slug": slug,
        "first_analyzed_at": prev.get("first_analyzed_at", payload["analyzed_at"]),
        "last_analyzed_at": payload["analyzed_at"],
        "profile_path": str(pathlib.Path("projects") / slug / "profile.md"),
        "last_update_path": str(pathlib.Path("projects") / slug / "updates" / report_path.name) if report_path else prev.get("last_update_path", ""),
        "status": "active",
    }
    save_index(index_path, index)

    print(
        json.dumps(
            {
                "profile": str(profile_path),
                "snapshot": str(snapshot_path),
                "report": str(report_path) if report_path else "",
                "llm_engine": payload.get("llm_engine", ""),
                "cache_path": payload.get("cache_path", ""),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
