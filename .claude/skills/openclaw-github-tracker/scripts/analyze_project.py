#!/usr/bin/env python3
"""Generate first-time or refreshed deep project dossier for a GitHub repo."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import tempfile
from typing import Any

from common import (
    decode_readme,
    ensure_layout,
    gh_api,
    gh_repo_clone_shallow,
    load_index,
    load_runtime_config,
    save_index,
    slug_from_repo,
    utc_now,
)


def _guess_modules(top_dirs: list[str], readme_text: str) -> list[dict[str, str]]:
    modules: list[dict[str, str]] = []
    priority = [
        "apps",
        "services",
        "packages",
        "cmd",
        "src",
        "api",
        "backend",
        "frontend",
        "docs",
        "examples",
    ]
    ordered = sorted(
        top_dirs,
        key=lambda d: (priority.index(d) if d in priority else len(priority), d),
    )
    for d in ordered[:8]:
        role = "Core code module"
        if d in {"docs"}:
            role = "Documentation"
        elif d in {"examples"}:
            role = "Usage examples"
        elif d in {"frontend"}:
            role = "UI application"
        elif d in {"backend", "services", "api"}:
            role = "Server or API layer"
        elif d in {"packages"}:
            role = "Shared package workspace"
        elif d in {"cmd"}:
            role = "CLI entrypoints"
        modules.append({"name": d, "responsibility": role})

    # Fallback from README headings when layout is sparse.
    if len(modules) < 3:
        headings = re.findall(r"^##+\s+(.+)$", readme_text, flags=re.MULTILINE)
        for h in headings[: 3 - len(modules)]:
            modules.append(
                {"name": h.strip(), "responsibility": "Documented feature area"}
            )
    return modules


def _extract_roadmap_signals(
    readme_text: str, milestones: list[dict[str, Any]], releases: list[dict[str, Any]]
) -> list[str]:
    signals: list[str] = []
    if re.search(
        r"roadmap|planned|next steps|future work", readme_text, flags=re.IGNORECASE
    ):
        signals.append("README contains explicit roadmap/planning signals.")
    if milestones:
        open_m = sum(1 for m in milestones if m.get("state") == "open")
        signals.append(f"Milestones found: {len(milestones)} total, {open_m} open.")
    if releases:
        signals.append(
            f"Releases published: {len(releases)} (latest: {releases[0].get('tag_name', 'n/a')})."
        )
    if not signals:
        signals.append(
            "No explicit roadmap artifacts found via README/milestones/releases."
        )
    return signals


def _render_profile(repo: str, payload: dict[str, Any]) -> str:
    lines = [
        "---",
        "type: github_project_profile",
        f"repo: {repo}",
        f"analyzed_at: {payload['analyzed_at']}",
        f"default_branch: {payload.get('default_branch', '')}",
        f"license: {payload.get('license_spdx', 'NOASSERTION')}",
        "---",
        "",
        f"# {repo} Dossier",
        "",
        "## Executive Summary",
        f"- {payload.get('summary', 'N/A')}",
        "",
        "## Architecture Signals",
        f"- Repository style: {payload.get('repo_style', 'unknown')}",
    ]
    for d in payload.get("top_directories", []):
        lines.append(f"- Top-level directory: `{d}`")

    lines.extend(
        [
            "",
            "## Technology Choices",
            f"- Primary language: {payload.get('primary_language', 'Unknown')}",
        ]
    )
    for k, v in payload.get("languages", {}).items():
        lines.append(f"- {k}: {v} bytes")
    for s in payload.get("tech_signals", []):
        lines.append(f"- {s}")

    lines.extend(["", "## Main Modules"])
    for m in payload.get("modules", []):
        lines.append(f"- `{m['name']}`: {m['responsibility']}")

    lines.extend(["", "## Roadmap Signals"])
    for s in payload.get("roadmap_signals", []):
        lines.append(f"- {s}")

    lines.extend(
        [
            "",
            "## License & Compliance",
            f"- SPDX: {payload.get('license_spdx', 'NOASSERTION')}",
            f"- License name: {payload.get('license_name', 'Unknown')}",
            "",
            "## Baseline Metrics",
            f"- Stars: {payload.get('stars', 0)}",
            f"- Forks: {payload.get('forks', 0)}",
            f"- Open issues: {payload.get('open_issues', 0)}",
            f"- Watchers: {payload.get('watchers', 0)}",
            f"- Last pushed at: {payload.get('pushed_at', 'N/A')}",
            f"- Latest release: {payload.get('latest_release', 'N/A')}",
        ]
    )
    return "\n".join(lines) + "\n"


def analyze(repo: str, token: str | None = None, deep: bool = False) -> dict[str, Any]:
    """Analyze a GitHub repository.

    Args:
        repo: Repository in format "owner/repo"
        token: GitHub API token
        deep: If True, clone repository for detailed analysis. Default False for speed.
    """

    def safe_api(
        path: str, query: dict[str, str] | None = None, default: Any = None
    ) -> Any:
        try:
            return gh_api(path, token=token, query=query)
        except Exception:
            return default

    repo_info = gh_api(f"/repos/{repo}", token=token)
    readme_resp = safe_api(f"/repos/{repo}/readme", default={}) or {}
    languages = safe_api(f"/repos/{repo}/languages", default={}) or {}
    milestones = (
        safe_api(
            f"/repos/{repo}/milestones",
            query={"state": "all", "per_page": "20"},
            default=[],
        )
        or []
    )
    releases = (
        safe_api(f"/repos/{repo}/releases", query={"per_page": "10"}, default=[]) or []
    )
    contents = safe_api(f"/repos/{repo}/contents", default=[]) or []

    top_dirs = [
        x["name"] for x in contents if isinstance(x, dict) and x.get("type") == "dir"
    ]

    # Tech signals - use API data unless deep analysis requested
    tech_signals: list[str] = []

    if deep:
        # Deep analysis: clone repository for accurate file detection
        with tempfile.TemporaryDirectory(prefix="openclaw-ghtrk-") as tmp:
            clone_dir = pathlib.Path(tmp) / repo.split("/", 1)[1]
            if gh_repo_clone_shallow(repo, clone_dir, token=token):
                local_dirs = sorted(
                    [
                        p.name
                        for p in clone_dir.iterdir()
                        if p.is_dir() and p.name != ".git"
                    ]
                )
                if local_dirs:
                    top_dirs = local_dirs
                marker_map = {
                    "package.json": "Node.js project signals (package.json)",
                    "pyproject.toml": "Python packaging signals (pyproject.toml)",
                    "requirements.txt": "Python dependency file (requirements.txt)",
                    "Cargo.toml": "Rust project signals (Cargo.toml)",
                    "go.mod": "Go module signals (go.mod)",
                    "pom.xml": "Java Maven signals (pom.xml)",
                }
                for marker, label in marker_map.items():
                    if (clone_dir / marker).exists():
                        tech_signals.append(label)
    else:
        # Fast analysis: infer from primary language and README
        primary_lang = repo_info.get("language", "")
        lang_markers = {
            "JavaScript": "Node.js project signals (inferred from JavaScript)",
            "TypeScript": "Node.js/TypeScript project signals",
            "Python": "Python project signals (inferred from Python)",
            "Rust": "Rust project signals (inferred from Rust)",
            "Go": "Go module signals (inferred from Go)",
            "Java": "Java project signals (inferred from Java)",
        }
        if primary_lang in lang_markers:
            tech_signals.append(lang_markers[primary_lang])
    readme_text = decode_readme(readme_resp.get("content", ""))

    total_lang = sum(languages.values()) or 1
    lang_sorted = dict(sorted(languages.items(), key=lambda kv: kv[1], reverse=True))
    primary_language = repo_info.get("language") or (
        next(iter(lang_sorted.keys())) if lang_sorted else "Unknown"
    )
    repo_style = (
        "monorepo-like"
        if any(d in top_dirs for d in ("apps", "packages", "services"))
        else "single-repo"
    )

    modules = _guess_modules(top_dirs, readme_text)
    roadmap_signals = _extract_roadmap_signals(readme_text, milestones, releases)

    summary = repo_info.get("description") or "No repository description."
    payload = {
        "repo": repo,
        "analyzed_at": utc_now(),
        "default_branch": repo_info.get("default_branch", ""),
        "summary": summary,
        "repo_style": repo_style,
        "top_directories": top_dirs[:12],
        "primary_language": primary_language,
        "languages": lang_sorted,
        "language_percent": {
            k: round(v * 100 / total_lang, 2) for k, v in lang_sorted.items()
        },
        "tech_signals": tech_signals,
        "modules": modules,
        "roadmap_signals": roadmap_signals,
        "license_spdx": (repo_info.get("license") or {}).get("spdx_id", "NOASSERTION"),
        "license_name": (repo_info.get("license") or {}).get("name", "Unknown"),
        "stars": repo_info.get("stargazers_count", 0),
        "forks": repo_info.get("forks_count", 0),
        "open_issues": repo_info.get("open_issues_count", 0),
        "watchers": repo_info.get(
            "subscribers_count", repo_info.get("watchers_count", 0)
        ),
        "pushed_at": repo_info.get("pushed_at"),
        "latest_release": releases[0].get("tag_name") if releases else "N/A",
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze a GitHub repository and build project dossier."
    )
    parser.add_argument("repo", help="owner/repo")
    parser.add_argument("--memory-root", default=".memory")
    parser.add_argument(
        "--config", default="", help="Optional config file path for proxy settings."
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Deep analysis with git clone (slower, more accurate)",
    )
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    load_runtime_config(args.config)
    paths = ensure_layout(args.memory_root)
    slug = slug_from_repo(args.repo)
    project_dir = paths["projects"] / slug
    snapshots_dir = project_dir / "snapshots"
    updates_dir = project_dir / "updates"
    project_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    updates_dir.mkdir(parents=True, exist_ok=True)

    payload = analyze(args.repo, token=token, deep=args.deep)
    profile_md = _render_profile(args.repo, payload)

    profile_path = project_dir / "profile.md"
    profile_path.write_text(profile_md, encoding="utf-8")

    snapshot_path = snapshots_dir / f"{payload['analyzed_at'].replace(':', '-')}.json"
    snapshot_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    index_path = paths["indexes"] / "project-index.jsonl"
    index = load_index(index_path)
    prev = index.get(args.repo, {})
    index[args.repo] = {
        "repo": args.repo,
        "slug": slug,
        "first_analyzed_at": prev.get("first_analyzed_at", payload["analyzed_at"]),
        "last_analyzed_at": payload["analyzed_at"],
        "profile_path": str(pathlib.Path("projects") / slug / "profile.md"),
        "last_update_path": prev.get("last_update_path", ""),
        "tags": prev.get("tags", []),
        "status": "active",
    }
    save_index(index_path, index)
    print(str(profile_path))


if __name__ == "__main__":
    main()
