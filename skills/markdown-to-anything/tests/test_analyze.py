#!/usr/bin/env python3
"""Unit tests for markdown-to-anything analyze.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze  # type: ignore  # noqa: E402


class AnalyzeMarkdownTextTest(unittest.TestCase):
    """Test markdown analysis and auto routing."""

    def test_empty_document_defaults_to_card(self) -> None:
        result = analyze.analyze_markdown_text("")
        self.assertEqual(result.mode_auto, "card")
        self.assertEqual(result.template_auto, "hero-summary")
        self.assertEqual(result.stats.section_count, 0)
        self.assertEqual(result.stats.nonempty_line_count, 0)

    def test_normal_short_markdown_chooses_card(self) -> None:
        md = """# 日报\n\n## 总览\n- 要点1\n- 要点2\n\n## 风险\n- 注意回撤\n"""
        result = analyze.analyze_markdown_text(md)
        self.assertEqual(result.mode_auto, "card")
        self.assertFalse(result.stats.has_complex_table)
        self.assertFalse(result.stats.has_complex_code)
        self.assertEqual(result.stats.section_count, 3)

    def test_complex_table_forces_report(self) -> None:
        md = "\n".join(
            [
                "# 表格报告",
                "",
                "| c1 | c2 | c3 | c4 | c5 |",
                "| --- | --- | --- | --- | --- |",
                "| 1 | 2 | 3 | 4 | 5 |",
            ]
        )
        result = analyze.analyze_markdown_text(md)
        self.assertEqual(result.mode_auto, "report")
        self.assertTrue(result.stats.has_complex_table)
        self.assertEqual(result.stats.max_table_cols, 5)

    def test_complex_table_too_many_rows_forces_report(self) -> None:
        rows = ["| a | b |", "| --- | --- |"] + [f"| {i} | {i} |" for i in range(11)]
        md = "# 多行表格\n\n" + "\n".join(rows)
        result = analyze.analyze_markdown_text(md)
        self.assertEqual(result.mode_auto, "report")
        self.assertTrue(result.stats.has_complex_table)
        self.assertGreater(result.stats.max_table_rows, 10)

    def test_multiple_code_blocks_forces_report(self) -> None:
        md = """# 代码\n\n```py\nprint(1)\n```\n\n```py\nprint(2)\n```\n"""
        result = analyze.analyze_markdown_text(md)
        self.assertEqual(result.mode_auto, "report")
        self.assertTrue(result.stats.has_complex_code)
        self.assertEqual(result.stats.code_block_count, 2)

    def test_long_code_block_forces_report(self) -> None:
        code_lines = "\n".join([f"line {i}" for i in range(21)])
        md = f"# 代码\n\n```\n{code_lines}\n```\n"
        result = analyze.analyze_markdown_text(md)
        self.assertEqual(result.mode_auto, "report")
        self.assertTrue(result.stats.has_complex_code)
        self.assertEqual(result.stats.max_code_block_lines, 21)

    def test_section_count_over_threshold_forces_report(self) -> None:
        md = "\n".join([f"## S{i}" for i in range(7)])
        result = analyze.analyze_markdown_text(md)
        self.assertEqual(result.mode_auto, "report")
        self.assertEqual(result.stats.section_count, 7)

    def test_metrics_grid_template_for_small_table(self) -> None:
        md = """# 指标\n\n| 指标 | 数值 |\n| --- | --- |\n| A | 1 |\n| B | 2 |\n"""
        result = analyze.analyze_markdown_text(md)
        self.assertEqual(result.template_auto, "metrics-grid")


if __name__ == "__main__":
    unittest.main()
