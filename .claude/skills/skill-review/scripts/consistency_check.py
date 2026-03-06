#!/usr/bin/env python3
"""Skill consistency checker.

Purpose: Extract command references and file references from SKILL.md,
         then validate them against actual scripts and files on disk.
         Also detects legacy pollution: commented-out code blocks and
         migration TODOs in Python scripts.
Input:   --skill-dir path to skill directory
Output:  JSON to stdout with fields: parameter_mismatches[], missing_files[],
         name_mismatch (object or null), legacy_pollution[]

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


def run_checks(skill_dir: Path) -> dict:
    """Run all consistency checks against the skill directory.

    Returns dict with keys: parameter_mismatches, missing_files, name_mismatch, legacy_pollution.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"error": f"SKILL.md not found in {skill_dir}"}

    content = skill_md.read_text(encoding="utf-8")

    issues: dict = {
        "parameter_mismatches": [],
        "missing_files": [],
        "name_mismatch": None,
        "legacy_pollution": [],
    }

    # Check frontmatter name vs directory name
    fm_name = parse_frontmatter_name(content)
    dir_name = skill_dir.name
    if fm_name and fm_name != dir_name:
        issues["name_mismatch"] = {
            "frontmatter_name": fm_name,
            "directory_name": dir_name,
        }

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
    for ref in extract_file_references(content):
        full_path = skill_dir / ref["path"]
        if not full_path.exists():
            issues["missing_files"].append({
                "type": "reference",
                "path": ref["path"],
                "line": ref["line"],
            })

    # Detect legacy pollution in scripts/
    issues["legacy_pollution"] = detect_legacy_pollution(skill_dir / "scripts")

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
