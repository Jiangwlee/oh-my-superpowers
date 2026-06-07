"""Shared read-only IMAP fetching for mail-pipeline scripts."""

from __future__ import annotations

import imaplib
import os
import ssl
from datetime import date, datetime

from parser import parse_bytes

_IMAP_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def imap_since(value: date) -> str:
    """Format a date as a locale-independent IMAP SEARCH date."""
    return f"{value.day:02d}-{_IMAP_MONTHS[value.month - 1]}-{value.year}"


def message_on_or_after(message: dict, since: date) -> bool:
    """Return True when the message date is on/after the given day (or unknown)."""
    raw = message["source"].get("date")
    if not raw:
        return True
    try:
        return datetime.fromisoformat(raw).date() >= since
    except ValueError:
        return True


def _connect_readonly(account) -> imaplib.IMAP4_SSL:
    password = os.environ.get(account.password_env) if account.password_env else None
    if not password:
        raise ValueError(f"missing password env: {account.password_env or '<unset>'} for account {account.id!r}")
    context = ssl.create_default_context()
    client = imaplib.IMAP4_SSL(account.host, account.port, ssl_context=context, timeout=30)
    client.login(account.username, password)
    status, _ = client.select(account.inbox, readonly=True)
    if status != "OK":
        client.logout()
        raise ValueError(f"select failed for inbox {account.inbox!r} on account {account.id!r}")
    return client


def fetch_messages(account, limit: int, since: date | None, unseen_only: bool) -> tuple[list[dict], int]:
    """Fetch the most recent inbox messages for one account, read-only.

    Returns (messages, total_matched); when total_matched exceeds limit the
    OLDEST messages are the ones dropped.
    """
    criteria: list[str] = []
    if unseen_only:
        criteria.append("UNSEEN")
    if since:
        criteria += ["SINCE", imap_since(since)]
    if not criteria:
        criteria = ["ALL"]
    messages: list[dict] = []
    client = _connect_readonly(account)
    try:
        status, data = client.uid("search", None, *criteria)
        if status != "OK":
            raise ValueError(f"uid search failed on account {account.id!r}")
        uids = data[0].split()
        for uid in uids[-limit:]:
            status, msg_data = client.uid("fetch", uid, "(BODY.PEEK[])")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue
            messages.append(parse_bytes(msg_data[0][1], account_id=account.id, mailbox=account.inbox, imap_uid=uid.decode()))
    finally:
        client.logout()
    return messages, len(uids)


def fetch_message(account, uid: str) -> dict | None:
    """Fetch one inbox message by uid, read-only."""
    client = _connect_readonly(account)
    try:
        status, msg_data = client.uid("fetch", uid, "(BODY.PEEK[])")
        if status != "OK" or not msg_data or msg_data[0] is None:
            return None
        return parse_bytes(msg_data[0][1], account_id=account.id, mailbox=account.inbox, imap_uid=uid)
    finally:
        client.logout()
