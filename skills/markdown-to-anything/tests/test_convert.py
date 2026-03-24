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
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import convert  # type: ignore  # noqa: E402
from inspect_input import InspectResult  # type: ignore  # noqa: E402
from normalize_input import NormalizeResult  # type: ignore  # noqa: E402


class ConvertCliTest(unittest.TestCase):
    """Test convert.py routing behavior."""

    def _run_main(self, argv: list[str]) -> dict[str, object]:
        stdout = io.StringIO()
        with mock.patch.object(sys, "argv", argv):
            with contextlib.redirect_stdout(stdout):
                convert.main()
        return json.loads(stdout.getvalue().strip())

    def test_auto_mode_without_format_defaults_to_report_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "input.md"
            md_path.write_text("# 短摘要\n\n正文", encoding="utf-8")
            out_base = Path(tmpdir) / "out"
            inspect_result = InspectResult(True, "markdown", "clean", {"has_heading": True}, "render_direct", [], [])

            with mock.patch.object(convert, "_check_dependencies", return_value=[]), \
                 mock.patch.object(convert, "_resolve_output_base", return_value=out_base), \
                 mock.patch.object(convert, "inspect_markdown_file", return_value=inspect_result), \
                 mock.patch.object(convert, "_render_report", return_value=([str(out_base.with_name("out_report").with_suffix(".pdf"))], [], {"markdown_to_html": "pandoc", "html_to_pdf": "chromium", "html_to_png": "n/a"}, [])) as render_report:
                manifest = self._run_main([
                    "convert.py",
                    str(md_path),
                    "--stdout-manifest",
                ])

            self.assertTrue(manifest["ok"])
            self.assertEqual(manifest["mode"], "report")
            self.assertEqual(manifest["format"], "pdf")
            self.assertIn(str(out_base.with_name("out_report").with_suffix(".pdf")), manifest["files"])
            render_report.assert_called_once()

    def test_light_dirty_input_triggers_normalize(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = Path(tmpdir) / "input.md"
            md_path.write_text("前言\n```markdown\n# 标题\n```", encoding="utf-8")
            out_base = Path(tmpdir) / "out"
            clean_path = out_base.parent / "out.clean.md"
            inspect_result = InspectResult(True, "markdown", "light_dirty", {"has_fenced_markdown": True}, "normalize_then_render", [], [])
            normalize_result = NormalizeResult(True, str(md_path), str(clean_path), True, "# 标题\n", {"fenced_markdown": True}, ["extracted_fenced_markdown"], [], [])

            with mock.patch.object(convert, "_check_dependencies", return_value=[]), \
                 mock.patch.object(convert, "_resolve_output_base", return_value=out_base), \
                 mock.patch.object(convert, "inspect_markdown_file", return_value=inspect_result), \
                 mock.patch.object(convert, "normalize_markdown_file", return_value=normalize_result) as normalize, \
                 mock.patch.object(convert, "_render_report", return_value=([str(out_base.with_name("out_report").with_suffix(".pdf"))], [], {"markdown_to_html": "pandoc", "html_to_pdf": "chromium", "html_to_png": "n/a"}, [])):
                manifest = self._run_main([
                    "convert.py",
                    str(md_path),
                    "--stdout-manifest",
                    "--keep-clean",
                ])

            self.assertTrue(manifest["normalization"]["performed"])
            self.assertEqual(manifest["normalization"]["clean_file"], str(clean_path))
            normalize.assert_called_once()

    def test_resolve_pdf_backend_auto_maps_to_html(self) -> None:
        self.assertEqual(convert._resolve_pdf_backend("auto"), "html")
        self.assertEqual(convert._resolve_pdf_backend("html"), "html")


if __name__ == "__main__":
    unittest.main()
