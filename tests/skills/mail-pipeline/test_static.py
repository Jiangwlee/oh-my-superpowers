"""T1 static checks for the mail-pipeline skill."""

from __future__ import annotations

import py_compile
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = ROOT / "skills" / "mail-pipeline"
CLI_MAIN = ROOT / "cli" / "mail-pipeline" / "main.py"


class TestMailPipelineStatic(unittest.TestCase):
    """Validate the skill skeleton through unittest discovery."""

    def test_skill_md_exists_and_name_matches_directory(self) -> None:
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIsNotNone(re.search(r"^name:\s*mail-pipeline\s*$", content, re.MULTILINE))

    def test_required_references_exist(self) -> None:
        for name in ["storage.md", "config.md", "pipeline.md", "schemas.md"]:
            self.assertTrue((SKILL_ROOT / "references" / name).exists(), name)

    def test_required_scripts_exist_and_compile(self) -> None:
        for name in ["common.py", "init.py", "accounts.py", "list_messages.py", "show.py", "stage.py", "submit.py", "mailbox.py", "status.py"]:
            script = SKILL_ROOT / "scripts" / name
            self.assertTrue(script.exists(), name)
            with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as tmp:
                py_compile.compile(str(script), cfile=tmp.name, doraise=True)

    def test_cli_wrapper_exists_and_compiles(self) -> None:
        self.assertTrue(CLI_MAIN.exists())
        with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as tmp:
            py_compile.compile(str(CLI_MAIN), cfile=tmp.name, doraise=True)

    def test_skill_md_uses_omp_commands_not_relative_script_calls(self) -> None:
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("omp mail-pipeline", content)
        self.assertIsNone(re.search(r"\b(bash|python|python3|node)\s+scripts/", content))


if __name__ == "__main__":
    unittest.main(verbosity=2)
