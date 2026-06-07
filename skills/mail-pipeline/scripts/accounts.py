"""Account commands for mail-pipeline."""

from __future__ import annotations

import argparse
import json

from common import data_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect mail-pipeline accounts.")
    parser.add_argument("action", choices=["list", "check"])
    parser.add_argument("--account", default="all", help="Account id or 'all'.")
    args = parser.parse_args()

    print(
        json.dumps(
            {
                "action": args.action,
                "account": args.account,
                "config": str(data_dir() / "config" / "accounts.yaml"),
                "status": "not_implemented",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
