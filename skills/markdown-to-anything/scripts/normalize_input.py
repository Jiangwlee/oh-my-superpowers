#!/usr/bin/env python3
"""Deterministic Markdown input normalizer for markdown-to-anything."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

ASSISTANT_PREAMBLE_PATTERNS = [
    "现在我已经读取了",
    "让我基于这些数据生成",
    "下面是我整理的",
    "下面进入设计阶段",
]


@dataclass(slots=True)
class NormalizeResult:
    ok: bool
    input: str
    output: str
    changed: bool
    text: str
    detected: dict[str, bool]
    actions: list[str]
    warnings: list[str]
    errors: list[str]


def _strip_bom(text: str) -> tuple[str, bool]:
    if text.startswith("\ufeff"):
        return text.lstrip("\ufeff"), True
    return text, False


def _normalize_newlines(text: str) -> tuple[str, bool]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized, normalized != text


def _extract_fenced_markdown(text: str) -> tuple[str, bool]:
    match = re.search(r"```(?:markdown|md)?\s*\n([\s\S]*?)\n```", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip("\n") + "\n", True
    return text, False


def _trim_to_first_heading(text: str) -> tuple[str, bool]:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            trimmed = "\n".join(lines[idx:]).strip() + "\n"
            return trimmed, idx > 0
    return text, False


def _looks_like_assistant_preamble(text: str) -> bool:
    head = "\n".join(text.splitlines()[:8])
    return any(token in head for token in ASSISTANT_PREAMBLE_PATTERNS)


def _ensure_blank_line_before_list(text: str) -> tuple[str, bool]:
    """Ensure blank line before list items for pandoc compatibility.

    Pandoc requires a blank line before list items when they follow
    non-list content (like bold headings). Without this, lists are
    rendered as inline text instead of proper <ul>/<li> or <ol>/<li>
    structures.

    Args:
        text: Markdown text to process.

    Returns:
        Tuple of (processed_text, was_modified).
    """
    lines = text.splitlines()
    result: list[str] = []
    modified = False

    # Pattern for unordered list item: optional indent, then - or * followed by space
    # Pattern for ordered list item: optional indent, then number followed by . and space
    unordered_pattern = re.compile(r"^(\s*)[-*] ")
    ordered_pattern = re.compile(r"^(\s*)(\d+)\. ")

    for i, line in enumerate(lines):
        unordered_match = unordered_pattern.match(line)
        ordered_match = ordered_pattern.match(line)
        match = unordered_match or ordered_match

        if match:
            # This is a list item (unordered or ordered)
            current_indent = len(match.group(1))
            is_ordered = ordered_match is not None

            # Check if we need to insert a blank line before it
            need_blank_line = False

            if i == 0:
                # First line, no need for blank line
                pass
            else:
                prev_line = lines[i - 1]
                prev_unordered = unordered_pattern.match(prev_line)
                prev_ordered = ordered_pattern.match(prev_line)
                prev_match = prev_unordered or prev_ordered

                if prev_match:
                    # Previous line is also a list item
                    prev_indent = len(prev_match.group(1))
                    prev_is_ordered = prev_ordered is not None

                    # Check if switching between ordered and unordered
                    if is_ordered != prev_is_ordered:
                        # Switching list types, need blank line
                        need_blank_line = True
                    elif current_indent > prev_indent:
                        # This is a nested list item, needs blank line before
                        need_blank_line = True
                    # else: same type, same or less indent, continuation of list
                elif prev_line.strip() == "":
                    # Previous line is already blank
                    pass
                else:
                    # Previous line is non-list, non-blank content
                    # Need blank line before list
                    need_blank_line = True

            if need_blank_line and result and result[-1].strip() != "":
                result.append("")
                modified = True

        result.append(line)

    return "\n".join(result), modified


def _is_inside_list_item(lines: list[str], index: int) -> bool:
    """Check if current line is inside a list item context.

    A line is considered inside a list item if:
    1. It's indented (starts with 2+ spaces)
    2. There's a preceding list item marker at a lower indent level
    3. No blank line between the list item and this line

    Args:
        lines: All lines of the document.
        index: Current line index.

    Returns:
        True if inside a list item context.
    """
    if index == 0:
        return False

    current_line = lines[index]
    # Must be indented to be nested content
    if not re.match(r"^\s{2,}", current_line):
        return False

    current_indent = len(current_line) - len(current_line.lstrip())

    # Look backwards for a list item marker
    for i in range(index - 1, -1, -1):
        prev_line = lines[i]

        # Blank line breaks list context
        if prev_line.strip() == "":
            return False

        prev_indent = len(prev_line) - len(prev_line.lstrip())

        # Found a list item marker at lower indent - we're inside it
        if prev_indent < current_indent:
            if re.match(r"^\s*[-*]\s+", prev_line) or re.match(r"^\s*\d+\.\s+", prev_line):
                return True
            # Found non-list content at lower indent, stop searching
            return False

    return False


def _parse_markdown_table(table_lines: list[str]) -> list[list[str]]:
    """Parse markdown table lines into cell data.

    Args:
        table_lines: Lines forming the table (including header and separator).

    Returns:
        List of rows, each row is a list of cell strings.
    """
    rows: list[list[str]] = []

    for line in table_lines:
        line = line.strip()
        if not line.startswith("|"):
            continue

        # Split by | and strip whitespace
        cells = [cell.strip() for cell in line.split("|")]
        # Remove empty first/last cells from leading/trailing |
        # But keep empty cells in the middle (they represent actual empty cells)
        while cells and cells[0] == "":
            cells.pop(0)
        while cells and cells[-1] == "":
            cells.pop()
        if cells:
            rows.append(cells)

    return rows


def _convert_table_to_html(table_lines: list[str]) -> str:
    """Convert markdown table lines to HTML table.

    Args:
        table_lines: Lines forming the markdown table.

    Returns:
        HTML table string.
    """
    rows = _parse_markdown_table(table_lines)
    if len(rows) < 2:
        return "\n".join(table_lines)

    # First row is header, second is separator (|---|), rest are data
    header = rows[0]
    data_rows = rows[2:] if len(rows) > 2 else []

    html_parts = ["<table>"]

    # Header
    html_parts.append("  <thead>")
    html_parts.append("    <tr>")
    for cell in header:
        html_parts.append(f"      <th>{cell}</th>")
    html_parts.append("    </tr>")
    html_parts.append("  </thead>")

    # Body
    if data_rows:
        html_parts.append("  <tbody>")
        for row in data_rows:
            html_parts.append("    <tr>")
            for i, cell in enumerate(row):
                # Handle case where data row has fewer cells than header
                if i < len(header):
                    html_parts.append(f"      <td>{cell}</td>")
            html_parts.append("    </tr>")
        html_parts.append("  </tbody>")

    html_parts.append("</table>")

    return "\n".join(html_parts)


def _convert_nested_tables_to_html(text: str) -> tuple[str, bool]:
    """Convert indented tables inside list items to raw HTML tables.

    Pandoc cannot parse Markdown tables when they are indented (nested in list items).
    This converts them to HTML tables that render correctly in all engines.

    Args:
        text: Markdown text to process.

    Returns:
        Tuple of (processed_text, was_modified).
    """
    lines = text.splitlines()
    result: list[str] = []
    modified = False
    i = 0

    # Pattern for table row: optional indent, then |...
    table_row_pattern = re.compile(r"^(\s*)\|.*\|\s*$")

    while i < len(lines):
        line = lines[i]
        match = table_row_pattern.match(line)

        if match and _is_inside_list_item(lines, i):
            # Found start of a nested table
            base_indent = len(match.group(1))

            # Collect all consecutive table rows
            table_lines: list[str] = []
            j = i
            while j < len(lines):
                row_line = lines[j]
                row_match = table_row_pattern.match(row_line)
                if not row_match:
                    break

                row_indent = len(row_match.group(1))
                # Allow same indent level, but must still be inside list context
                if row_indent < base_indent:
                    break

                table_lines.append(row_line)
                j += 1

            # Convert to HTML table
            if len(table_lines) >= 2:  # Need at least header + separator
                html_table = _convert_table_to_html(table_lines)
                result.append(html_table)
                modified = True
                i = j
                continue

        result.append(line)
        i += 1

    return "\n".join(result), modified


def normalize_markdown_text(text: str) -> NormalizeResult:
    original = text
    actions: list[str] = []
    warnings: list[str] = []

    text, had_bom = _strip_bom(text)
    if had_bom:
        actions.append("removed_bom")

    text, newline_changed = _normalize_newlines(text)
    if newline_changed:
        actions.append("normalized_newlines")

    detected_fence = bool(re.search(r"```(?:markdown|md)?\s*\n", text, flags=re.IGNORECASE))
    text, extracted_fence = _extract_fenced_markdown(text)
    if extracted_fence:
        actions.append("extracted_fenced_markdown")

    detected_preamble = _looks_like_assistant_preamble(text)
    if detected_preamble and not extracted_fence:
        text, trimmed = _trim_to_first_heading(text)
        if trimmed:
            actions.append("removed_assistant_preamble")

    text, added_blank_lines = _ensure_blank_line_before_list(text)
    if added_blank_lines:
        actions.append("added_blank_lines_before_list")

    text, converted_tables = _convert_nested_tables_to_html(text)
    if converted_tables:
        actions.append("converted_nested_tables_to_html")

    stripped = text.strip()
    if stripped != text:
        text = stripped + "\n"
        actions.append("trimmed_outer_whitespace")

    if not stripped:
        warnings.append("normalized markdown is empty")

    detected = {
        "bom": had_bom,
        "fenced_markdown": detected_fence,
        "assistant_preamble": detected_preamble,
    }
    return NormalizeResult(
        ok=bool(stripped),
        input="",
        output="",
        changed=text != original,
        text=text,
        detected=detected,
        actions=actions,
        warnings=warnings,
        errors=[] if stripped else ["empty markdown after normalization"],
    )


def _read_text_robust(path: Path) -> tuple[str, list[str]]:
    """Read text file with encoding fallback handling.

    Tries UTF-8 first, then GBK/GB18030 for mixed-encoding files.

    Returns:
        Tuple of (text, warnings).
    """
    warnings: list[str] = []

    # Try UTF-8 strict first
    try:
        return path.read_text(encoding="utf-8"), warnings
    except UnicodeDecodeError:
        pass

    # Try GBK/GB18030 for Chinese Windows-generated files
    try:
        text = path.read_bytes().decode("gb18030")
        warnings.append("file detected as GB18030 encoding, converted to UTF-8")
        return text, warnings
    except Exception:
        pass

    # Fallback: UTF-8 with replacement
    text = path.read_bytes().decode("utf-8", errors="replace")
    warnings.append("file contains invalid UTF-8 sequences, replaced with �")
    return text, warnings


def normalize_markdown_file(input_path: Path, output_path: Path) -> NormalizeResult:
    text, read_warnings = _read_text_robust(input_path)
    result = normalize_markdown_text(text)
    result.warnings.extend(read_warnings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.text, encoding="utf-8")
    return NormalizeResult(
        ok=result.ok,
        input=str(input_path),
        output=str(output_path),
        changed=result.changed or bool(read_warnings),
        text=result.text,
        detected=result.detected,
        actions=result.actions,
        warnings=result.warnings,
        errors=result.errors,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize Markdown input")
    parser.add_argument("input", help="Input markdown file")
    parser.add_argument("--output", required=True, help="Output clean markdown file")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args()

    result = normalize_markdown_file(Path(args.input).expanduser(), Path(args.output).expanduser())
    payload = asdict(result)
    payload.pop("text", None)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(result.output)

    if not result.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
