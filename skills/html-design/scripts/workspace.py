#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-").lower()
    return slug or "html-design"


def init_workspace(root: Path, slug: str) -> int:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    workspace = root.expanduser().resolve() / f"html-design-{timestamp}-{_slug(slug)}"
    for rel in ["designs", "prototypes", "exports"]:
        (workspace / rel).mkdir(parents=True, exist_ok=True)
    (workspace / "DESIGN.md").write_text(
        "# HTML Design Prototype\n\n"
        "## Scenario\n\n"
        "## Information Organization\n\n"
        "## Visual Direction\n\n"
        "## Prototype Notes\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "workspace": str(workspace),
                "designs": str(workspace / "designs"),
                "prototypes": str(workspace / "prototypes"),
                "exports": str(workspace / "exports"),
                "design": str(workspace / "DESIGN.md"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="workspace.py")
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--root", required=True, type=Path)
    p_init.add_argument("--slug", required=True)
    args = parser.parse_args()
    if args.command == "init":
        return init_workspace(args.root, args.slug)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
