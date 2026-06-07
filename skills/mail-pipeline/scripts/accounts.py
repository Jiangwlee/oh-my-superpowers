"""Account commands for mail-pipeline."""

# /// script
# dependencies = ["pyyaml"]
# ///

from __future__ import annotations

import argparse
import imaplib
import json
import os
import ssl
import sys

from common import account_public_dict, data_dir, load_accounts, select_accounts


def _check_account(account) -> dict:
    missing = []
    if not account.host:
        missing.append("host")
    if not account.username:
        missing.append("username")
    if not account.password_env:
        missing.append("password_env")
    password = os.environ.get(account.password_env) if account.password_env else None
    if account.password_env and password is None:
        missing.append(f"env:{account.password_env}")
    if missing:
        return {
            "id": account.id,
            "ok": False,
            "reason": "missing " + ", ".join(missing),
        }

    try:
        context = ssl.create_default_context()
        with imaplib.IMAP4_SSL(account.host, account.port, ssl_context=context, timeout=15) as client:
            client.login(account.username, password)
            status, _ = client.select(account.inbox, readonly=True)
            if status != "OK":
                return {"id": account.id, "ok": False, "reason": f"select failed for inbox {account.inbox!r}"}
            client.logout()
        return {"id": account.id, "ok": True, "reason": "connected"}
    except Exception as exc:  # pragma: no cover - real network path
        return {"id": account.id, "ok": False, "reason": type(exc).__name__}


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect mail-pipeline accounts.")
    parser.add_argument("action", choices=["list", "check"])
    parser.add_argument("--account", default="all", help="Account id or 'all'.")
    args = parser.parse_args()

    try:
        accounts = select_accounts(load_accounts(data_dir()), args.account)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)

    if args.action == "list":
        payload = {"status": "ok", "accounts": [account_public_dict(account) for account in accounts]}
    else:
        checks = [_check_account(account) for account in accounts]
        payload = {"status": "ok" if all(item["ok"] for item in checks) else "error", "checks": checks}
        if payload["status"] != "ok":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            raise SystemExit(1)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
