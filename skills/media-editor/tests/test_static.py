"""T1 静态检查：验证 media-editor skill 结构和代码语法。

检查内容：
- SKILL.md 存在且不含相对路径脚本调用
- SKILL.md 包含所有必要 CLI 命令
- 4 个脚本文件存在
- 所有脚本通过语法检查（py_compile）
"""

import py_compile
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
SKILL_MD = SKILL_DIR / "SKILL.md"

REQUIRED_SCRIPTS = ["init.py", "save.py", "query.py", "promote.py"]
REQUIRED_CLI_COMMANDS = [
    "omp-media-init",
    "omp-media-save",
    "omp-media-query",
    "omp-media-promote",
]
FORBIDDEN_PATTERNS = [
    "bash scripts/",
    "python scripts/",
    "python3 scripts/",
    "sh scripts/",
    "./scripts/",
]


class TestSkillMd(unittest.TestCase):
    """SKILL.md 结构验证。"""

    def test_skill_md_exists(self) -> None:
        """SKILL.md 必须存在。"""
        self.assertTrue(SKILL_MD.exists(), f"SKILL.md 不存在：{SKILL_MD}")

    def test_no_relative_script_paths(self) -> None:
        """SKILL.md 不得包含相对路径脚本调用。"""
        content = SKILL_MD.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            self.assertNotIn(
                pattern,
                content,
                f"SKILL.md 包含禁止的相对路径调用：'{pattern}'",
            )

    def test_required_cli_commands_present(self) -> None:
        """SKILL.md 必须包含所有 CLI 命令。"""
        content = SKILL_MD.read_text(encoding="utf-8")
        for cmd in REQUIRED_CLI_COMMANDS:
            self.assertIn(cmd, content, f"SKILL.md 缺少 CLI 命令：{cmd}")


class TestScriptsExist(unittest.TestCase):
    """脚本文件存在性验证。"""

    def test_scripts_directory_exists(self) -> None:
        """scripts/ 目录必须存在。"""
        self.assertTrue(SCRIPTS_DIR.exists(), f"scripts/ 目录不存在：{SCRIPTS_DIR}")

    def test_all_required_scripts_exist(self) -> None:
        """所有必要脚本文件必须存在。"""
        for script_name in REQUIRED_SCRIPTS:
            script_path = SCRIPTS_DIR / script_name
            self.assertTrue(
                script_path.exists(),
                f"脚本文件不存在：{script_path}",
            )


class TestScriptSyntax(unittest.TestCase):
    """脚本语法验证（py_compile）。"""

    def _check_syntax(self, script_name: str) -> None:
        script_path = SCRIPTS_DIR / script_name
        if not script_path.exists():
            self.skipTest(f"脚本不存在，跳过语法检查：{script_name}")
        try:
            with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as tmp:
                py_compile.compile(str(script_path), cfile=tmp.name, doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"{script_name} 语法错误：{e}")

    def test_init_syntax(self) -> None:
        self._check_syntax("init.py")

    def test_save_syntax(self) -> None:
        self._check_syntax("save.py")

    def test_query_syntax(self) -> None:
        self._check_syntax("query.py")

    def test_promote_syntax(self) -> None:
        self._check_syntax("promote.py")


if __name__ == "__main__":
    unittest.main(verbosity=2)
