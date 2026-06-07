"""Account config and MIME parser tests for mail-pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "mail-pipeline" / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from common import load_accounts, select_accounts  # noqa: E402
from parser import parse_file  # noqa: E402


class TestAccountsAndParser(unittest.TestCase):
    """Validate account config loading and local MIME parsing."""

    def test_load_accounts_and_select_multiple_accounts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "accounts.yaml").write_text(
                """
accounts:
  - id: work
    provider: imap
    host: imap.example.com
    port: 993
    username: me@example.com
    password_env: MAIL_PIPELINE_WORK_PASSWORD
    folders:
      inbox: INBOX
  - id: personal
    provider: imap
    host: imap.personal.example.com
    port: 993
    username: me@personal.example.com
    password_env: MAIL_PIPELINE_PERSONAL_PASSWORD
    folders:
      inbox: PersonalInbox
""",
                encoding="utf-8",
            )
            accounts = load_accounts(root)
            self.assertEqual(["work", "personal"], [item.id for item in accounts])
            self.assertEqual(["work", "personal"], [item.id for item in select_accounts(accounts, "all")])
            self.assertEqual("INBOX", select_accounts(accounts, "work")[0].inbox)
            self.assertEqual("PersonalInbox", select_accounts(accounts, "personal")[0].inbox)

    def test_accounts_list_does_not_print_secret_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir(parents=True)
            (root / "config" / "accounts.yaml").write_text(
                """
accounts:
  - id: personal
    provider: imap
    host: imap.example.com
    port: 993
    username: me@example.com
    password_env: MAIL_PIPELINE_PERSONAL_PASSWORD
""",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["MAIL_PIPELINE_DATA_DIR"] = str(root)
            env["MAIL_PIPELINE_PERSONAL_PASSWORD"] = "super-secret"
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "accounts.py"), "list"],
                cwd=str(SCRIPTS),
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual("ok", payload["status"])
            self.assertNotIn("super-secret", result.stdout)

    def test_parse_fixture_message_extracts_attachment_metadata(self) -> None:
        parsed = parse_file(FIXTURES / "invoice.eml", account_id="work")

        self.assertEqual("work", parsed["account_id"])
        self.assertEqual("Invoice INV-001", parsed["source"]["subject"])
        self.assertIn("Please find attached", parsed["text"])
        self.assertEqual(1, len(parsed["attachments"]))
        attachment = parsed["attachments"][0]
        self.assertEqual("invoice.pdf", attachment["filename"])
        self.assertEqual("application/pdf", attachment["mime_type"])
        self.assertEqual(27, attachment["size_bytes"])
        self.assertEqual(64, len(attachment["sha256"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
