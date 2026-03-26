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

    for py_file in sorted(scripts_dir.glob("*.py")):
        lines = py_file.read_text(encoding="utf-8").splitlines()
        consecutive = 0
        block_start = 0

        for i, line in enumerate(lines, 1):
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


def check_cli_requirement(skill_dir: Path, skill_name: str) -> list[dict]:
    """Verify CLI-ization rules when scripts/ directory exists.

    Rules:
    - If scripts/ exists: exactly one file named omp-{skill_name} must be present.
    - SKILL.md must not invoke scripts via relative path (bash scripts/ or python scripts/).

    Returns list of dicts: {type, reason, detail}.
    """
    findings: list[dict] = []
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return findings

    scripts_files = [f for f in scripts_dir.iterdir() if f.is_file()]
    if not scripts_files:
        return findings

    expected_cli = f"omp-{skill_name}"
    cli_files = [f for f in scripts_files if f.name == expected_cli]

    if not cli_files:
        findings.append({
            "type": "cli",
            "reason": "missing_cli",
            "detail": f"scripts/ exists but no '{expected_cli}' CLI found. "
                      f"All scripts must be consolidated into scripts/{expected_cli}.",
        })
    elif len(cli_files) > 1:
        findings.append({
            "type": "cli",
            "reason": "multiple_cli",
            "detail": f"Found {len(cli_files)} files named '{expected_cli}'. "
                      "A skill must have exactly one CLI entry point.",
        })

    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        content = skill_md.read_text(encoding="utf-8")
        direct_invocation_pattern = re.compile(
            r"(?:python3?|bash)\s+scripts/[\w.\-/]+",
        )
        for i, line in enumerate(content.splitlines(), 1):
            if direct_invocation_pattern.search(line.strip()):
                findings.append({
                    "type": "cli",
                    "reason": "direct_script_invocation",
                    "line": i,
                    "detail": f"Direct script invocation found: '{line.strip()}'. "
                              f"Use '{expected_cli}' CLI instead.",
                })

    return findings


def run_checks(skill_dir: Path) -> dict:
    """Run all consistency checks against the skill directory.

    Returns dict with keys used by skill-review mechanical checks.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"error": f"SKILL.md not found in {skill_dir}"}

    content = skill_md.read_text(encoding="utf-8")

    issues: dict = {
        "parameter_mismatches": [],
        "missing_files": [],
        "frontmatter_warnings": [],
        "name_mismatch": None,
        "spec_violations": [],
        "force_load_syntax": [],
        "path_style_violations": [],
        "orphaned_references": [],
        "legacy_pollution": [],
        "cli_violations": [],
    }

    spec_violations, frontmatter_warnings, name_mismatch = validate_frontmatter(
        content,
        skill_dir,
    )
    issues["spec_violations"] = spec_violations
    issues["frontmatter_warnings"] = frontmatter_warnings
    issues["name_mismatch"] = name_mismatch
    issues["force_load_syntax"] = find_force_load_syntax(content)
    issues["path_style_violations"] = find_path_variable_invocations(content)

    # Check script command references
    commands = extract_script_commands(content)
    for cmd in commands:
        script_path = skill_dir / cmd["script"]
        if not script_path.exists():
            issues["missing_files"].append({
                "type": "script",
                "path": cmd["script"],
                "line": cmd["line"],
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
                    "available_flags": sorted(set(help_flags)),
                })

    # Check file references (references/, assets/)
    linked_references = extract_linked_references(content)
    for ref in extract_file_references(content):
        full_path = skill_dir / ref["path"]
        if not full_path.exists():
            issues["missing_files"].append({
                "type": "reference",
                "path": ref["path"],
                "line": ref["line"],
            })
    issues["orphaned_references"] = find_orphaned_references(
        skill_dir,
        linked_references,
    )

    # Detect legacy pollution in scripts/
    issues["legacy_pollution"] = detect_legacy_pollution(skill_dir / "scripts")

    # Check CLI-ization requirement
    fm = parse_frontmatter(content)
    skill_name = (fm or {}).get("name", "") or skill_dir.name
    issues["cli_violations"] = check_cli_requirement(skill_dir, skill_name)

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
