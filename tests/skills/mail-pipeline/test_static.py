"""T1 static checks for the mail-pipeline skill."""

from __future__ import annotations

import py_compile
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = ROOT / "skills" / "mail-pipeline"
CLI_MAIN = ROOT / "cli" / "mail-pipeline" / "main.py"


def test_skill_md_exists_and_name_matches_directory() -> None:
    content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert re.search(r"^name:\s*mail-pipeline\s*$", content, re.MULTILINE)


def test_required_references_exist() -> None:
    for name in ["storage.md", "config.md", "pipeline.md", "schemas.md"]:
        assert (SKILL_ROOT / "references" / name).exists()


def test_required_scripts_exist_and_compile() -> None:
    for name in ["common.py", "init.py", "accounts.py", "run.py", "status.py"]:
        script = SKILL_ROOT / "scripts" / name
        assert script.exists()
        with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as tmp:
            py_compile.compile(str(script), cfile=tmp.name, doraise=True)


def test_cli_wrapper_exists_and_compiles() -> None:
    assert CLI_MAIN.exists()
    with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as tmp:
        py_compile.compile(str(CLI_MAIN), cfile=tmp.name, doraise=True)


def test_skill_md_uses_omp_commands_not_relative_script_calls() -> None:
    content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "omp mail-pipeline" in content
    assert not re.search(r"\b(bash|python|python3|node)\s+scripts/", content)
