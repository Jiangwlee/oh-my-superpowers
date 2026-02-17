#!/usr/bin/env python3
"""Initialize storage layout for github-researcher."""

from __future__ import annotations

import argparse
import json

from common import ensure_layout


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap storage layout for github-researcher.")
    parser.add_argument("--memory-root", default=".memory", help="Root directory for memory data.")
    args = parser.parse_args()

    paths = ensure_layout(args.memory_root)
    print(json.dumps({"status": "ok", "layout": {k: str(v) for k, v in paths.items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
