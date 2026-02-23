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
                with mock.patch.object(report_render, "render_markdown_to_html", return_value=("marked", ["html warn"])) as render_html:
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
            self.assertIn("html warn", result.warnings)
            render_html.assert_called_once()
            cmd = sub_run.call_args.args[0]
            self.assertEqual(cmd[2], "--png")
            self.assertEqual(cmd[-3:], ["3", "750", "0"])


if __name__ == "__main__":
    unittest.main()
