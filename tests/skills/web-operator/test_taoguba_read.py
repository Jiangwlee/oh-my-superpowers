"""Static and CLI contract tests for Taoguba main-post reading."""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
READ_SCRIPT = (
    ROOT
    / "skills"
    / "web-operator"
    / "scripts"
    / "sites"
    / "taoguba"
    / "open-post.sh"
)
READ_URL_SCRIPT = ROOT / "skills" / "web-operator" / "scripts" / "read-url.sh"
CLI = ROOT / "cli" / "web-operator" / "main.py"


class TaogubaReadContractTest(unittest.TestCase):
    """Validate the JSON and routing contract without requiring Chrome."""

    def test_invalid_url_is_compact_json_on_stderr(self) -> None:
        result = subprocess.run(
            ["bash", str(READ_SCRIPT), "https://example.com/post"],
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
        self.assertEqual(payload["error"]["code"], "invalid_url")

    def test_public_cli_help_documents_read_command(self) -> None:
        environment = os.environ.copy()
        environment["OMP_HOME"] = str(ROOT)
        result = subprocess.run(
            ["uv", "run", str(CLI), "taoguba", "read", "--help"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("taoguba read", result.stdout)
        self.assertIn("main-post URL", result.stdout)
        self.assertIn("--target", result.stdout)
        self.assertIn("compact JSON", result.stdout)

    def test_all_taoguba_read_routes_share_one_script(self) -> None:
        cli_source = CLI.read_text(encoding="utf-8")
        read_url_source = READ_URL_SCRIPT.read_text(encoding="utf-8")

        self.assertIn('str(SITES_DIR / "taoguba" / "open-post.sh")', cli_source)
        self.assertIn(
            'scripts/sites/taoguba/open-post.sh" "$URL"',
            read_url_source,
        )

    def test_reader_does_not_export_browser_secrets(self) -> None:
        source = READ_SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("document.cookie", source)
        self.assertNotIn("localStorage", source)
        self.assertNotIn("sessionStorage", source)
        self.assertNotIn("password:", source)
        self.assertIn("jq -c .", source)
        self.assertIn("published_at_asia_shanghai", source)


if __name__ == "__main__":
    unittest.main()
