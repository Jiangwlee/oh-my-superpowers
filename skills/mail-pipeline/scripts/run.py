"""Run the mail-pipeline ingest."""

from __future__ import annotations

import argparse
import json

from common import data_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run mail-pipeline ingest.")
    parser.add_argument("--account", default="all", help="Account id or 'all'.")
    parser.add_argument("--processor", default="all", help="Processor name or 'all'.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum messages per account.")
    parser.add_argument("--apply", action="store_true", help="Write files/state and modify allowed mailbox state.")
    args = parser.parse_args()

    print(
        json.dumps(
            {
                "account": args.account,
                "processor": args.processor,
                "limit": args.limit,
                "apply": args.apply,
                "data_dir": str(data_dir()),
                "status": "not_implemented",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
