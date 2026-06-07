"""Storage/config tests for mail-pipeline."""

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


class TestConfigStorage(unittest.TestCase):
    """Validate init and status against a temporary data dir."""

    def run_script(self, script: str, *args: str, data_dir: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["MAIL_PIPELINE_DATA_DIR"] = str(data_dir)
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args],
            cwd=str(SCRIPTS),
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

    def test_init_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            result = self.run_script("init.py", "--dry-run", data_dir=root)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["dry_run"])
            self.assertEqual(str(root), payload["data_dir"])
            self.assertFalse(root.exists())

    def test_init_apply_creates_templates_and_event_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)

            self.assertTrue((root / "config" / "accounts.yaml").exists())
            self.assertTrue((root / "config" / "processors.yaml").exists())
            self.assertIn("password_env:", (root / "config" / "accounts.yaml").read_text())
            self.assertNotIn("password:", (root / "config" / "accounts.yaml").read_text())
            for name in ["all.jsonl", "invoices.jsonl"]:
                self.assertTrue((root / "events" / name).exists(), name)

    def test_status_reports_initialized_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)
            result = self.run_script("status.py", data_dir=root)
            payload = json.loads(result.stdout)

            self.assertEqual("ready", payload["status"])
            self.assertTrue(payload["config"]["accounts_exists"])
            self.assertEqual(0, payload["event_counts"]["all.jsonl"])

    def test_status_reports_partial_for_empty_existing_data_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            root.mkdir()
            result = self.run_script("status.py", data_dir=root)
            payload = json.loads(result.stdout)

            self.assertEqual("partial", payload["status"])
            self.assertFalse(payload["config"]["accounts_exists"])
            self.assertFalse(payload["directories"]["events"])

    def test_status_reports_not_initialized_when_root_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            result = self.run_script("status.py", data_dir=root)
            payload = json.loads(result.stdout)

            self.assertEqual("not_initialized", payload["status"])
            self.assertFalse(payload["exists"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
