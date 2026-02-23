#!/usr/bin/env python3
"""Analyze Markdown structure and choose rendering mode/template."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


_TEMPLATE_CHOICES = (
    "hero-summary",
    "headline-list",
    "metrics-grid",
    "quote-and-bullets",
)


@dataclass(slots=True)
class MarkdownStats:
    """Markdown structural statistics for routing decisions.

    Attributes:
        section_count: Number of headings (`#` to `###`).
        heading_lines: Heading texts in source order.
        bullet_count: Count of bullet list items.
        code_block_count: Number of fenced code blocks.
        max_code_block_lines: Longest fenced code block line count.
        table_count: Number of Markdown table blocks.
        max_table_rows: Maximum row count among tables.
        max_table_cols: Maximum column count among tables.
        has_complex_table: True when any table exceeds configured threshold.
        has_complex_code: True when code blocks exceed configured threshold.
        line_count: Total lines in the file.
        nonempty_line_count: Non-empty line count.
    """

    section_count: int
    heading_lines: list[str]
    bullet_count: int
    code_block_count: int
    max_code_block_lines: int
    table_count: int
    max_table_rows: int
    max_table_cols: int
    has_complex_table: bool
    has_complex_code: bool
    line_count: int
    nonempty_line_count: int


@dataclass(slots=True)
class AnalysisResult:
    """Analysis output consumed by converters."""

    mode_auto: str
    template_auto: str
    stats: MarkdownStats


@dataclass(slots=True)
class AnalyzeConfig:
    """Thresholds for `auto` routing and template selection."""

    complex_table_max_cols: int = 4
    complex_table_max_rows: int = 10
    complex_code_max_blocks: int = 1
    complex_code_max_lines: int = 20
    card_max_sections: int = 6


def _count_leading_hashes(text: str) -> int:
    count = 0
    for ch in text:
        if ch == "#":
            count += 1
        else:
            break
    return count


def _split_table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped:
        return []
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [part.strip() for part in stripped.split("|")]


def _is_table_separator_line(line: str) -> bool:
    cells = _split_table_cells(line)
    if not cells:
        return False
    for cell in cells:
        if not cell:
            return False
        for ch in cell:
            if ch not in {"-", ":", " "}:
                return False
    return True


def analyze_markdown_text(text: str, config: AnalyzeConfig | None = None) -> AnalysisResult:
    """Analyze Markdown text.

    Args:
        text: Markdown source.
        config: Optional thresholds.

    Returns:
        Analysis result with stats and auto mode/template.
    """
    cfg = config or AnalyzeConfig()
    lines = text.splitlines()

    heading_lines: list[str] = []
    bullet_count = 0
    code_block_count = 0
    max_code_block_lines = 0
    in_code = False
    current_code_lines = 0

    table_count = 0
    max_table_rows = 0
    max_table_cols = 0
    table_rows_in_block = 0
    table_cols_in_block = 0
    table_active = False
    table_seen_header = False

    for idx, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                in_code = False
                if current_code_lines > max_code_block_lines:
                    max_code_block_lines = current_code_lines
                current_code_lines = 0
            else:
                in_code = True
                code_block_count += 1
            if table_active:
                max_table_rows = max(max_table_rows, table_rows_in_block)
                max_table_cols = max(max_table_cols, table_cols_in_block)
                table_active = False
                table_seen_header = False
                table_rows_in_block = 0
                table_cols_in_block = 0
            continue

        if in_code:
            current_code_lines += 1
            continue

        if stripped.startswith("#"):
            hashes = _count_leading_hashes(stripped)
            if 1 <= hashes <= 3 and len(stripped) > hashes and stripped[hashes] == " ":
                heading_lines.append(stripped[hashes + 1 :].strip())

        if stripped.startswith("- ") or stripped.startswith("* "):
            bullet_count += 1

        # Simple Markdown table detection: header row + separator row + subsequent rows.
        if "|" in line:
            cells = _split_table_cells(line)
            looks_like_row = len(cells) >= 2
        else:
            cells = []
            looks_like_row = False

        if not table_active:
            if looks_like_row and idx + 1 < len(lines) and _is_table_separator_line(lines[idx + 1]):
                table_active = True
                table_seen_header = True
                table_count += 1
                table_rows_in_block = 1
                table_cols_in_block = len(cells)
            continue

        if table_active:
            if table_seen_header and _is_table_separator_line(line):
                table_rows_in_block += 1
                continue
            if looks_like_row:
                table_rows_in_block += 1
                table_cols_in_block = max(table_cols_in_block, len(cells))
            else:
                max_table_rows = max(max_table_rows, table_rows_in_block)
                max_table_cols = max(max_table_cols, table_cols_in_block)
                table_active = False
                table_seen_header = False
                table_rows_in_block = 0
                table_cols_in_block = 0

    if in_code and current_code_lines > max_code_block_lines:
        max_code_block_lines = current_code_lines
    if table_active:
        max_table_rows = max(max_table_rows, table_rows_in_block)
        max_table_cols = max(max_table_cols, table_cols_in_block)

    stats = MarkdownStats(
        section_count=len(heading_lines),
        heading_lines=heading_lines,
        bullet_count=bullet_count,
        code_block_count=code_block_count,
        max_code_block_lines=max_code_block_lines,
        table_count=table_count,
        max_table_rows=max_table_rows,
        max_table_cols=max_table_cols,
        has_complex_table=(max_table_cols > cfg.complex_table_max_cols or max_table_rows > cfg.complex_table_max_rows),
        has_complex_code=(code_block_count > cfg.complex_code_max_blocks or max_code_block_lines > cfg.complex_code_max_lines),
        line_count=len(lines),
        nonempty_line_count=sum(1 for line in lines if line.strip()),
    )

    mode_auto = choose_mode_auto(stats, cfg)
    template_auto = choose_template_auto(stats)
    return AnalysisResult(mode_auto=mode_auto, template_auto=template_auto, stats=stats)


def choose_mode_auto(stats: MarkdownStats, config: AnalyzeConfig | None = None) -> str:
    """Choose mode for `--mode auto`."""
    cfg = config or AnalyzeConfig()
    if stats.has_complex_table or stats.has_complex_code:
        return "report"
    if stats.section_count > cfg.card_max_sections:
        return "report"
    return "card"


def choose_template_auto(stats: MarkdownStats) -> str:
    """Choose a card template using simple heuristics."""
    if stats.table_count > 0 and stats.max_table_cols >= 2 and stats.max_table_rows <= 6:
        return "metrics-grid"
    if 2 <= stats.section_count <= 4 and stats.bullet_count >= 6:
        return "headline-list"
    if stats.section_count <= 1 and stats.bullet_count >= 2:
        return "quote-and-bullets"
    return "hero-summary"


def analyze_markdown_file(path: Path, config: AnalyzeConfig | None = None) -> AnalysisResult:
    """Analyze a Markdown file."""
    text = path.read_text(encoding="utf-8")
    return analyze_markdown_text(text, config=config)


def _json_default(value: Any) -> Any:
    if hasattr(value, "__dict__"):
        return asdict(value)
    raise TypeError(f"Unsupported type: {type(value)}")


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Analyze Markdown structure for markdown-to-anything")
    parser.add_argument("input", help="Input Markdown file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    result = analyze_markdown_file(Path(args.input).expanduser())
    if args.pretty:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(asdict(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
