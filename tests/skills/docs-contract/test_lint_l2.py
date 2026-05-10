"""T1 测试：scripts/lint.py L2 — 模式 lint + 行内豁免 + 配置叠加。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "skills" / "docs-contract")
)

from scripts.lint import lint_all, lint_l2  # noqa: E402
from scripts.scaffold import apply as apply_scaffold, plan as build_plan  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3]
ASSETS_DIR = REPO_ROOT / "skills" / "docs-contract" / "assets"


def _scaffold(tmp_path: Path) -> None:
    apply_scaffold(build_plan(tmp_path, ASSETS_DIR))


def _write(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_clean_scaffold_has_no_l2_findings(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    findings = lint_l2(tmp_path)
    assert findings == []


# ---------------------------------------------------------------------------
# Each label triggers
# ---------------------------------------------------------------------------


def test_l2_function_name_triggers(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    _write(
        tmp_path / "PROJECT.md",
        "doc-type: project\npurpose: x\nmust-not-contain: [function-name]\n",
        "见 module.foo() 实现。\n",
    )
    findings = lint_l2(tmp_path)
    rules = [f.rule for f in findings]
    assert "L2.function-name" in rules


def test_l2_file_path_triggers(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    _write(
        tmp_path / "PROJECT.md",
        "doc-type: project\npurpose: x\nmust-not-contain: [file-path]\n",
        "代码在 src/foo/bar.py 中\n",
    )
    findings = lint_l2(tmp_path)
    assert any(f.rule == "L2.file-path" for f in findings)


def test_l2_code_block_triggers(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    _write(
        tmp_path / "PROJECT.md",
        "doc-type: project\npurpose: x\nmust-not-contain: [code-block]\n",
        "```python\nx = 1\n```\n",
    )
    findings = lint_l2(tmp_path)
    assert any(f.rule == "L2.code-block" for f in findings)


def test_l2_step_verb_triggers(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    _write(
        tmp_path / "PROJECT.md",
        "doc-type: project\npurpose: x\nmust-not-contain: [step-verb]\n",
        "先初始化数据库，再启动服务。\n",
    )
    findings = lint_l2(tmp_path)
    assert any(f.rule == "L2.step-verb" for f in findings)


# ---------------------------------------------------------------------------
# Inline exemption
# ---------------------------------------------------------------------------


def test_l2_inline_exemption_suppresses(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    body = (
        "<!-- docs-contract: allow-code-block -->\n"
        "需要展示一段示例：\n"
        "```yaml\n"
        "key: value\n"
        "```\n"
    )
    _write(
        tmp_path / "PROJECT.md",
        "doc-type: project\npurpose: x\nmust-not-contain: [code-block]\n",
        body,
    )
    findings = lint_l2(tmp_path)
    assert not any(f.rule == "L2.code-block" for f in findings)


def test_l2_exemption_only_within_paragraph(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    body = (
        "<!-- docs-contract: allow-code-block -->\n"
        "段一示例：\n"
        "```yaml\n"
        "a: 1\n"
        "```\n"
        "\n"
        "段二代码块（不应被豁免）：\n"
        "```yaml\n"
        "b: 2\n"
        "```\n"
    )
    _write(
        tmp_path / "PROJECT.md",
        "doc-type: project\npurpose: x\nmust-not-contain: [code-block]\n",
        body,
    )
    findings = lint_l2(tmp_path)
    code_findings = [f for f in findings if f.rule == "L2.code-block"]
    assert len(code_findings) == 1


# ---------------------------------------------------------------------------
# must_not_contain_extra config merging
# ---------------------------------------------------------------------------


def test_l2_config_extra_labels_merge_in(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    # Frontmatter does NOT list step-verb; config injects it.
    _write(
        tmp_path / "PROJECT.md",
        "doc-type: project\npurpose: x\nmust-not-contain: []\n",
        "先做 A 再做 B。\n",
    )
    findings = lint_l2(
        tmp_path,
        must_not_contain_extra={"PROJECT.md": ("step-verb",)},
    )
    assert any(f.rule == "L2.step-verb" for f in findings)


def test_l2_unknown_label_silently_ignored(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    _write(
        tmp_path / "PROJECT.md",
        "doc-type: project\npurpose: x\nmust-not-contain: [some-future-label]\n",
        "正常内容\n",
    )
    findings = lint_l2(tmp_path)
    # No exception, no finding
    assert findings == []


# ---------------------------------------------------------------------------
# Combined L1 + L2
# ---------------------------------------------------------------------------


def test_lint_all_returns_l1_and_l2(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    # Inject an L1 violation (location mismatch) AND an L2 violation (file-path)
    _write(
        tmp_path / "wrong-location.md",
        "doc-type: project\npurpose: x\nmust-not-contain: [file-path]\n",
        "src/foo.py 实现\n",
    )
    findings = lint_all(tmp_path)
    rules = [f.rule for f in findings]
    assert any(r == "L1.location.mismatch" for r in rules)
    assert any(r == "L2.file-path" for r in rules)
