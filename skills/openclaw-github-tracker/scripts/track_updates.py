#!/usr/bin/env python3
"""Track important updates for watched repositories since last snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

from common import (
    ensure_layout,
    gh_api,
    load_index,
    load_runtime_config,
    read_watchlist,
    save_index,
    slug_from_repo,
)
from analyze_project import analyze


def _latest_snapshot(project_dir: Path) -> tuple[Path | None, dict[str, Any] | None]:
    snaps = sorted((project_dir / "snapshots").glob("*.json"))
    if not snaps:
        return None, None
    p = snaps[-1]
    return p, json.loads(p.read_text(encoding="utf-8"))


def _format_delta(now: dict[str, Any], prev: dict[str, Any]) -> list[str]:
    rows = []
    for key in ["stars", "forks", "open_issues", "watchers"]:
        n = int(now.get(key, 0))
        p = int(prev.get(key, 0))
        d = n - p
        sign = "+" if d >= 0 else ""
        rows.append(f"- {key}: {p} -> {n} ({sign}{d})")
    return rows


def _recent_commits(
    repo: str, since_iso: str, token: str | None
) -> list[dict[str, Any]]:
    try:
        return gh_api(
            f"/repos/{repo}/commits",
            token=token,
            query={"since": since_iso, "per_page": "10"},
        )
    except Exception:
        return []


def _recent_releases(repo: str, token: str | None) -> list[dict[str, Any]]:
    try:
        return gh_api(f"/repos/{repo}/releases", token=token, query={"per_page": "5"})
    except Exception:
        return []


def _render_update(
    repo: str, now: dict[str, Any], prev: dict[str, Any], commits: list[dict[str, Any]]
) -> str:
    lines = [
        "---",
        "type: github_project_update",
        f"repo: {repo}",
        f"generated_at: {now['analyzed_at']}",
        f"compared_to_snapshot: {prev.get('analyzed_at', 'unknown')}",
        "---",
        "",
        f"# Update Digest: {repo}",
        "",
        "## Metric Changes",
        *_format_delta(now, prev),
        "",
        "## Important Activity",
    ]
    if commits:
        for c in commits[:5]:
            msg = (c.get("commit", {}).get("message", "").splitlines() or [""])[0][:120]
            sha = c.get("sha", "")[:7]
            lines.append(f"- Commit {sha}: {msg}")
    else:
        lines.append("- No recent commits detected in the compared window.")

    if now.get("latest_release") != prev.get("latest_release"):
        lines.append(
            f"- Release changed: {prev.get('latest_release', 'N/A')} -> {now.get('latest_release', 'N/A')}"
        )

    lines.extend(
        [
            "",
            "## Why It Matters",
            "- Metric and activity changes may indicate project momentum or maintenance risk.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Track updates for watchlist repositories."
    )
    parser.add_argument("--memory-root", default=".memory")
    parser.add_argument("--repo", default="", help="Optional single repo owner/repo")
    parser.add_argument(
        "--config", default="", help="Optional config file path for proxy settings."
    )
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    load_runtime_config(args.config)
    paths = ensure_layout(args.memory_root)
    watchlist_file = paths["watchlist"] / "watchlist.json"
    repos = [args.repo] if args.repo else read_watchlist(watchlist_file)

    if not repos:
        raise SystemExit("watchlist is empty")

    index_path = paths["indexes"] / "project-index.jsonl"
    index = load_index(index_path)
    updated = []

    for repo in repos:
        slug = slug_from_repo(repo)
        project_dir = paths["projects"] / slug
        (project_dir / "snapshots").mkdir(parents=True, exist_ok=True)
        (project_dir / "updates").mkdir(parents=True, exist_ok=True)

        _, prev = _latest_snapshot(project_dir)
        if prev is None:
            prev = {
                "analyzed_at": "1970-01-01T00:00:00Z",
                "stars": 0,
                "forks": 0,
                "open_issues": 0,
                "watchers": 0,
                "latest_release": "N/A",
            }

        now = analyze(repo, token=token, deep=False)  # Fast analysis by default
        snapshot_path = (
            project_dir / "snapshots" / f"{now['analyzed_at'].replace(':', '-')}.json"
        )
        snapshot_path.write_text(
            json.dumps(now, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        commits = _recent_commits(
            repo, prev.get("analyzed_at", "1970-01-01T00:00:00Z"), token=token
        )
        update_md = _render_update(repo, now, prev, commits)
        day = dt.datetime.now(dt.timezone.utc).date().isoformat()
        update_path = project_dir / "updates" / f"{day}.md"
        update_path.write_text(update_md, encoding="utf-8")

        prev_index = index.get(repo, {})
        index[repo] = {
            "repo": repo,
            "slug": slug,
            "first_analyzed_at": prev_index.get(
                "first_analyzed_at", now["analyzed_at"]
            ),
            "last_analyzed_at": now["analyzed_at"],
            "profile_path": str(Path("projects") / slug / "profile.md"),
            "last_update_path": str(Path("projects") / slug / "updates" / f"{day}.md"),
            "tags": prev_index.get("tags", []),
            "status": "active",
        }
        updated.append({"repo": repo, "update_path": str(update_path)})

    save_index(index_path, index)
    print(json.dumps({"updated": updated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
