"""Static and CLI contract tests for authenticated Taoguba search."""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SEARCH_SCRIPT = (
    ROOT / "skills" / "web-operator" / "scripts" / "sites" / "taoguba" / "search.sh"
)
CLI = ROOT / "cli" / "web-operator" / "main.py"


class TaogubaSearchContractTest(unittest.TestCase):
    """Validate the public contract without requiring Chrome."""

    def test_year_is_required_before_browser_access(self) -> None:
        result = subprocess.run(
            ["bash", str(SEARCH_SCRIPT), "1112 复盘", "5"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(len(result.stderr.splitlines()), 1)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["error"]["code"], "invalid_year")

    def test_invalid_sort_is_compact_json(self) -> None:
        result = subprocess.run(
            [
                "bash",
                str(SEARCH_SCRIPT),
                "1112 复盘",
                "5",
                "--year",
                "2024",
                "--sort",
                "popular",
            ],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(len(result.stderr.splitlines()), 1)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["error"]["code"], "invalid_sort")

    def test_limit_above_cap_is_rejected(self) -> None:
        result = subprocess.run(
            [
                "bash",
                str(SEARCH_SCRIPT),
                "1112 复盘",
                "51",
                "--year",
                "2024",
            ],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(len(result.stderr.splitlines()), 1)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["error"]["code"], "invalid_limit")

    def test_search_is_anchored_to_result_cards(self) -> None:
        source = SEARCH_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("document.querySelectorAll('.topic_Item')", source)
        self.assertIn("requested_filters", source)
        self.assertIn("applied_filters", source)
        self.assertIn("published_at_asia_shanghai", source)
        self.assertNotIn("document.querySelectorAll('a')", source)

    def test_public_cli_help_documents_taoguba_filters(self) -> None:
        environment = os.environ.copy()
        environment["OMP_HOME"] = str(ROOT)
        result = subprocess.run(
            ["uv", "run", str(CLI), "search", "--help"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("--year", result.stdout)
        self.assertIn("--sort", result.stdout)
        self.assertIn("1112 复盘", result.stdout)


if __name__ == "__main__":
    unittest.main()
