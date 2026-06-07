"""List inbox messages for agent triage. Read-only."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from common import already_processed, data_dir, dedupe_key, load_accounts, open_dedupe_db, select_accounts
from mailfetch import fetch_messages, message_on_or_after
from parser import body_text, parse_file

SNIPPET_LENGTH = 200


def _summary(message: dict, conn) -> dict:
    return {
        "imap_uid": message["source"].get("imap_uid"),
        "account_id": message["account_id"],
        "date": message["source"].get("date"),
        "from": message["source"].get("from"),
        "subject": message["source"].get("subject"),
        "snippet": body_text(message)[:SNIPPET_LENGTH],
        "attachments": [item["filename"] for item in message.get("attachments") or []],
        "processed_before": already_processed(conn, dedupe_key(message)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="List inbox messages for agent triage (read-only).")
    parser.add_argument("--account", default="all", help="Account id or 'all'.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum messages per account.")
    parser.add_argument("--since", help="Only list messages dated on/after this day (YYYY-MM-DD).")
    parser.add_argument("--include-seen", action="store_true", help="Also list already-read messages (default: unseen only).")
    parser.add_argument("--fixture-dir", help="Read local .eml files instead of IMAP (uid = file stem).")
    args = parser.parse_args()

    try:
        since = date.fromisoformat(args.since) if args.since else None
    except ValueError as exc:
        print(json.dumps({"status": "error", "error": f"invalid --since: {exc}"}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)

    root = data_dir()
    total_matched = 0
    try:
        if args.fixture_dir:
            fixture_dir = Path(args.fixture_dir).expanduser()
            account_id = args.account if args.account != "all" else "fixture"
            paths = sorted(fixture_dir.glob("*.eml"))
            total_matched = len(paths)
            messages = []
            for path in paths[: args.limit]:
                message = parse_file(path, account_id=account_id)
                message["source"]["imap_uid"] = path.stem
                messages.append(message)
            if since:
                messages = [message for message in messages if message_on_or_after(message, since)]
        else:
            accounts = select_accounts(load_accounts(root), args.account)
            messages = []
            for account in accounts:
                fetched, matched = fetch_messages(account, args.limit, since, unseen_only=not args.include_seen)
                messages.extend(fetched)
                total_matched += matched
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)

    conn = open_dedupe_db(root, create=False)
    summaries = [_summary(message, conn) for message in messages]
    if conn is not None:
        conn.close()

    print(
        json.dumps(
            {
                "status": "ok",
                "count": len(summaries),
                "total_matched": total_matched,
                "truncated": total_matched > args.limit,
                "messages": summaries,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
