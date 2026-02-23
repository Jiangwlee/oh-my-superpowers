#!/usr/bin/env python3
"""Unit tests for markdown-to-anything convert.py."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import convert  # type: ignore  # noqa: E402


class ConvertCliTest(unittest.TestCase):
    """Test convert.py routing behavior."""

    def _run_main(self, argv: list[str]) -> dict[str, object]:
        stdout = io.StringIO()
        with mock.patch.object(sys, "argv", argv):
            with contextlib.redirect_stdout(stdout):
                convert.main()
        return json.loads(stdout.getvalue().strip())

    def test_report_png_stays_report_and_uses_report_png_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "input.md"
            md_path.write_text("# 报告\n\n正文", encoding="utf-8")
            out_base = Path(tmpdir) / "out"

            report_png_result = SimpleNamespace(markdown_engine="marked", warnings=["png warn"])
            with mock.patch.object(convert, "_default_output_base", return_value=out_base):
                with mock.patch.object(convert, "render_markdown_to_png", return_value=report_png_result) as render_png:
                    with mock.patch.object(convert, "render_markdown_to_pdf") as render_pdf:
                        manifest = self._run_main(
                            [
                                "convert.py",
                                str(md_path),
                                "--mode",
                                "report",
                                "--format",
                                "png",
                                "--stdout-manifest",
                            ]
                        )

            self.assertEqual(manifest["mode"], "report")
            self.assertEqual(manifest["format"], "png")
            self.assertIn(str(out_base.with_name("out_report").with_suffix(".png")), manifest["files"])
            render_png.assert_called_once()
            render_pdf.assert_not_called()

    def test_auto_mode_without_format_defaults_to_report_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "input.md"
            md_path.write_text("# 短摘要", encoding="utf-8")
            out_base = Path(tmpdir) / "out"

            report_pdf_result = SimpleNamespace(markdown_engine="fallback", warnings=[])
            with mock.patch.object(convert, "_default_output_base", return_value=out_base):
                with mock.patch.object(convert, "render_markdown_to_pdf", return_value=report_pdf_result) as render_pdf:
                    manifest = self._run_main(
                        [
                            "convert.py",
                            str(md_path),
                            "--stdout-manifest",
                            "--pdf-backend",
                            "html",
                        ]
                    )

            self.assertEqual(manifest["mode"], "report")
            self.assertEqual(manifest["format"], "pdf")
            self.assertIn(str(out_base.with_name("out_report").with_suffix(".pdf")), manifest["files"])
            render_pdf.assert_called_once()

    def test_resolve_pdf_backend_auto_prefers_typst_when_installed(self) -> None:
        self.assertEqual(convert._resolve_pdf_backend("auto"), "html")
        self.assertEqual(convert._resolve_pdf_backend("html"), "html")


if __name__ == "__main__":
    unittest.main()
