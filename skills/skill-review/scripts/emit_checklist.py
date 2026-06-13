#!/usr/bin/env python3
"""Emit a per-dimension review scaffold for a skill.

Reads `references/rubric.md` (always co-located with this script) to
enumerate every checkbox per dimension, runs `consistency_check.run_checks`
to attach mechanical findings, and writes a Markdown scaffold the agent
must fill in. Validation is delegated to `validate_review.py`.

Output shape: see `assets/review-result-template.md`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from consistency_check import run_checks  # noqa: E402


SKILL_REVIEW_DIR = Path(__file__).resolve().parent.parent
RUBRIC_PATH = SKILL_REVIEW_DIR / "references" / "rubric.md"

DIMENSION_HEADING = re.compile(r"^###\s+([AB]\d+)\.\s+(.+?)\s*$")
NEXT_HEADING = re.compile(r"^(?:###\s+|---\s*$)")
CHECKBOX = re.compile(r"^-\s+\[\s\]\s+(.+?)\s*$")


def parse_rubric(rubric_text: str) -> list[dict]:
    """Extract dimension code, title, and checklist items from rubric.md.

    A dimension's checklist spans from its `### Xn. Title` heading to the
    next `### ` heading or `---` separator. Nested bullets under a checkbox
    item are merged into the checkbox text via newline-stripped joining.
    """
    lines = rubric_text.splitlines()
    dimensions: list[dict] = []
    current: dict | None = None

    for line in lines:
        m = DIMENSION_HEADING.match(line)
        if m:
            if current is not None:
                dimensions.append(current)
            current = {"code": m.group(1), "title": m.group(2).strip(), "items": []}
            continue
        if current is None:
            continue
        if NEXT_HEADING.match(line):
            dimensions.append(current)
            current = None
            continue
        cb = CHECKBOX.match(line)
        if cb:
            current["items"].append(cb.group(1).strip())

    if current is not None:
        dimensions.append(current)

    return dimensions


def severity_counts(findings: dict) -> tuple[int, int, int]:
    """Approximate finding counts by reading the most actionable JSON arrays.

    The exact CRITICAL/WARNING/SUGGESTION mapping is decided per-dimension
    during semantic review. This is a sanity-check pre-count: any non-empty
    mechanical array implies at least one finding the agent must address.
    """
    critical_keys = ("missing_files", "force_load_syntax", "cross_skill_references", "cli_violations")
    warning_keys = (
        "parameter_mismatches",
        "spec_violations",
        "frontmatter_warnings",
        "path_style_violations",
        "scripts_legacy_pollution",
        "md_legacy_markers",
        "cross_file_command_variants",
    )
    suggestion_keys = ("orphaned_references",)

    crit = sum(len(findings.get(k, [])) for k in critical_keys)
    if findings.get("name_mismatch"):
        crit += 1
    warn = sum(len(findings.get(k, [])) for k in warning_keys)
    sugg = sum(len(findings.get(k, [])) for k in suggestion_keys)
    return crit, warn, sugg


def render_dimension(dim: dict, scripts_dir_exists: bool) -> str:
    """Render one dimension as a checklist block.

    B5 is N/A when `scripts/` is absent; in that case items collapse to
    `[—]` lines with a fixed reason.
    """
    lines: list[str] = []
    if dim["code"] == "B5" and not scripts_dir_exists:
        lines.append(f"### {dim['code']}. {dim['title']} — N/A")
        lines.append("")
        for item in dim["items"]:
            lines.append(f"- [—] {item} → scripts/ 目录不存在")
        return "\n".join(lines)

    lines.append(f"### {dim['code']}. {dim['title']} — __STATE__")
    lines.append("")
    for item in dim["items"]:
        lines.append(f"- [ ] {item} → __STATE__ · __EVIDENCE__")
    return "\n".join(lines)


def render_scaffold(skill_dir: Path, findings: dict, dimensions: list[dict]) -> str:
    """Build the full scaffold Markdown."""
    skill_name = skill_dir.name
    review_scope = findings.get("review_scope", [])
    if "error" in findings:
        mech_status = f"失败（原因：{findings['error']}）"
    else:
        mech_status = "完成"
    crit, warn, sugg = severity_counts(findings)

    scripts_dir_exists = (skill_dir / "scripts").is_dir()

    parts: list[str] = []
    parts.append(f"# skill-review: {skill_name}")
    parts.append("")
    parts.append(f"审查路径：`{skill_dir}`")
    parts.append(f"机械扫描范围：{', '.join(f'`{p}`' for p in review_scope) or '（空）'}")
    parts.append("语义审查范围：`SKILL.md`, `references/**/*.md`, `scripts/*`, `assets/**`")
    parts.append(f"机械检查：{mech_status}")
    parts.append(f"机械检查原始计数：{crit} CRITICAL · {warn} WARNING · {sugg} SUGGESTION")
    parts.append("")
    parts.append("填写规则见 SKILL.md。`omp skill-review validate <path>` 验证完整性。")
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("## 机械检查 JSON")
    parts.append("")
    parts.append("<details>")
    parts.append("<summary>consistency_check 原始输出</summary>")
    parts.append("")
    parts.append("```json")
    parts.append(json.dumps(findings, indent=2, ensure_ascii=False))
    parts.append("```")
    parts.append("")
    parts.append("</details>")
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("## 审查结果")
    parts.append("")

    for dim in dimensions:
        parts.append(render_dimension(dim, scripts_dir_exists))
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit a per-dimension review scaffold for a skill.",
    )
    parser.add_argument(
        "--skill-dir",
        required=True,
        help="Path to the skill directory to review.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write the scaffold Markdown.",
    )
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).resolve()
    if not skill_dir.is_dir():
        print(f"Error: directory not found: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    if not RUBRIC_PATH.is_file():
        print(f"Error: rubric not found at {RUBRIC_PATH}", file=sys.stderr)
        sys.exit(1)

    rubric_text = RUBRIC_PATH.read_text(encoding="utf-8")
    dimensions = parse_rubric(rubric_text)
    if not dimensions:
        print("Error: failed to parse any dimension from rubric.md", file=sys.stderr)
        sys.exit(1)

    findings = run_checks(skill_dir)
    scaffold = render_scaffold(skill_dir, findings, dimensions)

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(scaffold, encoding="utf-8")
    print(str(output_path))


if __name__ == "__main__":
    main()
