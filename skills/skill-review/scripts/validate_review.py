#!/usr/bin/env python3
"""Validate a filled-in skill-review report.

Rejects reports that still contain unfilled checkboxes, scaffold
placeholders, or `[✗]` lines without their four required sub-items
(标签 / 影响 / 修复 / 验证). Plain-text scan; no Markdown AST.

Exit code: 0 when valid, 1 when issues found, 2 on usage error.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


UNCHECKED = re.compile(r"^\s*-\s+\[\s\]\s")
FAILED_BOX = re.compile(r"^\s*-\s+\[✗\]\s+(.+?)$")
TEMPLATE_VAR = re.compile(r"\{\{[^}]+\}\}")
INLINE_CODE = re.compile(r"`[^`\n]*`")
PLACEHOLDER_TOKENS = ("__STATE__", "__EVIDENCE__")
REQUIRED_SUBITEMS = ("标签", "影响", "修复", "验证")


def _strip_inline_code(line: str) -> str:
    """Remove backtick-quoted segments so rule citations don't trigger placeholder checks."""
    return INLINE_CODE.sub("", line)


def collect_issues(text: str) -> list[str]:
    """Return one human-readable error per violation."""
    issues: list[str] = []
    lines = text.splitlines()

    in_code_block = False
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        if UNCHECKED.match(line):
            issues.append(f"line {idx}: 未勾选的 checkbox（保留 `[ ]`）")

        scan_line = _strip_inline_code(line)

        for token in PLACEHOLDER_TOKENS:
            if token in scan_line:
                issues.append(f"line {idx}: 未替换占位符 `{token}`")
                break

        if TEMPLATE_VAR.search(scan_line):
            issues.append(f"line {idx}: 残留模板变量 `{{...}}`")

    issues.extend(_check_failed_box_subitems(lines))
    return issues


def _check_failed_box_subitems(lines: list[str]) -> list[str]:
    """Each `[✗]` line must be followed by 标签/影响/修复/验证 within the next block.

    A block ends at the next non-indented line that is not blank, the next
    list item at the same level, or end of file. Sub-items are matched by
    their leading bold label (e.g. `**标签**:`).
    """
    issues: list[str] = []
    in_code_block = False
    n = len(lines)
    label_pattern = re.compile(r"^\s+(?:- )?\*\*(标签|影响|修复|验证)\*\*")

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        m = FAILED_BOX.match(line)
        if not m:
            continue

        found: set[str] = set()
        j = idx + 1
        while j < n:
            nxt = lines[j]
            nxt_stripped = nxt.strip()
            if not nxt_stripped:
                j += 1
                continue
            indent = len(nxt) - len(nxt.lstrip())
            if indent == 0 and not nxt_stripped.startswith("- "):
                break
            if indent == 0 and nxt_stripped.startswith("- "):
                break
            sub_match = label_pattern.match(nxt)
            if sub_match:
                found.add(sub_match.group(1))
            j += 1

        missing = [s for s in REQUIRED_SUBITEMS if s not in found]
        if missing:
            issues.append(
                f"line {idx + 1}: `[✗]` 行缺少子项：{', '.join(missing)}"
            )

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a filled-in skill-review report.",
    )
    parser.add_argument(
        "report",
        help="Path to the filled review report Markdown.",
    )
    args = parser.parse_args()

    report_path = Path(args.report).resolve()
    if not report_path.is_file():
        print(f"Error: report not found: {report_path}", file=sys.stderr)
        sys.exit(2)

    text = report_path.read_text(encoding="utf-8")
    issues = collect_issues(text)

    if not issues:
        print(f"OK: {report_path} 全部填写完整")
        sys.exit(0)

    print(f"FAIL: {report_path}", file=sys.stderr)
    for issue in issues:
        print(f"  {issue}", file=sys.stderr)
    print(f"\n共 {len(issues)} 处问题", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
