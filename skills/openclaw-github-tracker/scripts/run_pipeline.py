#!/usr/bin/env python3
"""Run non-trending GitHub tracker workflow in one command.

Trending collection is intentionally manual/browser-driven per SKILL.md.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from common import ensure_layout, load_index, read_watchlist


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return (proc.stdout or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run analyze/track stages for watchlist repositories.")
    parser.add_argument("--memory-root", default=".memory")
    parser.add_argument("--config", default="", help="Optional config file path for proxy settings.")
    parser.add_argument(
        "--analyze-mode",
        choices=["new", "all", "none"],
        default="new",
        help="Analyze new watchlist repos, all repos, or skip analysis.",
    )
    parser.add_argument("--skip-track", action="store_true", help="Skip update tracking stage.")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    py = sys.executable

    _run([py, str(script_dir / "bootstrap_layout.py"), "--memory-root", args.memory_root])

    paths = ensure_layout(args.memory_root)
    watchlist_file = paths["watchlist"] / "watchlist.json"
    repos = read_watchlist(watchlist_file)
    index = load_index(paths["indexes"] / "project-index.jsonl")

    analyzed: list[str] = []
    if args.analyze_mode != "none":
        if args.analyze_mode == "new":
            targets = [r for r in repos if r not in index]
        else:
            targets = repos
        for repo in targets:
            _run(
                [
                    py,
                    str(script_dir / "analyze_project.py"),
                    repo,
                    "--memory-root",
                    args.memory_root,
                    *(["--config", args.config] if args.config else []),
                ]
            )
            analyzed.append(repo)

    track_output = ""
    if not args.skip_track and repos:
        track_output = _run(
            [
                py,
                str(script_dir / "track_updates.py"),
                "--memory-root",
                args.memory_root,
                *(["--config", args.config] if args.config else []),
            ]
        )

    print(
        json.dumps(
            {
                "status": "ok",
                "trending_step": "manual_browser_required",
                "watchlist_size": len(repos),
                "analyzed": analyzed,
                "tracking_ran": not args.skip_track and bool(repos),
                "tracking_output": track_output,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
