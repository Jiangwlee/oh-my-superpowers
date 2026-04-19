#!/usr/bin/env python3
"""Skill consistency checker.

Purpose: Extract command references and file references from SKILL.md,
         then validate them against actual scripts and files on disk.
         Also detect mechanical spec violations and stale content that
         should be reported before semantic review begins.
Input:   --skill-dir path to skill directory
Output:  JSON to stdout with fields for mechanical review findings.

Public API:
    run_checks(skill_dir) -> dict  -- run all consistency checks
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FORCE_LOAD_PATTERN = re.compile(r"@[\w./-]*SKILL\.md|@skills/[\w./-]+")
_SCRIPT_PATH_VAR_PATTERN = re.compile(
    r"(?:python3?|bash)\s+[$][A-Z_][A-Z0-9_]*[/][\w.\-/]+",
)
_CROSS_SKILL_PATH_PATTERN = re.compile(r"(?<![\w./-])skills/([a-z0-9][\w-]*)/[\w.\-/]+")
_SEMANTIC_DEP_VERB_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:先|再|然后|接着|配合|依赖|基于)\s*(?:运行|使用|调用|跑|执行|触发)?\s*[`'\"]?([a-z][a-z0-9-]*)[`'\"]?\s*skill",
    ),
    re.compile(
        r"\b(?:first\s+)?(?:use|run|invoke|call|trigger)\s+(?:the\s+)?[`'\"]?([a-z][a-z0-9-]*)[`'\"]?\s+skill\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bafter\s+(?:running|invoking|calling|using)\s+(?:the\s+)?[`'\"]?([a-z][a-z0-9-]*)[`'\"]?\s+skill",
        re.IGNORECASE,
    ),
]
_SEMANTIC_DEP_STOPWORDS = {
    "this", "that", "the", "a", "an", "any", "every", "some",
    "such", "all", "various", "these", "those", "other", "another",
}


def parse_frontmatter_name(content: str) -> str:
    """Extract the name field from YAML frontmatter.

    Returns empty string if frontmatter is absent or name is missing.
    """
    if not content.startswith("---"):
        return ""
    end = content.find("\n---", 3)
    if end == -1:
        return ""
    block = content[3:end]
    m = re.search(r"^name:\s*(.+)$", block, re.MULTILINE)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")


def parse_frontmatter(content: str) -> dict[str, str] | None:
    """Extract simple frontmatter key-value pairs.

    Returns None when frontmatter delimiters are missing.
    """
    if not content.startswith("---"):
        return None
    end = content.find("\n---", 3)
    if end == -1:
        return None

    data: dict[str, str] = {}
    lines = content[3:end].splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" not in line:
            i += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value in {">", ">-", "|", "|-"}:
            block_lines: list[str] = []
            i += 1
            while i < len(lines):
                next_line = lines[i]
                if next_line.startswith(" ") or next_line.startswith("\t"):
                    block_lines.append(next_line.strip())
                    i += 1
                    continue
                break
            data[key] = " ".join(block_lines).strip()
            continue
        data[key] = value.strip('"').strip("'")
        i += 1
    return data


def extract_script_commands(content: str) -> list[dict]:
    """Find python/bash script invocations inside fenced code blocks.

    Matches lines like:
        python scripts/foo.py --flag value
        python3 -m scripts.bar --opt
        bash scripts/run.sh --mode x

    Returns list of dicts: {script, flags, line, raw}.
    """
    results: list[dict] = []
    in_code_block = False
    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if not in_code_block:
            continue

        # python scripts/foo.py or python3 scripts/foo.py
        m = re.match(
            r"(?:python3?)\s+(scripts/[\w.\-/]+\.py)\s*(.*)",
            stripped,
        )
        if m:
            results.append({
                "script": m.group(1),
                "flags": re.findall(r"--[\w\-]+", m.group(2)),
                "line": i,
                "raw": stripped,
            })
            continue

        # bash scripts/foo.sh
        m = re.match(
            r"bash\s+(scripts/[\w.\-/]+\.sh)\s*(.*)",
            stripped,
        )
        if m:
            results.append({
                "script": m.group(1),
                "flags": re.findall(r"--[\w\-]+", m.group(2)),
                "line": i,
                "raw": stripped,
            })

    return results


def get_script_flags(script_path: Path) -> list[str] | None:
    """Run script --help and return all --flag names found in the output.

    Returns None if the script cannot be executed or times out.
    """
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout + result.stderr
        return re.findall(r"--[\w\-]+", output)
    except Exception:
        return None


def extract_file_references(content: str) -> list[dict]:
    """Find references/ and assets/ paths mentioned anywhere in SKILL.md.

    Returns list of dicts: {path, line}.
    """
    pattern = re.compile(r"`?((?:references|assets)/[\w.\-/]+)`?")
    results: list[dict] = []
    seen: set[str] = set()
    for i, line in enumerate(content.splitlines(), 1):
        for m in pattern.finditer(line):
            p = m.group(1)
            if p not in seen:
                seen.add(p)
                results.append({"path": p, "line": i})
    return results


def extract_linked_references(content: str) -> set[str]:
    """Return referenced files under references/ from SKILL.md."""
    return {item["path"] for item in extract_file_references(content)}


def find_force_load_syntax(content: str) -> list[dict]:
    """Detect force-load syntax such as @skills/foo/SKILL.md."""
    findings: list[dict] = []
    for i, line in enumerate(content.splitlines(), 1):
        match = _FORCE_LOAD_PATTERN.search(line)
        if match:
            findings.append({
                "line": i,
                "snippet": line.strip(),
            })
    return findings


def find_path_variable_invocations(content: str) -> list[dict]:
    """Detect script invocations using environment path variables."""
    findings: list[dict] = []
    for i, line in enumerate(content.splitlines(), 1):
        match = _SCRIPT_PATH_VAR_PATTERN.search(line.strip())
        if match:
            findings.append({
                "line": i,
                "snippet": line.strip(),
            })
    return findings


def _body_lines(content: str) -> list[tuple[int, str]]:
    """Return (lineno, text) pairs from SKILL.md body, skipping frontmatter."""
    lines = content.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                start = j + 1
                break
    return [(i + 1, lines[i]) for i in range(start, len(lines))]


def find_cross_skill_references(content: str, skill_name: str) -> list[dict]:
    """Detect dependencies on other skills (path or semantic).

    Emits candidate evidence for Layer A3 Skill Independence. The semantic
    reviewer decides whether each candidate is a true violation or an allowed
    boundary mention. Frontmatter is skipped so description boundary hints
    ("Do NOT use for X — use Y instead") do not produce noise.

    Returns list of dicts: {type, line, snippet, target?}.
    """
    findings: list[dict] = []
    for lineno, line in _body_lines(content):
        for m in _CROSS_SKILL_PATH_PATTERN.finditer(line):
            target = m.group(1)
            if target == skill_name:
                continue
            if line[: m.start()].rstrip().endswith("@"):
                continue
            findings.append({
                "type": "cross_skill_path",
                "line": lineno,
                "snippet": line.strip(),
                "target": target,
            })
        matched_target: str | None = None
        for pattern in _SEMANTIC_DEP_VERB_PATTERNS:
            m = pattern.search(line)
            if not m:
                continue
            candidate = m.group(1).lower()
            if candidate == skill_name or candidate in _SEMANTIC_DEP_STOPWORDS:
                continue
            matched_target = candidate
            break
        if matched_target:
            findings.append({
                "type": "semantic_dependency",
                "line": lineno,
                "snippet": line.strip(),
                "target": matched_target,
            })
    return findings


def validate_frontmatter(
    content: str,
    skill_dir: Path,
) -> tuple[list[dict], list[dict], dict | None]:
    """Validate frontmatter structure and name constraints."""
    spec_violations: list[dict] = []
    warnings: list[dict] = []
    data = parse_frontmatter(content)

    if data is None:
        spec_violations.append({
            "type": "frontmatter",
            "reason": "missing_or_unclosed_frontmatter",
        })
        return spec_violations, warnings, None

    name = data.get("name", "")
    description = data.get("description", "")

    if not name:
        spec_violations.append({
            "type": "name",
            "reason": "missing_name",
        })
    elif not _NAME_PATTERN.fullmatch(name) or len(name) > 64:
        spec_violations.append({
            "type": "name",
            "reason": "invalid_name_format",
            "value": name,
        })

    if not description:
        spec_violations.append({
            "type": "description",
            "reason": "missing_description",
        })
    elif len(description) > 1024:
        warnings.append({
            "type": "description",
            "reason": "description_too_long",
            "length": len(description),
        })

    if name and name != skill_dir.name:
        return spec_violations, warnings, {
            "frontmatter_name": name,
            "directory_name": skill_dir.name,
        }
    return spec_violations, warnings, None


def find_orphaned_references(skill_dir: Path, linked_references: set[str]) -> list[dict]:
    """Find reference files that exist but are never linked from SKILL.md."""
    references_dir = skill_dir / "references"
    findings: list[dict] = []
    if not references_dir.is_dir():
        return findings

    for path in sorted(references_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(skill_dir).as_posix()
        if relative == "references/rubric.md":
            continue
        if relative not in linked_references:
            findings.append({"path": relative})
    return findings


def detect_legacy_pollution(scripts_dir: Path) -> list[dict]:
    """Scan Python scripts for commented-out code blocks and migration TODOs.

    Detects:
    - Consecutive commented lines (>=2) that look like logic, not prose.
    - Lines containing migration markers: TODO: remove, FIXME: migrate, # legacy, # compat.

    Returns list of dicts: {file, line, type, snippet}.
    """
    findings: list[dict] = []
    if not scripts_dir.is_dir():
        return findings

    # Anchored to line start so docstrings and string literals are not matched.
    # "legacy" and "compat" only match when they are the entire comment body.
    migration_pattern = re.compile(
        r"^\s*#\s*(?:TODO:\s*(?:remove|delete)\b|FIXME:\s*migrat\w*\b|(legacy|compat)\s*$)",
        re.IGNORECASE,
    )
    # Matches commented lines that contain code-like tokens (=, (, ), :, import, def, return)
    code_comment_pattern = re.compile(r"^\s*#.*[=(){}\[\]:]\s*\S")

    pep723_delim = re.compile(r"^\s*#\s*///\s*(?:script)?\s*$")

    for py_file in sorted(scripts_dir.glob("*.py")):
        lines = py_file.read_text(encoding="utf-8").splitlines()
        consecutive = 0
        block_start = 0
        in_pep723 = False

        for i, line in enumerate(lines, 1):
            # PEP 723 inline-script metadata block: skip everything between `# ///` delimiters
            if pep723_delim.match(line):
                in_pep723 = not in_pep723
                consecutive = 0
                continue
            if in_pep723:
                continue

            # Migration TODO detection
            if migration_pattern.match(line):
                findings.append({
                    "file": py_file.name,
                    "line": i,
                    "type": "migration_todo",
                    "snippet": line.strip(),
                })

            # Commented-out code block detection
            if code_comment_pattern.match(line):
                if consecutive == 0:
                    block_start = i
                consecutive += 1
            else:
                if consecutive >= 2:
                    findings.append({
                        "file": py_file.name,
                        "line": block_start,
                        "type": "commented_code_block",
                        "snippet": f"{consecutive} consecutive commented lines starting here",
                    })
                consecutive = 0

        # Flush trailing block
        if consecutive >= 2:
            findings.append({
                "file": py_file.name,
                "line": block_start,
                "type": "commented_code_block",
                "snippet": f"{consecutive} consecutive commented lines starting here",
            })

    return findings


def collect_review_files(skill_dir: Path) -> list[tuple[Path, str, str]]:
    """Collect every file that agent may load at runtime.

    Scope: SKILL.md + references/**/*.md. scripts/ and assets/ are handled
    by their own dedicated checks.

    Returns list of (absolute_path, relative_posix_path, content).
    """
    files: list[tuple[Path, str, str]] = []
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        files.append((
            skill_md,
            "SKILL.md",
            skill_md.read_text(encoding="utf-8"),
        ))
    ref_dir = skill_dir / "references"
    if ref_dir.is_dir():
        for path in sorted(ref_dir.rglob("*.md")):
            if not path.is_file():
                continue
            rel = path.relative_to(skill_dir).as_posix()
            files.append((path, rel, path.read_text(encoding="utf-8")))
    return files


_MD_LEGACY_PATTERN = re.compile(
    r"<!--[^>]*?\b(TODO|FIXME|deprecated|legacy|migrat\w*|obsolete)\b[^>]*?-->",
    re.IGNORECASE,
)
_MD_DEPRECATED_HEADING_PATTERN = re.compile(
    r"^#{1,6}\s+.*\((?:deprecated|legacy|obsolete|removed)\)",
    re.IGNORECASE,
)


def detect_md_legacy_markers(
    files: list[tuple[Path, str, str]],
) -> list[dict]:
    """Scan markdown files for HTML-comment migration markers and deprecated headings.

    Returns list of dicts: {source_file, line, type, snippet}.
    """
    findings: list[dict] = []
    for _, rel, content in files:
        for i, line in enumerate(content.splitlines(), 1):
            if _MD_LEGACY_PATTERN.search(line):
                findings.append({
                    "source_file": rel,
                    "line": i,
                    "type": "html_comment_migration",
                    "snippet": line.strip(),
                })
            elif _MD_DEPRECATED_HEADING_PATTERN.match(line):
                findings.append({
                    "source_file": rel,
                    "line": i,
                    "type": "deprecated_heading",
                    "snippet": line.strip(),
                })
    return findings


_COMMAND_BODY_PATTERN = re.compile(
    r"(omp\s+[a-z][\w-]*(?:\s+[a-z][\w-]*)?|python3?\s+scripts/[\w.\-/]+\.py|bash\s+scripts/[\w.\-/]+\.sh)([^`\n]*)",
)
_INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")


def _extract_invocations_from_line(line: str) -> list[tuple[str, list[str], str]]:
    """Return list of (head, flags, raw) for every command invocation in a line.

    Accepts both fenced-code-block lines (passed as-is) and inline `` `...` ``
    backtick content (caller strips the backticks).
    """
    results: list[tuple[str, list[str], str]] = []
    for m in _COMMAND_BODY_PATTERN.finditer(line):
        head = m.group(1).strip()
        tail = m.group(2)
        body = (head + tail).strip()
        flags = sorted(set(re.findall(r"--[\w\-]+", body)))
        results.append((head, flags, body))
    return results


def find_cross_file_command_variants(
    files: list[tuple[Path, str, str]],
) -> list[dict]:
    """Collect invocations of the same command across files to surface flag drift.

    Scans both fenced code blocks and inline backtick spans, because
    SKILL.md commonly writes commands as inline code while references put
    them in fenced blocks. Groups by command head (e.g. `omp fake`) and
    collects distinct flag sets.

    Emits one finding per command head that has >1 distinct flag set OR
    appears in >=2 files. Layer B decides if drift is a real contradiction.

    Returns list of dicts: {command, variants: [{source_file, line, flags, raw}]}.
    """
    variants: dict[str, list[dict]] = {}
    for _, rel, content in files:
        in_code_block = False
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            sources: list[str] = []
            if in_code_block:
                sources.append(line)
            else:
                sources.extend(m.group(1) for m in _INLINE_CODE_PATTERN.finditer(line))
            for src in sources:
                for head, flags, raw in _extract_invocations_from_line(src):
                    variants.setdefault(head, []).append({
                        "source_file": rel,
                        "line": i,
                        "flags": flags,
                        "raw": raw,
                    })

    findings: list[dict] = []
    for head, occurrences in variants.items():
        distinct_flag_sets = {tuple(o["flags"]) for o in occurrences}
        distinct_files = {o["source_file"] for o in occurrences}
        if len(distinct_flag_sets) > 1 or (
            len(distinct_files) > 1 and len(occurrences) > 1
        ):
            findings.append({
                "command": head,
                "variants": occurrences,
            })
    return findings


def _find_project_bin(skill_dir: Path) -> Path | None:
    """Walk up from skill_dir to find a bin/ directory (project root indicator)."""
    current = skill_dir.resolve()
    for _ in range(6):  # max 6 levels up
        candidate = current / "bin"
        if candidate.is_dir():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def check_cli_requirement(
    skill_dir: Path,
    skill_name: str,
    review_files: list[tuple[Path, str, str]],
) -> list[dict]:
    """Verify CLI-ization rules when scripts/ directory exists.

    Accepts either CLI layout:
    - Per-skill `bin/omp-<skill>` (classic)
    - Unified `cli/<skill>/main.py` routed via `bin/omp <skill>` (oh-my-superpowers)

    Scans every review file (SKILL.md + references/**/*.md) for direct relative
    script invocations — agent loads these files at runtime and may copy the
    invocation form.

    Returns list of dicts: {type, reason, source_file?, line?, detail}.
    """
    findings: list[dict] = []
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return findings

    scripts_files = [f for f in scripts_dir.iterdir() if f.is_file()]
    if not scripts_files:
        return findings

    expected_cli = f"omp-{skill_name}"
    bin_dir = _find_project_bin(skill_dir)
    cli_files = [f for f in bin_dir.iterdir() if f.name == expected_cli] if bin_dir else []

    project_root = bin_dir.parent if bin_dir else None
    unified_main = project_root / "cli" / skill_name / "main.py" if project_root else None
    has_unified_cli = unified_main.is_file() if unified_main else False

    if not cli_files and not has_unified_cli:
        bin_hint = str(bin_dir) if bin_dir else "bin/"
        findings.append({
            "type": "cli",
            "reason": "missing_cli",
            "detail": f"scripts/ exists but no CLI entry point found. Expected either "
                      f"'{bin_hint}/{expected_cli}' or 'cli/{skill_name}/main.py' "
                      f"(unified omp router).",
        })
    elif len(cli_files) > 1:
        findings.append({
            "type": "cli",
            "reason": "multiple_cli",
            "detail": f"Found {len(cli_files)} files named '{expected_cli}' in bin/. "
                      "A skill must have exactly one CLI entry point.",
        })

    direct_invocation_pattern = re.compile(
        r"(?:python3?|bash)\s+scripts/[\w.\-/]+",
    )
    for _, rel, content in review_files:
        in_code_block = False
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if not in_code_block:
                continue
            if direct_invocation_pattern.search(stripped):
                findings.append({
                    "type": "cli",
                    "reason": "direct_script_invocation",
                    "source_file": rel,
                    "line": i,
                    "detail": f"Direct script invocation found: '{stripped}'. "
                              f"Use '{expected_cli}' CLI instead.",
                })

    return findings


def run_checks(skill_dir: Path) -> dict:
    """Run all consistency checks against the skill directory.

    Scope: SKILL.md + references/**/*.md are all review targets. Every
    finding that is traceable to a file carries `source_file`.

    Returns dict with keys used by skill-review mechanical checks.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"error": f"SKILL.md not found in {skill_dir}"}

    review_files = collect_review_files(skill_dir)
    skill_content = next(
        (c for _, rel, c in review_files if rel == "SKILL.md"),
        "",
    )

    issues: dict = {
        "review_scope": [rel for _, rel, _ in review_files],
        "parameter_mismatches": [],
        "missing_files": [],
        "frontmatter_warnings": [],
        "name_mismatch": None,
        "spec_violations": [],
        "force_load_syntax": [],
        "path_style_violations": [],
        "cross_skill_references": [],
        "orphaned_references": [],
        "scripts_legacy_pollution": [],
        "md_legacy_markers": [],
        "cross_file_command_variants": [],
        "cli_violations": [],
    }

    spec_violations, frontmatter_warnings, name_mismatch = validate_frontmatter(
        skill_content,
        skill_dir,
    )
    issues["spec_violations"] = spec_violations
    issues["frontmatter_warnings"] = frontmatter_warnings
    issues["name_mismatch"] = name_mismatch

    fm = parse_frontmatter(skill_content)
    skill_name = (fm or {}).get("name", "") or skill_dir.name

    linked_references: set[str] = set()

    for _, rel, content in review_files:
        for item in find_force_load_syntax(content):
            item["source_file"] = rel
            issues["force_load_syntax"].append(item)
        for item in find_path_variable_invocations(content):
            item["source_file"] = rel
            issues["path_style_violations"].append(item)
        for item in find_cross_skill_references(content, skill_name):
            item["source_file"] = rel
            issues["cross_skill_references"].append(item)

        for cmd in extract_script_commands(content):
            script_path = skill_dir / cmd["script"]
            if not script_path.exists():
                issues["missing_files"].append({
                    "type": "script",
                    "path": cmd["script"],
                    "line": cmd["line"],
                    "source_file": rel,
                })
                continue
            if not cmd["flags"]:
                continue
            help_flags = get_script_flags(script_path)
            if help_flags is None:
                continue
            for flag in cmd["flags"]:
                if flag not in help_flags:
                    issues["parameter_mismatches"].append({
                        "script": cmd["script"],
                        "flag": flag,
                        "line": cmd["line"],
                        "source_file": rel,
                        "available_flags": sorted(set(help_flags)),
                    })

        linked_references.update(extract_linked_references(content))
        for ref in extract_file_references(content):
            full_path = skill_dir / ref["path"]
            if not full_path.exists():
                issues["missing_files"].append({
                    "type": "reference",
                    "path": ref["path"],
                    "line": ref["line"],
                    "source_file": rel,
                })

    issues["orphaned_references"] = find_orphaned_references(
        skill_dir,
        linked_references,
    )
    issues["scripts_legacy_pollution"] = detect_legacy_pollution(
        skill_dir / "scripts",
    )
    issues["md_legacy_markers"] = detect_md_legacy_markers(review_files)
    issues["cross_file_command_variants"] = find_cross_file_command_variants(
        review_files,
    )
    issues["cli_violations"] = check_cli_requirement(
        skill_dir,
        skill_name,
        review_files,
    )

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check consistency between SKILL.md and actual skill files.",
    )
    parser.add_argument(
        "--skill-dir",
        required=True,
        help="Path to the skill directory to check.",
    )
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).resolve()
    if not skill_dir.is_dir():
        print(json.dumps({"error": f"Directory not found: {skill_dir}"}))
        sys.exit(1)

    result = run_checks(skill_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
