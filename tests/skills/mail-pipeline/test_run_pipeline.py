"""End-to-end fixture tests for the mail-pipeline interfaces (list/show/stage/submit/mailbox)."""

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


class TestPipelineInterfaces(unittest.TestCase):
    """Validate the agent-facing interfaces using local .eml fixtures."""

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

    def init_root(self, tmp: str) -> Path:
        root = Path(tmp) / "mail-data"
        self.run_script("init.py", data_dir=root)
        return root

    def stage(self, root: Path, fixture_dir: Path, uid: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.run_script(
            "stage.py", "--account", "fixture", "--uid", uid, "--fixture-dir", str(fixture_dir), data_dir=root, check=check
        )

    # ---- list ----

    def test_list_outputs_summaries_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            payload = json.loads(self.run_script("list_messages.py", "--fixture-dir", str(FIXTURES), data_dir=root).stdout)
            self.assertEqual(1, payload["count"])
            summary = payload["messages"][0]
            self.assertEqual("invoice", summary["imap_uid"])
            self.assertEqual("Invoice INV-001", summary["subject"])
            self.assertEqual(["billing@example.com"], summary["from"])
            self.assertIn("attached invoice INV-001", summary["snippet"])
            self.assertEqual(["invoice.pdf"], summary["attachments"])
            self.assertFalse(summary["processed_before"])
            self.assertEqual("", (root / "events" / "all.jsonl").read_text())

    def test_list_since_filters_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            kept = json.loads(self.run_script("list_messages.py", "--fixture-dir", str(FIXTURES), "--since", "2026-06-01", data_dir=root).stdout)
            self.assertEqual(1, kept["count"])
            filtered = json.loads(self.run_script("list_messages.py", "--fixture-dir", str(FIXTURES), "--since", "2026-06-07", data_dir=root).stdout)
            self.assertEqual(0, filtered["count"])

    def test_list_reports_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            fixture_dir = Path(tmp) / "many"
            fixture_dir.mkdir()
            source = (FIXTURES / "invoice.eml").read_text()
            (fixture_dir / "a.eml").write_text(source)
            (fixture_dir / "b.eml").write_text(source.replace("invoice-001@example.com", "invoice-002@example.com"))
            payload = json.loads(
                self.run_script("list_messages.py", "--fixture-dir", str(fixture_dir), "--limit", "1", data_dir=root).stdout
            )
            self.assertEqual(1, payload["count"])
            self.assertEqual(2, payload["total_matched"])
            self.assertTrue(payload["truncated"])

    def test_submit_passes_currency_through(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            staged = json.loads(self.stage(root, FIXTURES, "invoice").stdout)
            fields = {**FIELDS, "currency": "USD"}
            self.run_script("submit.py", "--id", staged["pending_id"], "--fields", json.dumps(fields), data_dir=root)
            event = json.loads((root / "events" / "all.jsonl").read_text().splitlines()[-1])
            self.assertEqual("USD", event["extracted"]["invoice"]["currency"])

    def test_list_annotates_processed_after_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            self.stage(root, FIXTURES, "invoice")
            payload = json.loads(self.run_script("list_messages.py", "--fixture-dir", str(FIXTURES), data_dir=root).stdout)
            self.assertTrue(payload["messages"][0]["processed_before"])

    # ---- show ----

    def test_show_returns_body_and_attachments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            payload = json.loads(
                self.run_script("show.py", "--account", "fixture", "--uid", "invoice", "--fixture-dir", str(FIXTURES), data_dir=root).stdout
            )
            self.assertIn("attached invoice INV-001", payload["body"])
            self.assertEqual("invoice.pdf", payload["attachments"][0]["filename"])

    # ---- stage ----

    def test_stage_saves_pdf_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            payload = json.loads(self.stage(root, FIXTURES, "invoice").stdout)
            staged = Path(payload["files"][0])
            self.assertTrue(staged.exists())
            self.assertTrue((root / "state" / "pending" / f"{payload['pending_id']}.json").exists())
            event = json.loads((root / "events" / "all.jsonl").read_text().splitlines()[0])
            self.assertEqual("pending_extraction", event["status"])
            conn = sqlite3.connect(root / "state" / "processed.sqlite")
            self.assertEqual(1, conn.execute("select count(*) from processed_messages").fetchone()[0])
            conn.close()

    def test_stage_rejects_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            self.stage(root, FIXTURES, "invoice")
            result = self.stage(root, FIXTURES, "invoice", check=False)
            self.assertEqual(1, result.returncode)
            self.assertIn("already staged or processed", result.stderr)

    def test_stage_expands_zip_members(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            payload = json.loads(self.stage(root, FIXTURES / "zip", "zip-invoice").stdout)
            staged = Path(payload["files"][0])
            self.assertTrue(staged.read_bytes().startswith(b"%PDF-"))
            manifest = json.loads((root / "state" / "pending" / f"{payload['pending_id']}.json").read_text())
            self.assertEqual("zip", manifest["attachments"][0]["origin"])
            self.assertEqual("invoice.zip", manifest["attachments"][0]["source_zip"])

    def test_stage_fails_without_pdf_or_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            result = self.stage(root, FIXTURES / "spam", "spam", check=False)
            self.assertEqual(1, result.returncode)
            self.assertIn("no pdf/zip attachment", result.stderr)

    def test_stage_failure_lists_unallowlisted_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            fixture_dir = Path(tmp) / "unknown-provider"
            fixture_dir.mkdir()
            (fixture_dir / "unknown.eml").write_text(
                "From: bill@unknown-corp.example.com\n"
                "To: me@example.com\n"
                "Subject: 电子发票下载通知\n"
                "Date: Sat, 06 Jun 2026 22:20:00 +0800\n"
                "Message-ID: <unknown-001@example.com>\n"
                "MIME-Version: 1.0\n"
                'Content-Type: text/plain; charset="utf-8"\n'
                "\n"
                "请点击 https://invoice.unknown-corp.example.com/dl/1.pdf 下载发票。\n",
                encoding="utf-8",
            )
            result = self.stage(root, fixture_dir, "unknown", check=False)
            self.assertEqual(1, result.returncode)
            self.assertIn("candidate link hosts (not allowlisted)", result.stderr)
            self.assertIn("invoice.unknown-corp.example.com", result.stderr)

    def test_stage_sanitizes_account_path_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            self.run_script(
                "stage.py", "--account", "../../outside", "--uid", "invoice", "--fixture-dir", str(FIXTURES), data_dir=root
            )
            saved = list((root / "files").rglob("*.pdf"))
            self.assertEqual(1, len(saved))
            self.assertTrue(saved[0].resolve().is_relative_to(root.resolve()))

    def test_stage_rejects_jsonl_output_outside_data_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            processors = root / "config" / "processors.yaml"
            processors.write_text(processors.read_text().replace("events/invoices.jsonl", "../outside.jsonl"), encoding="utf-8")
            result = self.stage(root, FIXTURES, "invoice", check=False)
            self.assertEqual(1, result.returncode)
            self.assertIn("path escapes data dir", result.stderr)
            self.assertFalse((root.parent / "outside.jsonl").exists())

    # ---- submit ----

    def test_submit_finalizes_with_rename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            staged = json.loads(self.stage(root, FIXTURES, "invoice").stdout)
            result = self.run_script("submit.py", "--id", staged["pending_id"], "--fields", json.dumps(FIELDS), data_dir=root)
            final = Path(json.loads(result.stdout)["files"][0])
            self.assertEqual("2026-06-04_26427000000465806619_测试电信公司.pdf", final.name)
            self.assertTrue(final.exists())
            self.assertFalse((root / "state" / "pending" / f"{staged['pending_id']}.json").exists())
            statuses = [json.loads(line)["status"] for line in (root / "events" / "all.jsonl").read_text().splitlines() if line]
            self.assertEqual(["pending_extraction", "processed"], statuses)

    def test_submit_rejects_invalid_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            staged = json.loads(self.stage(root, FIXTURES, "invoice").stdout)
            bad = {**FIELDS, "invoice_date": "not-a-date"}
            result = self.run_script("submit.py", "--id", staged["pending_id"], "--fields", json.dumps(bad), data_dir=root, check=False)
            self.assertEqual(1, result.returncode)
            self.assertIn("malformed invoice field", result.stderr)

    def test_submit_rejects_provider_metadata_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            staged = json.loads(self.stage(root, FIXTURES, "invoice").stdout)
            manifest_path = root / "state" / "pending" / f"{staged['pending_id']}.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["provider_meta"] = {"invoice_number": "DIFFERENT", "amount": 1.0}
            manifest_path.write_text(json.dumps(manifest))
            result = self.run_script("submit.py", "--id", staged["pending_id"], "--fields", json.dumps(FIELDS), data_dir=root, check=False)
            self.assertEqual(1, result.returncode)
            self.assertEqual(2, len(json.loads(result.stderr)["mismatches"]))
            self.assertTrue(manifest_path.exists())

    def test_duplicate_invoice_number_rejected_then_discardable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            first = json.loads(self.stage(root, FIXTURES, "invoice").stdout)
            second = json.loads(self.stage(root, FIXTURES / "zip", "zip-invoice").stdout)
            self.run_script("submit.py", "--id", first["pending_id"], "--fields", json.dumps(FIELDS), data_dir=root)

            dup = self.run_script("submit.py", "--id", second["pending_id"], "--fields", json.dumps(FIELDS), data_dir=root, check=False)
            self.assertEqual(1, dup.returncode)
            self.assertIn("already processed", dup.stderr)

            discard = self.run_script(
                "submit.py", "--id", second["pending_id"], "--discard", "--reason", "duplicate delivery", data_dir=root
            )
            self.assertEqual("ok", json.loads(discard.stdout)["status"])
            self.assertFalse(Path(second["files"][0]).exists())
            statuses = [json.loads(line)["status"] for line in (root / "events" / "all.jsonl").read_text().splitlines() if line]
            self.assertIn("discarded", statuses)

    def test_submit_does_not_overwrite_different_file_with_same_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            processors = root / "config" / "processors.yaml"
            processors.write_text(
                processors.read_text().replace(
                    'rename_template: "{invoice_date}_{invoice_number}_{seller}"',
                    'rename_template: "{invoice_date}_{seller}"',
                ),
                encoding="utf-8",
            )
            first = json.loads(self.stage(root, FIXTURES, "invoice").stdout)
            second = json.loads(self.stage(root, FIXTURES / "zip", "zip-invoice").stdout)
            self.run_script("submit.py", "--id", first["pending_id"], "--fields", json.dumps(FIELDS), data_dir=root)
            other = {**FIELDS, "invoice_number": "99999999999999999999"}
            result = self.run_script("submit.py", "--id", second["pending_id"], "--fields", json.dumps(other), data_dir=root)
            final = Path(json.loads(result.stdout)["files"][0])
            clean = final.parent / "2026-06-04_测试电信公司.pdf"
            self.assertTrue(clean.exists())
            self.assertNotEqual(clean, final)
            self.assertTrue(final.exists())

    def test_invoice_file_selects_clean_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            staged = json.loads(self.stage(root, FIXTURES / "multi", "multi-invoice").stdout)
            self.assertEqual(2, len(staged["files"]))
            result = self.run_script(
                "submit.py",
                "--id", staged["pending_id"],
                "--fields", json.dumps(FIELDS),
                "--invoice-file", "real-invoice.pdf",
                data_dir=root,
            )
            event = json.loads((root / "events" / "all.jsonl").read_text().splitlines()[-1])
            by_name = {record["original_filename"]: record for record in event["attachments"]}
            self.assertTrue(by_name["real-invoice.pdf"]["saved_path"].endswith("2026-06-04_26427000000465806619_测试电信公司.pdf"))

    # ---- mailbox ----

    def test_mailbox_rejects_unknown_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.init_root(tmp)
            result = self.run_script("mailbox.py", "mark-read", "--account", "nope", "--uid", "1", data_dir=root, check=False)
            self.assertEqual(1, result.returncode)
            self.assertIn("unknown account", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
