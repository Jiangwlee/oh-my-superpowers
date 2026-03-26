"""Initialize a deep-research workspace.

Usage:
    omp-deep-research init --topic "<topic>" [--slug "<slug>"] [--mode quick|default|deep]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime

from common import data_dir, dump_json, ensure_workspace_dirs, slugify, timestamp_prefix


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Initialize a deep-research workspace.")
    parser.add_argument("--topic", required=True, help="Research topic.")
    parser.add_argument("--slug", help="Optional explicit workspace slug.")
    parser.add_argument(
        "--mode",
        choices=["quick", "default", "deep"],
        default="default",
        help="Research depth mode.",
    )
    return parser.parse_args()


def main() -> None:
    """Create the workspace and print its metadata as JSON."""

    args = parse_args()
    root = data_dir()
    root.mkdir(parents=True, exist_ok=True)

    slug = args.slug or slugify(args.topic)
    workspace = root / f"{timestamp_prefix()}-{slug}"
    paths = ensure_workspace_dirs(workspace)

    state = {
        "topic": args.topic,
        "slug": slug,
        "mode": args.mode,
        "workspace": str(workspace),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "initialized",
        "report_files": {"brief": None, "full_report": None},
    }
    dump_json(paths.state_file, state)

    print(
        json.dumps(
            {
                "status": "ok",
                "workspace": str(workspace),
                "state_file": str(paths.state_file),
                "reports_dir": str(paths.reports_dir),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
