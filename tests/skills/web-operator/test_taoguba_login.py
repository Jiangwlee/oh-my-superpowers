"""Static and CLI contract tests for the Taoguba login SOP.

Covers: public help, compact invalid-input errors, and credential-data redlines.
"""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOGIN_SCRIPT = (
    ROOT / "skills" / "web-operator" / "scripts" / "sites" / "taoguba" / "login.sh"
)
CLI = ROOT / "cli" / "web-operator" / "main.py"


class TaogubaLoginContractTest(unittest.TestCase):
    """Validate the non-secret public contract without requiring Chrome."""

    def test_invalid_timeout_is_compact_json_on_stderr(self) -> None:
        result = subprocess.run(
            ["bash", str(LOGIN_SCRIPT), "0"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(len(result.stderr.splitlines()), 1)
        payload = json.loads(result.stderr)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["site"], "taoguba")
        self.assertEqual(payload["error"]["code"], "invalid_timeout")

    def test_script_does_not_export_browser_secrets(self) -> None:
        source = LOGIN_SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("document.cookie", source)
        self.assertNotIn("localStorage", source)
        self.assertNotIn("sessionStorage", source)
        self.assertNotIn("username:", source)
        self.assertNotIn("password:", source)

    def test_public_cli_help_documents_login_command(self) -> None:
        environment = os.environ.copy()
        environment["OMP_HOME"] = str(ROOT)
        result = subprocess.run(
            ["uv", "run", str(CLI), "taoguba", "login", "--help"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("taoguba login", result.stdout)
        self.assertIn("--timeout", result.stdout)
        self.assertIn("--target", result.stdout)


if __name__ == "__main__":
    unittest.main()
