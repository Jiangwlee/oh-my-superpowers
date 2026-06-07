"""Explicit mailbox action interfaces for mail-pipeline.

These commands execute exactly what the calling AI agent decided after
reading message content. Scripts make no judgment about which messages to
touch. Supported actions are `\\Seen` flagging and folder moves; permanent
deletion is not offered.
"""

from __future__ import annotations

import argparse
import imaplib
import json
import os
import ssl
import sys
from datetime import datetime, timezone

from common import append_jsonl, data_dir, events_dir, load_accounts, select_accounts


def _fail(error: str) -> None:
    print(json.dumps({"status": "error", "error": error}, ensure_ascii=False, indent=2), file=sys.stderr)
    raise SystemExit(1)


def _folder_map(account) -> dict[str, str | None]:
    return {
        "inbox": account.inbox,
        "processed": account.processed,
        "needs_review": account.needs_review,
        "trash": account.trash,
    }


def _connect(account) -> imaplib.IMAP4_SSL:
    password = os.environ.get(account.password_env) if account.password_env else None
    if not password:
        raise ValueError(f"missing password env: {account.password_env or '<unset>'} for account {account.id!r}")
    context = ssl.create_default_context()
    client = imaplib.IMAP4_SSL(account.host, account.port, ssl_context=context, timeout=30)
    client.login(account.username, password)
    status, _ = client.select(account.inbox)
    if status != "OK":
        client.logout()
        raise ValueError(f"select failed for inbox {account.inbox!r} on account {account.id!r}")
    return client


def _mark_read(client: imaplib.IMAP4_SSL, uids: list[str]) -> list[str]:
    status, _ = client.uid("STORE", ",".join(uids), "+FLAGS.SILENT", r"(\Seen)")
    return [] if status == "OK" else [f"mark_read failed for uids {','.join(uids)}"]


def _move(client: imaplib.IMAP4_SSL, uids: list[str], target: str) -> list[str]:
    errors: list[str] = []
    has_move = any(str(cap).upper() == "MOVE" for cap in client.capabilities)
    quoted = f'"{target}"'
    expunge_needed = False
    for uid in uids:
        if has_move:
            status, _ = client.uid("MOVE", uid, quoted)
            if status != "OK":
                errors.append(f"move failed for uid {uid} -> {target}")
        else:
            status, _ = client.uid("COPY", uid, quoted)
            if status != "OK":
                errors.append(f"copy failed for uid {uid} -> {target}")
                continue
            client.uid("STORE", uid, "+FLAGS.SILENT", r"(\Deleted)")
            expunge_needed = True
    if expunge_needed:
        client.expunge()
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute an explicit mailbox action decided by the calling agent.")
    parser.add_argument("action", choices=["mark-read", "move"])
    parser.add_argument("--account", required=True, help="Account id.")
    parser.add_argument("--uid", action="append", required=True, help="IMAP uid in the account inbox (repeatable).")
    parser.add_argument("--to", default="trash", help="Logical target folder for `move` (from the account folders map).")
    parser.add_argument("--reason", help="Why the agent decided this action; recorded in the audit event.")
    args = parser.parse_args()

    root = data_dir()
    try:
        account = select_accounts(load_accounts(root), args.account)[0]
    except Exception as exc:
        _fail(str(exc))

    target = None
    if args.action == "move":
        target = _folder_map(account).get(args.to)
        if not target:
            _fail(f"folder {args.to!r} not configured for account {account.id!r}")

    try:
        client = _connect(account)
    except (ValueError, OSError, imaplib.IMAP4.error) as exc:
        _fail(str(exc))
    try:
        if args.action == "mark-read":
            errors = _mark_read(client, args.uid)
        else:
            errors = _move(client, args.uid, target)
        client.logout()
    except (OSError, imaplib.IMAP4.error) as exc:
        _fail(f"mailbox action failed: {exc}")

    event = {
        "schema_version": "1.0",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "account_id": account.id,
        "source": {"mailbox": account.inbox, "imap_uids": args.uid},
        "actions": [{"type": "mark_read" if args.action == "mark-read" else "move_email", "target": args.to if args.action == "move" else None, "reason": args.reason}],
        "status": "mailbox_action" if not errors else "mailbox_action_failed",
        "errors": errors,
    }
    append_jsonl(events_dir(root) / "all.jsonl", event)

    if errors:
        _fail("; ".join(errors))
    print(
        json.dumps(
            {"status": "ok", "action": args.action, "account": account.id, "uids": args.uid, "target": args.to if args.action == "move" else None},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
