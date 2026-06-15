"""T1 static checks for the deep-research skill."""

from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[3] / "skills" / "deep-research"
SCRIPTS_DIR = SKILL_DIR / "scripts"
REFERENCES_DIR = SKILL_DIR / "references"
ASSETS_DIR = SKILL_DIR / "assets"
SKILL_MD = SKILL_DIR / "SKILL.md"

REQUIRED_SCRIPTS = [
    "common.py",
    "init.py",
    "build_report.py",
]
REQUIRED_REFERENCES = [
    "cli.md",
    "methodology.md",
    "source-strategy.md",
    "stop-criteria.md",
    "workspace.md",
    "reporting.md",
    "html-reporting.md",
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

    def test_report_page_template_exists(self) -> None:
        template = ASSETS_DIR / "report-page-template.html"
        self.assertTrue(template.exists())
        content = template.read_text(encoding="utf-8")
        for marker in ["{{REPORT_TITLE}}", "{{CONCLUSION_CARDS}}", "{{SOURCE_TABLE_ROWS}}"]:
            self.assertIn(marker, content)


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


class TestBuildReportHtml(unittest.TestCase):
    """Validate build-report writes the required HTML artifact."""

    def test_build_report_generates_html_from_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "2026-06-14T09-00-template-check"
            workspace.mkdir()
            (workspace / "state.json").write_text(
                json.dumps(
                    {
                        "topic": "模板生成检查",
                        "slug": "template-check",
                        "mode": "default",
                        "workspace": str(workspace),
                        "created_at": "2026-06-14T09:00:00",
                        "status": "initialized",
                        "report_files": {"brief": None, "full_report": None},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            brief = root / "brief.md"
            brief.write_text(
                "# 模板生成检查\n\n"
                "## 核心结论\n"
                "1. build-report 应生成 HTML（来源：https://example.com/report）\n\n"
                "## 关键分歧 / 风险\n"
                "- 来源不足会降低审计质量\n\n"
                "## 推荐下一步\n"
                "- 检查 HTML 输出\n",
                encoding="utf-8",
            )
            full_report = root / "full-report.md"
            full_report.write_text(
                "# 模板生成检查\n\n"
                "## 研究目标\n"
                "- 验证 CLI 使用模板生成报告页\n\n"
                "## 关键来源汇总\n\n"
                "| 来源 | 平台 | 摘要 |\n"
                "|------|------|------|\n"
                "| https://example.com/report | web | 证明来源表能填充证据价值 |\n\n"
                "## 未解决问题\n"
                "- 无\n",
                encoding="utf-8",
            )
            sources = root / "sources.json"
            sources.write_text(
                json.dumps(
                    [
                        {
                            "url": "https://example.com/report",
                            "title": "Example Report",
                            "platform": "web",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "build_report.py"),
                    "--workspace",
                    str(workspace),
                    "--brief-file",
                    str(brief),
                    "--full-report-file",
                    str(full_report),
                    "--sources-file",
                    str(sources),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            payload = json.loads(result.stdout)
            html_file = Path(payload["html_file"])
            self.assertTrue(html_file.exists())
            html_text = html_file.read_text(encoding="utf-8")
            self.assertNotIn("{{", html_text)
            self.assertIn("Example Report", html_text)
            self.assertIn(
                '<a href="https://example.com/report" target="_blank" rel="noreferrer">Example Report</a>',
                html_text,
            )
            self.assertNotIn(">https://example.com/report</a>", html_text)
            self.assertIn("overflow-wrap: anywhere", html_text)
            self.assertIn("证明来源表能填充证据价值", html_text)
            state = json.loads((workspace / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["report_files"]["html"], str(html_file))


if __name__ == "__main__":
    unittest.main(verbosity=2)
