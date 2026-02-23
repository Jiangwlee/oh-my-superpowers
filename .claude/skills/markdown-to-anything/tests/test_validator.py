#!/usr/bin/env python3
"""Unit tests for markdown-to-anything validator.py."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validator  # type: ignore  # noqa: E402


SVG_HEADER = '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">'
SVG_FOOTER = '</svg>'


class ValidateSvgFileTest(unittest.TestCase):
    """Test approximate SVG validation rules."""

    def _validate(self, body: str) -> validator.ValidationResult:
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
            path = Path(tmp.name)
        try:
            path.write_text(SVG_HEADER + body + SVG_FOOTER, encoding="utf-8")
            return validator.validate_svg_file(path)
        finally:
            path.unlink(missing_ok=True)

    def test_valid_layout_passes(self) -> None:
        body = (
            '<rect x="0" y="0" width="1080" height="1920" fill="#000" />'
            '<text id="t1" x="50" y="100" font-size="40">标题</text>'
            '<text id="t2" x="50" y="200" font-size="40">正文</text>'
        )
        result = self._validate(body)
        self.assertTrue(result.ok)
        self.assertEqual(result.errors, [])

    def test_out_of_bounds_text_fails(self) -> None:
        body = '<text id="t1" x="1040" y="100" font-size="60">超界文本</text>'
        result = self._validate(body)
        self.assertFalse(result.ok)
        self.assertTrue(any(issue.code == "out_of_bounds" for issue in result.errors))

    def test_text_overlap_fails(self) -> None:
        body = (
            '<text id="t1" x="50" y="100" font-size="60">AAAAAAAAAA</text>'
            '<text id="t2" x="60" y="105" font-size="60">BBBBBBBBBB</text>'
        )
        result = self._validate(body)
        self.assertFalse(result.ok)
        self.assertTrue(any(issue.code == "overlap" for issue in result.errors))

    def test_rect_overlap_is_ignored_for_collision_rule(self) -> None:
        body = (
            '<rect x="0" y="0" width="1080" height="1920" fill="#000" />'
            '<rect x="20" y="20" width="1000" height="1800" fill="#111" />'
        )
        result = self._validate(body)
        self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
