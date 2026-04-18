"""T1 static checks for the llm-wiki skill."""

from __future__ import annotations

import py_compile
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
REFERENCES_DIR = SKILL_DIR / "references"
SKILL_MD = SKILL_DIR / "SKILL.md"

REQUIRED_SCRIPTS = [
    "common.py",
    "init.py",
    "ingest.py",
    "nav.py",
    "lint.py",
]
REQUIRED_REFERENCES = [
    "cli.md",
    "workflow.md",
    "compile.md",
    "linting.md",
    "archive.md",
]
REQUIRED_CLI_COMMANDS = [
    "omp wiki init",
    "omp wiki ingest",
    "omp wiki nav",
    "omp wiki lint",
]
FORBIDDEN_CLI_COMMANDS = [
    "omp wiki compile",
    "omp wiki read",
]
FORBIDDEN_PATTERNS = [
    "bash scripts/",
    "python scripts/",
    "python3 scripts/",
    "sh scripts/",
    "./scripts/",
]


class TestSkillLayout(unittest.TestCase):
    """Validate llm-wiki skill structure."""

    def test_skill_md_exists(self) -> None:
        self.assertTrue(SKILL_MD.exists())

    def test_references_exist(self) -> None:
        for name in REQUIRED_REFERENCES:
            self.assertTrue((REFERENCES_DIR / name).exists(), f"missing reference file: {name}")

    def test_required_scripts_exist(self) -> None:
        for name in REQUIRED_SCRIPTS:
            self.assertTrue((SCRIPTS_DIR / name).exists(), f"missing script: {name}")


class TestSkillMd(unittest.TestCase):
    """Validate SKILL.md content."""

    def test_cli_commands_present(self) -> None:
        content = SKILL_MD.read_text(encoding="utf-8")
        for command in REQUIRED_CLI_COMMANDS:
            self.assertIn(command, content)

    def test_no_removed_cli_commands(self) -> None:
        content = SKILL_MD.read_text(encoding="utf-8")
        for command in FORBIDDEN_CLI_COMMANDS:
            self.assertNotIn(command, content)

    def test_no_relative_script_calls(self) -> None:
        content = SKILL_MD.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            self.assertNotIn(pattern, content)

    def test_query_starts_from_wiki_not_raw(self) -> None:
        content = SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("Start from the wiki, not raw", content)


class TestScriptSyntax(unittest.TestCase):
    """Compile all Python scripts."""

    def test_scripts_compile(self) -> None:
        for name in REQUIRED_SCRIPTS:
            script = SCRIPTS_DIR / name
            with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as tmp:
                py_compile.compile(str(script), cfile=tmp.name, doraise=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
