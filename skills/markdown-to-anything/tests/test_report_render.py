#!/usr/bin/env python3
"""Unit tests for markdown-to-anything report_render.py."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import report_render  # type: ignore  # noqa: E402


class ReportRenderPngTest(unittest.TestCase):
    """Test report PNG rendering helpers."""

    def test_light_theme_exists(self) -> None:
        self.assertIn("light", report_render.THEMES)

    def test_build_css_has_print_contrast_fallback(self) -> None:
        css = report_render._build_css("dark", "medium")
        self.assertIn("@media print", css)
        self.assertIn("background: #ffffff !important", css)
        self.assertIn("color: #111827 !important", css)
        self.assertIn("font-family:", css)

    def test_render_markdown_to_html_can_disable_remote_fonts_for_pdf_stability(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "input.md"
            out_html = Path(tmpdir) / "out.html"
            md_path.write_text("# 标题\n\n正文", encoding="utf-8")

            engine, warnings = report_render.render_markdown_to_html(
                md_path,
                out_html,
                theme="blue",
                font_size="medium",
                prefer_engine="fallback",
                include_remote_fonts=False,
            )

            html_text = out_html.read_text(encoding="utf-8")
            self.assertEqual(engine, "fallback")
            self.assertEqual(warnings, [])
            self.assertNotIn("fonts.googleapis.com", html_text)
            self.assertNotIn("fonts.gstatic.com", html_text)

    def test_render_markdown_to_pdf_uses_legacy_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "input.md"
            md_path.write_text("# 报告\n\n正文", encoding="utf-8")
            out_pdf = Path(tmpdir) / "out.pdf"
            tmp_html = Path(tmpdir) / "tmp_report.html"

            fake_proc = SimpleNamespace(returncode=0, stderr="")

            with mock.patch.object(report_render.tempfile, "NamedTemporaryFile") as named_tmp:
                named_tmp.return_value.__enter__.return_value.name = str(tmp_html)
                named_tmp.return_value.__exit__.return_value = None
                with mock.patch.object(report_render, "report_markdown_to_html", return_value=("<html/>", "pandoc")) as html_render:
                    with mock.patch.object(report_render.shutil, "which", return_value="/usr/bin/node"):
                        with mock.patch.object(report_render.subprocess, "run", return_value=fake_proc) as sub_run:
                            result = report_render.render_markdown_to_pdf(
                                md_path,
                                out_pdf,
                                theme="blue",
                                font_size="medium",
                                prefer_engine="auto",
                            )

            self.assertEqual(result.markdown_engine, "pandoc")
            self.assertTrue(any("report html renderer" in w for w in result.warnings))
            html_render.assert_called_once()
            cmd = sub_run.call_args.args[0]
            self.assertEqual(cmd[2], "--pdf")

    def test_render_markdown_to_png_uses_report_screenshot_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "input.md"
            md_path.write_text("# 报告\n\n正文", encoding="utf-8")
            out_png = Path(tmpdir) / "report.png"
            tmp_html = Path(tmpdir) / "tmp_report.html"

            fake_proc = SimpleNamespace(returncode=0, stderr="")

            with mock.patch.object(report_render.tempfile, "NamedTemporaryFile") as named_tmp:
                named_tmp.return_value.__enter__.return_value.name = str(tmp_html)
                named_tmp.return_value.__exit__.return_value = None
                with mock.patch.object(report_render, "report_markdown_to_html", return_value=("<html/>", "marked")) as html_render:
                    with mock.patch.object(report_render.shutil, "which", return_value="/usr/bin/node"):
                        with mock.patch.object(report_render.subprocess, "run", return_value=fake_proc) as sub_run:
                            result = report_render.render_markdown_to_png(
                                md_path,
                                out_png,
                                theme="light",
                                font_size="medium",
                                prefer_engine="auto",
                            )

            self.assertEqual(result.markdown_engine, "marked")
            self.assertTrue(any("report html renderer" in w for w in result.warnings))
            html_render.assert_called_once()
            cmd = sub_run.call_args.args[0]
            self.assertEqual(cmd[2], "--png")
            self.assertEqual(cmd[-3:], ["3", "750", "0"])


if __name__ == "__main__":
    unittest.main()
