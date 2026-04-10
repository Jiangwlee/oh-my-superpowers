"""T1 static checks for the deep-research skill."""

from __future__ import annotations

import py_compile
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
REFERENCES_DIR = SKILL_DIR / "references"
EVALS_DIR = SKILL_DIR / "evals"
SKILL_MD = SKILL_DIR / "SKILL.md"

REQUIRED_SCRIPTS = [
    "cli.py",
    "common.py",
    "init.py",
    "build_report.py",
]
REQUIRED_REFERENCES = [
    "README.md",
    "cli.md",
    "methodology.md",
    "source-strategy.md",
    "stop-criteria.md",
    "workspace.md",
    "state-schema.md",
    "reporting.md",
]
REQUIRED_CLI_COMMANDS = [
    "omp deep-research <subcommand> [args]",
]
FORBIDDEN_PATTERNS = [
    "bash scripts/",
    "python scripts/",
    "python3 scripts/",
    "sh scripts/",
    "./scripts/",
]


class TestSkillLayout(unittest.TestCase):
    """Validate skill structure and references."""

    def test_skill_md_exists(self) -> None:
        self.assertTrue(SKILL_MD.exists())

    def test_references_exist(self) -> None:
        for name in REQUIRED_REFERENCES:
            self.assertTrue((REFERENCES_DIR / name).exists(), f"missing reference file: {name}")

    def test_required_scripts_exist(self) -> None:
        for name in REQUIRED_SCRIPTS:
            self.assertTrue((SCRIPTS_DIR / name).exists(), f"missing script: {name}")

    def test_evals_exist(self) -> None:
        self.assertTrue((EVALS_DIR / "trigger-cases" / "README.md").exists())
        self.assertTrue((EVALS_DIR / "output-quality" / "README.md").exists())

    def test_trigger_case_samples_exist(self) -> None:
        self.assertTrue((EVALS_DIR / "trigger-cases" / "should-trigger" / "01-deep-dive.txt").exists())
        self.assertTrue((EVALS_DIR / "trigger-cases" / "should-not-trigger" / "01-single-fact.txt").exists())


class TestSkillMd(unittest.TestCase):
    """Validate SKILL.md content."""

    def test_cli_commands_present(self) -> None:
        content = SKILL_MD.read_text(encoding="utf-8")
        for command in REQUIRED_CLI_COMMANDS:
            self.assertIn(command, content)

    def test_no_relative_script_calls(self) -> None:
        content = SKILL_MD.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            self.assertNotIn(pattern, content)


class TestScriptSyntax(unittest.TestCase):
    """Compile all Python scripts."""

    def test_scripts_compile(self) -> None:
        for name in REQUIRED_SCRIPTS:
            script = SCRIPTS_DIR / name
            with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as tmp:
                py_compile.compile(str(script), cfile=tmp.name, doraise=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
