#!/usr/bin/env python3
"""Manage watchlist for github-researcher."""

from __future__ import annotations

import argparse
import json
import re

from common import ensure_layout, read_watchlist, write_watchlist

REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage github-researcher watchlist.")
    parser.add_argument("action", choices=["add", "remove", "list"])
    parser.add_argument("repo", nargs="?")
    parser.add_argument("--memory-root", default=".memory")
    args = parser.parse_args()

    paths = ensure_layout(args.memory_root)
    watchlist_file = paths["watchlist"] / "watchlist.json"
    repos = read_watchlist(watchlist_file)

    if args.action == "list":
        print(json.dumps({"repos": repos}, ensure_ascii=False, indent=2))
        return

    if not args.repo:
        raise SystemExit("repo is required for add/remove, format: owner/repo")
    if not REPO_RE.match(args.repo):
        raise SystemExit(f"invalid repo format: {args.repo}")

    if args.action == "add":
        repos = sorted(set(repos + [args.repo]))
    elif args.action == "remove":
        repos = [r for r in repos if r != args.repo]

    write_watchlist(watchlist_file, repos)
    print(json.dumps({"repos": repos}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
