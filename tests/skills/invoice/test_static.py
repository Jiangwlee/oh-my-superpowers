"""T1 static and functional checks for the invoice skill."""

from __future__ import annotations

import json
import os
import py_compile
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = ROOT / "skills" / "invoice"
SCRIPT = SKILL_ROOT / "scripts" / "invoice.py"
CLI_MAIN = ROOT / "cli" / "invoice" / "main.py"


class TestInvoiceStatic(unittest.TestCase):
    """Validate the skill skeleton."""

    def test_skill_md_exists_and_name_matches_directory(self) -> None:
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: invoice", content)
        self.assertIn("omp invoice scan", content)
        self.assertIn("omp invoice discard", content)

    def test_required_references_exist(self) -> None:
        for name in ["config.md", "registry.md", "cli.md"]:
            self.assertTrue((SKILL_ROOT / "references" / name).exists(), name)

    def test_scripts_compile(self) -> None:
        for script in [SCRIPT, CLI_MAIN]:
            with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as tmp:
                py_compile.compile(str(script), cfile=tmp.name, doraise=True)

    def test_skill_md_uses_omp_commands_not_relative_script_calls(self) -> None:
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("omp invoice", content)
        for pattern in ["bash scripts/", "python scripts/", "python3 scripts/", "./scripts/"]:
            self.assertNotIn(pattern, content)

    def test_script_does_not_parse_pdf_content(self) -> None:
        content = SCRIPT.read_text(encoding="utf-8").lower()
        forbidden = ["pdfplumber", "pypdf", "pdftotext", "pymupdf", "fitz", "ocr", "invoice_number_re"]
        for token in forbidden:
            self.assertNotIn(token, content)


class TestInvoiceWorkflow(unittest.TestCase):
    """Exercise the minimal invoice registry workflow."""

    def run_invoice(self, data_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["INVOICE_DATA_DIR"] = str(data_dir)
        return subprocess.run(
            ["uv", "run", str(SCRIPT), *args],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    def test_scan_submit_list_archive_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = base / "invoice-data"
            source_dir = base / "source"
            source_dir.mkdir()
            invoice_file = source_dir / "invoice.pdf"
            invoice_file.write_bytes(b"%PDF-1.4\nfake invoice\n")
            image_file = source_dir / "invoice.png"
            image_file.write_bytes(b"not an invoice pdf\n")

            self.run_invoice(data_dir, "init")
            self.run_invoice(data_dir, "init", "--dry-run")

            sources = data_dir / "config" / "sources.yaml"
            sources.write_text(
                f"""sources:
  test_source:
    kind: local_dir
    path: {source_dir}
    owner: Test Owner
""",
                encoding="utf-8",
            )

            scan = self.run_invoice(data_dir, "scan")
            self.assertIn('"imported": 1', scan.stdout)

            pending = self.run_invoice(data_dir, "pending")
            pending_row = json.loads(pending.stdout.splitlines()[0])
            self.assertEqual(pending_row["owner"], "Test Owner")
            self.assertEqual(pending_row["source_id"], "test_source")

            fields = {
                "invoice_number": "INV-001",
                "invoice_date": "2026-06-01",
                "amount": 100.0,
                "seller": "Seller Co",
            }
            submit = self.run_invoice(
                data_dir,
                "submit",
                "--id",
                pending_row["id"],
                "--purpose",
                "claim",
                "--fields",
                json.dumps(fields),
            )
            self.assertIn('"status": "submitted"', submit.stdout)

            listed = self.run_invoice(data_dir, "list")
            self.assertIn('"invoice_number": "INV-001"', listed.stdout)
            self.assertIn('"status": "available"', listed.stdout)

            used = self.run_invoice(data_dir, "mark-used", "--invoice-number", "INV-001", "--reason", "test")
            self.assertIn('"status": "used"', used.stdout)

            available = self.run_invoice(data_dir, "list")
            self.assertIn("no invoices", available.stdout)

            all_rows = self.run_invoice(data_dir, "list", "--status", "all")
            self.assertIn('"status": "used"', all_rows.stdout)

            archived = self.run_invoice(data_dir, "archive", "--invoice-number", "INV-001", "--reason", "done")
            self.assertIn('"status": "archived"', archived.stdout)

            hidden = self.run_invoice(data_dir, "list", "--status", "all")
            self.assertIn("no invoices", hidden.stdout)

            visible = self.run_invoice(data_dir, "list", "--status", "all", "--include-archived")
            self.assertIn('"status": "archived"', visible.stdout)

    def test_discard_removes_pending_copy_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            data_dir = base / "invoice-data"
            source_dir = base / "source"
            source_dir.mkdir()
            invoice_file = source_dir / "invoice.pdf"
            invoice_file.write_bytes(b"%PDF-1.4\nfake invoice\n")

            self.run_invoice(data_dir, "init")
            (data_dir / "config" / "sources.yaml").write_text(
                f"""sources:
  test_source:
    kind: local_dir
    path: {source_dir}
    owner: Test Owner
""",
                encoding="utf-8",
            )
            self.run_invoice(data_dir, "scan")
            pending = self.run_invoice(data_dir, "pending")
            pending_row = json.loads(pending.stdout.splitlines()[0])
            pending_copy = Path(pending_row["imported_path"])
            self.assertTrue(pending_copy.exists())

            discarded = self.run_invoice(data_dir, "discard", "--id", pending_row["id"], "--reason", "duplicate")
            self.assertIn('"status": "discarded"', discarded.stdout)
            self.assertFalse(pending_copy.exists())
            self.assertTrue(invoice_file.exists())
            self.assertIn("no pending invoices", self.run_invoice(data_dir, "pending").stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
