"""Initialize mail-pipeline storage."""

from __future__ import annotations

import argparse
import json

from common import data_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize mail-pipeline storage.")
    parser.add_argument("--dry-run", action="store_true", help="Preview directories without writing.")
    args = parser.parse_args()

    root = data_dir()
    plan = {
        "data_dir": str(root),
        "directories": ["config", "events", "files", "state", "logs"],
        "dry_run": args.dry_run,
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))

    if args.dry_run:
        return
    for name in plan["directories"]:
        (root / name).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
