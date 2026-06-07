"""Show one message in full for agent judgment. Read-only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import data_dir, load_accounts, select_accounts
from mailfetch import fetch_message
from parser import body_text, parse_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Show one inbox message in full (read-only).")
    parser.add_argument("--account", required=True, help="Account id.")
    parser.add_argument("--uid", required=True, help="IMAP uid (or file stem in fixture mode).")
    parser.add_argument("--fixture-dir", help="Read local .eml files instead of IMAP.")
    args = parser.parse_args()

    root = data_dir()
    try:
        if args.fixture_dir:
            path = Path(args.fixture_dir).expanduser() / f"{args.uid}.eml"
            if not path.exists():
                raise ValueError(f"fixture not found: {path}")
            message = parse_file(path, account_id=args.account)
            message["source"]["imap_uid"] = args.uid
        else:
            account = select_accounts(load_accounts(root), args.account)[0]
            message = fetch_message(account, args.uid)
            if message is None:
                raise ValueError(f"message uid {args.uid!r} not found in inbox of account {account.id!r}")
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)

    print(
        json.dumps(
            {
                "status": "ok",
                "source": message["source"],
                "body": body_text(message),
                "attachments": [
                    {"filename": item["filename"], "mime_type": item["mime_type"], "size_bytes": item["size_bytes"]}
                    for item in message.get("attachments") or []
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
