#!/usr/bin/env python3
"""Track updates for watchlist repositories."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib

from analyze_repo import analyze_repo
from common import ensure_layout, load_index, read_watchlist, save_index, slug_from_repo


def latest_snapshot(project_dir: pathlib.Path) -> dict | None:
    snaps = sorted((project_dir / "snapshots").glob("*.json"))
    if not snaps:
        return None
    return json.loads(snaps[-1].read_text(encoding="utf-8"))


def metric_delta(prev: dict, now: dict, key: str) -> str:
    p = prev.get(key)
    n = now.get(key)
    if p is None or n is None:
        return f"- {key}: N/A (fallback mode)"
    d = int(n) - int(p)
    sign = "+" if d >= 0 else ""
    return f"- {key}: {p} -> {n} ({sign}{d})"


def render_update(repo: str, prev: dict, now: dict) -> str:
    lines = [
        "---",
        "type: github_project_update",
        f"repo: {repo}",
        f"generated_at: {now['analyzed_at']}",
        f"source: {now.get('source', 'unknown')}",
        "---",
        "",
        f"# Update Digest: {repo}",
        "",
        "## Metric Changes",
        metric_delta(prev, now, "stars"),
        metric_delta(prev, now, "forks"),
        metric_delta(prev, now, "open_issues"),
        metric_delta(prev, now, "watchers"),
        "",
        "## Commit Signals",
    ]
    prev_commit = prev.get("latest_commit")
    now_commit = now.get("latest_commit")
    if prev_commit and now_commit and prev_commit != now_commit:
        lines.append(f"- latest_commit: {prev_commit[:7]} -> {now_commit[:7]}")
    elif now_commit:
        lines.append(f"- latest_commit: {now_commit[:7]} (unchanged or baseline)")
    else:
        lines.append("- Commit hash unavailable in gh-only mode.")

    if now.get("pushed_at") != prev.get("pushed_at"):
        lines.append(f"- pushed_at: {prev.get('pushed_at', 'N/A')} -> {now.get('pushed_at', 'N/A')}")

    lines.extend(
        [
            "",
            "## Why It Matters",
            "- Use these deltas to judge project momentum and maintenance activity.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Track updates for watched repositories.")
    parser.add_argument("--memory-root", default=".memory")
    parser.add_argument("--repo", default="", help="Optional single repo owner/repo")
    args = parser.parse_args()

    paths = ensure_layout(args.memory_root)
    watchlist_file = paths["watchlist"] / "watchlist.json"
    repos = [args.repo] if args.repo else read_watchlist(watchlist_file)
    if not repos:
        raise SystemExit("watchlist is empty")

    index_path = paths["indexes"] / "project-index.jsonl"
    index = load_index(index_path)

    results: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()

    for repo in repos:
        slug = slug_from_repo(repo)
        project_dir = paths["projects"] / slug
        snapshots_dir = project_dir / "snapshots"
        updates_dir = project_dir / "updates"
        project_dir.mkdir(parents=True, exist_ok=True)
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        updates_dir.mkdir(parents=True, exist_ok=True)

        prev = latest_snapshot(project_dir) or {}
        try:
            now = analyze_repo(repo, cache_root=paths["base"] / "cache", deep=False)
        except Exception as exc:
            failures.append(
                {
                    "repo": repo,
                    "error": (
                        f"GitHub access failed: {exc}. "
                        "Please verify network access to github.com. "
                        "If you are behind a restricted network, configure a local proxy and retry."
                    ),
                }
            )
            continue

        snapshot_path = snapshots_dir / f"{now['analyzed_at'].replace(':', '-')}.json"
        snapshot_path.write_text(json.dumps(now, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        profile_path = project_dir / "profile.md"
        if not profile_path.exists():
            profile_path.write_text(
                "# Profile Missing\n\nRun analyze_repo.py first to generate full profile.\n",
                encoding="utf-8",
            )

        update_path = updates_dir / f"{today}.md"
        update_path.write_text(render_update(repo, prev, now), encoding="utf-8")

        prev_index = index.get(repo, {})
        index[repo] = {
            "repo": repo,
            "slug": slug,
            "first_analyzed_at": prev_index.get("first_analyzed_at", now["analyzed_at"]),
            "last_analyzed_at": now["analyzed_at"],
            "profile_path": str(pathlib.Path("projects") / slug / "profile.md"),
            "last_update_path": str(pathlib.Path("projects") / slug / "updates" / f"{today}.md"),
            "status": "active",
        }

        results.append({"repo": repo, "update": str(update_path), "snapshot": str(snapshot_path), "source": str(now.get("source"))})

    save_index(index_path, index)
    output: dict[str, object] = {"updated": results}
    if failures:
        output["failures"] = failures
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
