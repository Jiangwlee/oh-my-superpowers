"""T1 static checks for agent-review skill."""
import re
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills" / "agent-review"


def test_skill_md_exists():
    assert (SKILL_ROOT / "SKILL.md").exists()


def test_skill_name_matches_directory():
    content = (SKILL_ROOT / "SKILL.md").read_text()
    assert re.search(r"^name:\s*agent-review\s*$", content, re.MULTILINE), (
        "SKILL.md frontmatter name must be 'agent-review'"
    )


def test_references_readme_exists():
    assert (SKILL_ROOT / "references" / "README.md").exists()


def test_agent_spec_exists():
    assert (SKILL_ROOT / "references" / "agent-spec.md").exists()


def test_agent_spec_has_tools_list():
    content = (SKILL_ROOT / "references" / "agent-spec.md").read_text()
    for tool in ["read", "bash", "edit", "write", "grep", "find", "ls"]:
        assert tool in content, f"agent-spec.md must list valid tool: {tool}"


def test_rubric_exists():
    assert (SKILL_ROOT / "references" / "rubric.md").exists()


def test_rubric_covers_all_dimensions():
    content = (SKILL_ROOT / "references" / "rubric.md").read_text()
    dimensions = [
        "Frontmatter",
        "身份",
        "输入",
        "工作流",
        "输出",
        "失败",
        "Guardrail",
        "工具",
    ]
    for dim in dimensions:
        assert dim in content, f"rubric.md must cover dimension: {dim}"


def test_skill_md_no_relative_script_calls():
    content = (SKILL_ROOT / "SKILL.md").read_text()
    assert not re.search(r"\b(bash|python|node)\s+scripts/", content), (
        "SKILL.md must not call scripts via relative paths"
    )
