"""T1 static checks for the github-trending skill."""

from __future__ import annotations

import py_compile
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = ROOT / "skills" / "github-trending"
CLI_MAIN = ROOT / "cli" / "github-trending" / "main.py"


class TestGithubTrendingStatic(unittest.TestCase):
    """Validate the skill skeleton through unittest discovery."""

    def test_skill_md_exists_and_name_matches_directory(self) -> None:
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIsNotNone(re.search(r"^name:\s*github-trending\s*$", content, re.MULTILINE))

    def test_fetch_script_exists_and_compiles(self) -> None:
        script = SKILL_ROOT / "scripts" / "fetch_trending.py"
        self.assertTrue(script.exists())
        with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as tmp:
            py_compile.compile(str(script), cfile=tmp.name, doraise=True)

    def test_cli_wrapper_exists_and_compiles(self) -> None:
        self.assertTrue(CLI_MAIN.exists())
        with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as tmp:
            py_compile.compile(str(CLI_MAIN), cfile=tmp.name, doraise=True)

    def test_report_template_exists_with_required_markers(self) -> None:
        content = (SKILL_ROOT / "assets" / "report-template.html").read_text(encoding="utf-8")
        for marker in ["{{DATE}}", "{{TAKEAWAY}}", "{{LEAD_NAME}}", "{{FOCUS_REPOS}}", "{{REST_REPOS}}"]:
            self.assertIn(marker, content)

    def test_skill_md_uses_omp_commands_not_relative_script_calls(self) -> None:
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("omp github-trending fetch", content)
        self.assertIsNone(re.search(r"(bash|python3?|uv run)\s+scripts/", content))

    def test_no_tests_inside_skill_dir(self) -> None:
        self.assertFalse((SKILL_ROOT / "tests").exists())

    def test_no_hardcoded_personal_paths(self) -> None:
        for f in SKILL_ROOT.rglob("*"):
            if f.is_file():
                text = f.read_text(encoding="utf-8", errors="ignore")
                self.assertNotIn("/home/bruce", text, f.name)


if __name__ == "__main__":
    unittest.main()
