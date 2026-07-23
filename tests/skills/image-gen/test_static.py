"""T1 static checks for the image-gen skill."""

import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[3] / "skills" / "image-gen"
SKILL_MD = SKILL_DIR / "SKILL.md"

FORBIDDEN_PATTERNS = [
    "bash scripts/",
    "python scripts/",
    "python3 scripts/",
    "sh scripts/",
    "./scripts/",
]


class TestSkillMd(unittest.TestCase):
    def test_skill_md_exists(self) -> None:
        self.assertTrue(SKILL_MD.exists(), f"SKILL.md missing: {SKILL_MD}")

    def test_frontmatter(self) -> None:
        content = SKILL_MD.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---"), "SKILL.md missing frontmatter")
        end = content.find("\n---", 3)
        self.assertGreater(end, 0, "SKILL.md frontmatter not closed")
        block = content[3:end]
        self.assertIn("name: image-gen", block)
        self.assertIn("description:", block)

    def test_no_relative_script_paths(self) -> None:
        content = SKILL_MD.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            self.assertNotIn(pattern, content, f"relative script path found: {pattern}")

    def test_commands_are_omp_cli(self) -> None:
        content = SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("omp web-operator generate-image", content)
        self.assertIn("omp web-operator image-serve", content)

    def test_no_tests_dir_in_skill(self) -> None:
        self.assertFalse((SKILL_DIR / "tests").exists(), "tests/ must not live in skill dir")


if __name__ == "__main__":
    unittest.main()
