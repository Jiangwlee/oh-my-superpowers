"""T1 static checks for the debug skill."""

import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[3] / "skills" / "debug"
REFERENCES_DIR = SKILL_DIR / "references"
SKILL_MD = SKILL_DIR / "SKILL.md"

REQUIRED_REFERENCES = [
    "coding-guideline.md",
    "debugging-guideline.md",
]
FORBIDDEN_PATTERNS = [
    "bash scripts/",
    "python scripts/",
    "python3 scripts/",
    "sh scripts/",
    "./scripts/",
]


class TestSkillMd(unittest.TestCase):
    """Validate SKILL.md structure."""

    def test_skill_md_exists(self) -> None:
        """SKILL.md must exist."""
        self.assertTrue(SKILL_MD.exists(), f"SKILL.md missing: {SKILL_MD}")

    def test_frontmatter_has_name(self) -> None:
        """Frontmatter must include the skill name."""
        content = SKILL_MD.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---"), "SKILL.md missing frontmatter")
        end = content.find("\n---", 3)
        self.assertGreater(end, 0, "SKILL.md frontmatter not closed")
        block = content[3:end]
        self.assertIn("name:", block, "frontmatter missing name")
        self.assertIn("debug", block, "frontmatter missing debug skill name")

    def test_frontmatter_has_description(self) -> None:
        """Frontmatter must include a description."""
        content = SKILL_MD.read_text(encoding="utf-8")
        end = content.find("\n---", 3)
        block = content[3:end]
        self.assertIn("description:", block, "frontmatter missing description")

    def test_no_relative_script_paths(self) -> None:
        """SKILL.md must not reference relative script paths."""
        content = SKILL_MD.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            self.assertNotIn(pattern, content, f"forbidden relative path found: {pattern}")

    def test_hard_gate_present(self) -> None:
        """SKILL.md must include a HARD-GATE section."""
        content = SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("<HARD-GATE>", content, "SKILL.md missing HARD-GATE")


class TestReferences(unittest.TestCase):
    """Validate required references."""

    def test_references_directory_exists(self) -> None:
        """references/ must exist."""
        self.assertTrue(REFERENCES_DIR.exists(), "references/ directory missing")

    def test_required_references_exist(self) -> None:
        """Required references must exist."""
        for name in REQUIRED_REFERENCES:
            self.assertTrue((REFERENCES_DIR / name).exists(), f"missing reference: {name}")

    def test_required_references_non_empty(self) -> None:
        """Required references must contain substantive content."""
        for name in REQUIRED_REFERENCES:
            content = (REFERENCES_DIR / name).read_text(encoding="utf-8").strip()
            self.assertGreater(len(content), 100, f"reference too short: {name}")


if __name__ == "__main__":
    unittest.main()
