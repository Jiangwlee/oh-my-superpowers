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

FIELDS = {
    "invoice_date": "2026-06-04",
    "invoice_number": "26427000000465806619",
    "amount": 314.4,
    "tax_rate": "13%",
    "purchase_content": "通信服务费",
    "seller": "测试电信公司",
    "confidence": 0.95,
}


class TestRunPipeline(unittest.TestCase):
    """Validate dry-run/apply/submit behavior using local .eml fixtures."""

    def run_script(self, script: str, *args: str, data_dir: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["MAIL_PIPELINE_DATA_DIR"] = str(data_dir)
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args],
            cwd=str(SCRIPTS),
            env=env,
            text=True,
            capture_output=True,
            check=check,
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
            self.assertEqual({}, payload["events"][0]["extracted"])
            self.assertEqual(1, len(payload["pending"]))
            self.assertEqual("", (root / "events" / "all.jsonl").read_text())

    def test_apply_stages_pending_and_submit_finalizes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)
            first = self.run_script("run.py", "--fixture-dir", str(FIXTURES), "--apply", data_dir=root)
            payload = json.loads(first.stdout)
            self.assertEqual(1, payload["processed"])
            pending = payload["pending"][0]
            staged = Path(pending["files"][0])
            self.assertTrue(staged.exists())
            self.assertTrue((root / "state" / "pending" / f"{pending['pending_id']}.json").exists())
            staged_event = json.loads((root / "events" / "all.jsonl").read_text().splitlines()[0])
            self.assertEqual("pending_extraction", staged_event["status"])

            submit = self.run_script("submit.py", "--id", pending["pending_id"], "--fields", json.dumps(FIELDS), data_dir=root)
            submit_payload = json.loads(submit.stdout)
            final = Path(submit_payload["files"][0])
            self.assertEqual("2026-06-04_26427000000465806619_测试电信公司.pdf", final.name)
            self.assertTrue(final.exists())
            self.assertFalse(staged.exists())
            self.assertFalse((root / "state" / "pending" / f"{pending['pending_id']}.json").exists())

            lines = [json.loads(line) for line in (root / "events" / "all.jsonl").read_text().splitlines() if line]
            self.assertEqual(["pending_extraction", "processed"], [event["status"] for event in lines])
            self.assertEqual(FIELDS["invoice_number"], lines[1]["extracted"]["invoice"]["invoice_number"])

            second = self.run_script("run.py", "--fixture-dir", str(FIXTURES), "--apply", data_dir=root)
            second_payload = json.loads(second.stdout)
            self.assertEqual(0, second_payload["processed"])
            self.assertEqual(1, second_payload["skipped"])
            conn = sqlite3.connect(root / "state" / "processed.sqlite")
            count = conn.execute("select count(*) from processed_messages").fetchone()[0]
            conn.close()
            self.assertEqual(1, count)

    def test_dry_run_reflects_dedupe_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)
            self.run_script("run.py", "--fixture-dir", str(FIXTURES), "--apply", data_dir=root)
            preview = json.loads(self.run_script("run.py", "--fixture-dir", str(FIXTURES), data_dir=root).stdout)
            self.assertEqual(0, preview["processed"])
            self.assertEqual(1, preview["skipped"])

    def test_submit_does_not_overwrite_different_file_with_same_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)
            first = json.loads(self.run_script("run.py", "--fixture-dir", str(FIXTURES), "--apply", data_dir=root).stdout)
            second = json.loads(self.run_script("run.py", "--fixture-dir", str(FIXTURES / "zip"), "--apply", data_dir=root).stdout)
            self.run_script("submit.py", "--id", first["pending"][0]["pending_id"], "--fields", json.dumps(FIELDS), data_dir=root)
            result = self.run_script("submit.py", "--id", second["pending"][0]["pending_id"], "--fields", json.dumps(FIELDS), data_dir=root)
            final = Path(json.loads(result.stdout)["files"][0])
            clean = final.parent / "2026-06-04_26427000000465806619_测试电信公司.pdf"
            self.assertTrue(clean.exists())
            self.assertNotEqual(clean, final)
            self.assertTrue(final.name.startswith("2026-06-04_26427000000465806619_测试电信公司_"))
            self.assertTrue(final.exists())

    def test_zip_attachment_expands_pdf_members(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)
            result = self.run_script("run.py", "--fixture-dir", str(FIXTURES / "zip"), "--apply", data_dir=root)
            payload = json.loads(result.stdout)
            pending = payload["pending"][0]
            self.assertEqual(1, len(pending["files"]))
            staged = Path(pending["files"][0])
            self.assertTrue(staged.exists())
            self.assertTrue(staged.read_bytes().startswith(b"%PDF-"))
            manifest = json.loads((root / "state" / "pending" / f"{pending['pending_id']}.json").read_text())
            self.assertEqual("zip", manifest["attachments"][0]["origin"])
            self.assertEqual("invoice.zip", manifest["attachments"][0]["source_zip"])

    def test_submit_rejects_provider_metadata_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)
            first = self.run_script("run.py", "--fixture-dir", str(FIXTURES), "--apply", data_dir=root)
            pending = json.loads(first.stdout)["pending"][0]
            manifest_path = root / "state" / "pending" / f"{pending['pending_id']}.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["provider_meta"] = {"invoice_number": "DIFFERENT", "amount": 1.0}
            manifest_path.write_text(json.dumps(manifest))

            result = self.run_script(
                "submit.py", "--id", pending["pending_id"], "--fields", json.dumps(FIELDS), data_dir=root, check=False
            )
            self.assertEqual(1, result.returncode)
            error = json.loads(result.stderr)
            self.assertEqual(2, len(error["mismatches"]))
            self.assertTrue(manifest_path.exists())

    def test_submit_rejects_invalid_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)
            first = self.run_script("run.py", "--fixture-dir", str(FIXTURES), "--apply", data_dir=root)
            pending = json.loads(first.stdout)["pending"][0]
            bad = {**FIELDS, "invoice_date": "not-a-date"}
            result = self.run_script(
                "submit.py", "--id", pending["pending_id"], "--fields", json.dumps(bad), data_dir=root, check=False
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("malformed invoice field", result.stderr)

    def test_apply_sanitizes_account_path_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mail-data"
            self.run_script("init.py", data_dir=root)
            self.run_script("run.py", "--fixture-dir", str(FIXTURES), "--account", "../../outside", "--apply", data_dir=root)
            saved = list((root / "files").rglob("*.pdf"))
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
            self.assertEqual([], list((root / "files").rglob("*.pdf")))
            lines = [line for line in (root / "events" / "important.jsonl").read_text().splitlines() if line]
            event = json.loads(lines[0])
            self.assertEqual([], event["attachments"])
            self.assertNotIn("save_attachment", json.dumps(event["actions"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
