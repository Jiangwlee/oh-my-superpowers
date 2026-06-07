"""End-to-end fixture pipeline tests for mail-pipeline."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "mail-pipeline" / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestRunPipeline(unittest.TestCase):
    """Validate dry-run/apply behavior using local .eml fixtures."""

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

    def test_dry_run_outputs_events_without_writing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)
            result = self.run_script("run.py", "--fixture-dir", str(FIXTURES), data_dir=root)
            payload = json.loads(result.stdout)

            self.assertFalse((root / "files" / "fixture").exists())
            self.assertEqual("ok", payload["status"])
            self.assertFalse(payload["apply"])
            self.assertEqual("invoices", payload["events"][0]["classification"]["category"])
            self.assertEqual("", (root / "events" / "all.jsonl").read_text())

    def test_apply_writes_jsonl_attachment_and_dedupe_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)
            first = self.run_script("run.py", "--fixture-dir", str(FIXTURES), "--apply", data_dir=root)
            second = self.run_script("run.py", "--fixture-dir", str(FIXTURES), "--apply", data_dir=root)
            first_payload = json.loads(first.stdout)
            second_payload = json.loads(second.stdout)

            self.assertEqual(1, first_payload["processed"])
            self.assertEqual(0, second_payload["processed"])
            self.assertEqual(1, second_payload["skipped"])
            all_lines = [line for line in (root / "events" / "all.jsonl").read_text().splitlines() if line]
            invoice_lines = [line for line in (root / "events" / "invoices.jsonl").read_text().splitlines() if line]
            self.assertEqual(1, len(all_lines))
            self.assertEqual(1, len(invoice_lines))
            event = json.loads(all_lines[0])
            saved_path = Path(event["attachments"][0]["saved_path"])
            self.assertTrue(saved_path.exists())
            conn = sqlite3.connect(root / "state" / "processed.sqlite")
            count = conn.execute("select count(*) from processed_messages").fetchone()[0]
            conn.close()
            self.assertEqual(1, count)

    def test_apply_sanitizes_account_path_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)
            self.run_script("run.py", "--fixture-dir", str(FIXTURES), "--account", "../../outside", "--apply", data_dir=root)
            saved = list((root / "files").rglob("*invoice.pdf"))
            self.assertEqual(1, len(saved))
            self.assertTrue(saved[0].resolve().is_relative_to(root.resolve()))

    def test_apply_rejects_jsonl_output_outside_data_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)
            processors = root / "config" / "processors.yaml"
            processors.write_text(processors.read_text().replace("events/invoices.jsonl", "../outside.jsonl"), encoding="utf-8")
            with self.assertRaises(subprocess.CalledProcessError) as ctx:
                self.run_script("run.py", "--fixture-dir", str(FIXTURES), "--apply", data_dir=root)
            self.assertIn("path escapes data dir", ctx.exception.stderr)
            self.assertFalse((root.parent / "outside.jsonl").exists())

    def test_processor_without_save_attachment_does_not_write_attachment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)
            self.run_script("run.py", "--fixture-dir", str(FIXTURES), "--processor", "important", "--apply", data_dir=root)
            self.assertEqual([], list((root / "files").rglob("*invoice.pdf")))
            lines = [line for line in (root / "events" / "important.jsonl").read_text().splitlines() if line]
            event = json.loads(lines[0])
            self.assertEqual([], event["attachments"])
            self.assertNotIn("save_attachment", json.dumps(event["actions"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
