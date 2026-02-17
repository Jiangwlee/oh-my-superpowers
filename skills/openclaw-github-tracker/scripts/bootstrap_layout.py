#!/usr/bin/env python3
"""Initialize claude-mem friendly storage layout for GitHub tracker skill."""

from __future__ import annotations

import argparse
import json

from common import ensure_layout


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap memory layout for openclaw-github-tracker.")
    parser.add_argument("--memory-root", default=".memory", help="Root directory for memory files.")
    args = parser.parse_args()

    paths = ensure_layout(args.memory_root)
    summary = {k: str(v) for k, v in paths.items()}
    print(json.dumps({"status": "ok", "layout": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

