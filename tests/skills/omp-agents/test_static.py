"""T1 static checks for the omp-agents skill."""

from __future__ import annotations

import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[3] / "skills" / "omp-agents"
SKILL_MD = SKILL_DIR / "SKILL.md"

FORBIDDEN_PATTERNS = [
    "bash scripts/",
    "python scripts/",
    "python3 scripts/",
    "sh scripts/",
    "./scripts/",
]

REQUIRED_COMMANDS = [
    "omp run",
    "omp list agent",
]


class TestSkillLayout(unittest.TestCase):
    """Validate skill structure."""

    def test_skill_md_exists(self) -> None:
        self.assertTrue(SKILL_MD.exists())


class TestSkillMd(unittest.TestCase):
    """Validate SKILL.md content."""

    def test_no_relative_script_calls(self) -> None:
        content = SKILL_MD.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            self.assertNotIn(pattern, content)

    def test_required_commands_present(self) -> None:
        content = SKILL_MD.read_text(encoding="utf-8")
        for command in REQUIRED_COMMANDS:
            self.assertIn(command, content, f"missing command reference: {command}")

    def test_frontmatter_present(self) -> None:
        content = SKILL_MD.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---"), "SKILL.md must start with frontmatter")
        self.assertGreater(content.count("---"), 1, "SKILL.md must have closing frontmatter")


if __name__ == "__main__":
    unittest.main(verbosity=2)
