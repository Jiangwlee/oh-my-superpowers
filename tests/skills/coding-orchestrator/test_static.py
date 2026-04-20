"""T1 静态检查：验证 coding-orchestrator skill 结构和代码语法。

检查内容：
- SKILL.md 存在且 frontmatter 合法
- hooks.json 存在且结构正确
- references/、worker-refs/、templates/ 文件存在
- 所有脚本文件存在且通过语法检查（py_compile）
- 新脚本入口支持 --help
"""

import json
import py_compile
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[3] / "skills" / "coding-orchestrator"
SCRIPTS_DIR = SKILL_DIR / "scripts"
REFERENCES_DIR = SKILL_DIR / "references"
WORKER_REFS_DIR = SKILL_DIR / "worker-refs"
TEMPLATES_DIR = SKILL_DIR / "templates"
SKILL_MD = SKILL_DIR / "SKILL.md"
HOOKS_JSON = SKILL_DIR / "hooks.json"

REQUIRED_REFERENCES = [
    "constitution.md",
    "handoff-guideline.md",
]
REQUIRED_WORKER_REFS = [
    "worker-guideline.md",
    "debugging-guideline.md",
]
REQUIRED_TEMPLATES = [
    "task.md",
    "story.md",
    "tasks.yaml",
    "handoff-context.yaml",
    "task-skeleton-reviewer-prompt.md",
    "review-rubric-default.md",
    "review-rubric-strict.md",
    "review-rubric-minimal.md",
]
REQUIRED_SCRIPTS = ["handoff.py", "task.py", "archive.py", "review.py", "story.py", "common.py"]
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

    def test_frontmatter_has_name(self) -> None:
        """SKILL.md frontmatter 必须包含 name 字段。"""
        content = SKILL_MD.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---"), "SKILL.md 缺少 frontmatter")
        end = content.find("\n---", 3)
        self.assertGreater(end, 0, "SKILL.md frontmatter 未闭合")
        block = content[3:end]
        self.assertIn("name:", block, "SKILL.md frontmatter 缺少 name 字段")
        self.assertIn("coding-orchestrator", block)

    def test_frontmatter_has_description(self) -> None:
        """SKILL.md frontmatter 必须包含 description 字段。"""
        content = SKILL_MD.read_text(encoding="utf-8")
        end = content.find("\n---", 3)
        block = content[3:end]
        self.assertIn("description:", block, "SKILL.md frontmatter 缺少 description 字段")

    def test_no_relative_script_paths(self) -> None:
        """SKILL.md 不得包含相对路径脚本调用。"""
        content = SKILL_MD.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            self.assertNotIn(
                pattern,
                content,
                f"SKILL.md 包含禁止的相对路径调用：'{pattern}'",
            )

    def test_hard_gate_present(self) -> None:
        """SKILL.md 必须包含 HARD-GATE 标记。"""
        content = SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("<HARD-GATE>", content, "SKILL.md 缺少 HARD-GATE 标记")


class TestHooksJson(unittest.TestCase):
    """hooks.json 结构验证。"""

    def test_hooks_json_exists(self) -> None:
        """hooks.json 必须存在。"""
        self.assertTrue(HOOKS_JSON.exists(), f"hooks.json 不存在：{HOOKS_JSON}")

    def test_hooks_json_valid(self) -> None:
        """hooks.json 必须是合法 JSON。"""
        content = HOOKS_JSON.read_text(encoding="utf-8")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            self.fail(f"hooks.json 不是合法 JSON：{e}")
        self.assertIn("hooks", data, "hooks.json 缺少 hooks 顶层键")

    def test_hooks_is_mapping(self) -> None:
        """hooks.json 的 hooks 字段必须是对象。"""
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        self.assertIsInstance(data["hooks"], dict)


class TestReferences(unittest.TestCase):
    """references/ 文件存在性验证。"""

    def test_references_directory_exists(self) -> None:
        """references/ 目录必须存在。"""
        self.assertTrue(REFERENCES_DIR.exists(), "references/ 目录不存在")

    def test_all_required_references_exist(self) -> None:
        """所有必要的 reference 文件必须存在。"""
        for ref_name in REQUIRED_REFERENCES:
            ref_path = REFERENCES_DIR / ref_name
            self.assertTrue(ref_path.exists(), f"reference 文件不存在：{ref_name}")

    def test_references_not_empty(self) -> None:
        """reference 文件不得为空。"""
        for ref_name in REQUIRED_REFERENCES:
            ref_path = REFERENCES_DIR / ref_name
            if ref_path.exists():
                content = ref_path.read_text(encoding="utf-8").strip()
                self.assertTrue(len(content) > 100, f"{ref_name} 内容过短（<100字符）")


class TestWorkerRefs(unittest.TestCase):
    """worker-refs/ 文件存在性验证。"""

    def test_worker_refs_directory_exists(self) -> None:
        """worker-refs/ 目录必须存在。"""
        self.assertTrue(WORKER_REFS_DIR.exists(), "worker-refs/ 目录不存在")

    def test_all_required_worker_refs_exist(self) -> None:
        """所有必要的 worker-ref 文件必须存在。"""
        for ref_name in REQUIRED_WORKER_REFS:
            ref_path = WORKER_REFS_DIR / ref_name
            self.assertTrue(ref_path.exists(), f"worker-ref 文件不存在：{ref_name}")

    def test_worker_refs_not_empty(self) -> None:
        """worker-ref 文件不得为空。"""
        for ref_name in REQUIRED_WORKER_REFS:
            ref_path = WORKER_REFS_DIR / ref_name
            if ref_path.exists():
                content = ref_path.read_text(encoding="utf-8").strip()
                self.assertTrue(len(content) > 100, f"{ref_name} 内容过短（<100字符）")


class TestTemplates(unittest.TestCase):
    """templates/ 文件存在性验证。"""

    def test_templates_directory_exists(self) -> None:
        """templates/ 目录必须存在。"""
        self.assertTrue(TEMPLATES_DIR.exists(), "templates/ 目录不存在")

    def test_all_required_templates_exist(self) -> None:
        """所有必要的 template 文件必须存在。"""
        for tpl_name in REQUIRED_TEMPLATES:
            tpl_path = TEMPLATES_DIR / tpl_name
            self.assertTrue(tpl_path.exists(), f"template 文件不存在：{tpl_name}")

    def test_templates_not_empty(self) -> None:
        """template 文件不得为空。"""
        for tpl_name in REQUIRED_TEMPLATES:
            tpl_path = TEMPLATES_DIR / tpl_name
            if tpl_path.exists():
                content = tpl_path.read_text(encoding="utf-8").strip()
                self.assertTrue(len(content) > 50, f"{tpl_name} 内容过短（<50字符）")


class TestScriptsExist(unittest.TestCase):
    """脚本文件存在性验证。"""

    def test_scripts_directory_exists(self) -> None:
        """scripts/ 目录必须存在。"""
        self.assertTrue(SCRIPTS_DIR.exists(), f"scripts/ 目录不存在")

    def test_all_required_scripts_exist(self) -> None:
        """所有必要脚本文件必须存在。"""
        for script_name in REQUIRED_SCRIPTS:
            script_path = SCRIPTS_DIR / script_name
            self.assertTrue(
                script_path.exists(),
                f"脚本文件不存在：{script_name}",
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

    def test_handoff_syntax(self) -> None:
        self._check_syntax("handoff.py")

    def test_task_syntax(self) -> None:
        self._check_syntax("task.py")

    def test_archive_syntax(self) -> None:
        self._check_syntax("archive.py")

    def test_review_syntax(self) -> None:
        self._check_syntax("review.py")

    def test_story_syntax(self) -> None:
        self._check_syntax("story.py")

    def test_common_syntax(self) -> None:
        self._check_syntax("common.py")


class TestScriptHelp(unittest.TestCase):
    """脚本 --help 支持验证。"""

    def _check_help(self, script_name: str) -> None:
        script_path = SCRIPTS_DIR / script_name
        if not script_path.exists():
            self.skipTest(f"脚本不存在，跳过 --help 检查：{script_name}")
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, f"{script_name} --help 返回非零：{result.stderr}")
        self.assertTrue(
            "--story-dir" in result.stdout or script_name == "common.py",
            f"{script_name} --help 缺少 --story-dir",
        )

    def test_handoff_help(self) -> None:
        self._check_help("handoff.py")

    def test_task_help(self) -> None:
        self._check_help("task.py")

    def test_archive_help(self) -> None:
        self._check_help("archive.py")

    def test_review_help(self) -> None:
        self._check_help("review.py")

    def test_story_help(self) -> None:
        self._check_help("story.py")


if __name__ == "__main__":
    unittest.main(verbosity=2)
