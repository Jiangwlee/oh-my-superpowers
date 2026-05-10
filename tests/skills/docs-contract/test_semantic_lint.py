"""T1 测试：scripts/semantic_lint.py 与 lint.py 的 L3 入口。

LLM 调用通过依赖注入用 fake 替代，不会启动真实 runtime。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "skills" / "docs-contract")
)

from scripts.lint import lint_l3, lint_with_semantic  # noqa: E402
from scripts.scaffold import apply as apply_scaffold, plan as build_plan  # noqa: E402
from scripts.semantic_lint import (  # noqa: E402
    HOW_LEAK_CATEGORY,
    SemanticFinding,
    build_prompt,
    parse_response,
    resolve_model,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
ASSETS_DIR = REPO_ROOT / "skills" / "docs-contract" / "assets"


def _scaffold(tmp_path: Path) -> None:
    apply_scaffold(build_plan(tmp_path, ASSETS_DIR))


def _fake_llm_returning(payload: str):
    def _fake(prompt: str, model: str | None, timeout: int) -> str:
        return payload
    return _fake


def _fake_llm_raising(exc_type: type[Exception]):
    def _fake(prompt: str, model: str | None, timeout: int) -> str:
        raise exc_type("simulated")
    return _fake


# ---------------------------------------------------------------------------
# build_prompt
# ---------------------------------------------------------------------------


def test_build_prompt_embeds_path_doctype_and_body() -> None:
    prompt = build_prompt(Path("/x/PROJECT.md"), "project", "# Body content\n")
    assert "/x/PROJECT.md" in prompt
    assert "Doc-type: project" in prompt
    assert "# Body content" in prompt
    assert "What" in prompt and "Why" in prompt and "How" in prompt


# ---------------------------------------------------------------------------
# parse_response
# ---------------------------------------------------------------------------


def test_parse_response_ndjson_returns_findings() -> None:
    file = Path("PROJECT.md")
    payload = (
        '{"line": 5, "category": "how-leak", "severity": "MEDIUM", '
        '"snippet": "调用 foo()", "suggestion": "移到代码"}\n'
        '{"line": 8, "category": "how-leak", "severity": "LOW", '
        '"snippet": "if x", "suggestion": "用What描述"}\n'
    )
    findings = parse_response(payload, file)
    assert len(findings) == 2
    assert findings[0].line == 5
    assert findings[0].severity == "MEDIUM"
    assert findings[1].severity == "LOW"


def test_parse_response_none_returns_empty() -> None:
    assert parse_response("NONE", Path("x.md")) == []
    assert parse_response("none", Path("x.md")) == []
    assert parse_response("  none  ", Path("x.md")) == []


def test_parse_response_skips_garbage_lines() -> None:
    payload = (
        "Some prose preamble\n"
        "```\n"
        '{"line": 1, "category": "how-leak", "severity": "MEDIUM", '
        '"snippet": "x", "suggestion": "y"}\n'
        "more garbage\n"
    )
    findings = parse_response(payload, Path("x.md"))
    assert len(findings) == 1


def test_parse_response_caps_snippet_length() -> None:
    payload = '{"line": 1, "category": "x", "severity": "MEDIUM", "snippet": "%s", "suggestion": "y"}' % ("z" * 500)
    findings = parse_response(payload, Path("x.md"))
    assert len(findings[0].snippet) <= 200


# ---------------------------------------------------------------------------
# resolve_model
# ---------------------------------------------------------------------------


def test_resolve_model_cli_override_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMP_DEFAULT_MODEL_PI", "env-model")
    assert resolve_model("cli-model", "cfg-model") == "cli-model"


def test_resolve_model_config_used_when_no_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMP_DEFAULT_MODEL_PI", "env-model")
    assert resolve_model(None, "cfg-model") == "cfg-model"


def test_resolve_model_env_used_when_no_cli_or_cfg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMP_DEFAULT_MODEL_PI", "env-model")
    assert resolve_model(None, None) == "env-model"


def test_resolve_model_returns_none_when_nothing_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMP_DEFAULT_MODEL_PI", raising=False)
    assert resolve_model(None, None) is None


def test_resolve_model_expands_env_placeholder_in_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMP_DEFAULT_MODEL_PI", "expanded-model")
    assert resolve_model(None, "${OMP_DEFAULT_MODEL_PI}") == "expanded-model"


# ---------------------------------------------------------------------------
# lint_l3 — happy path with injected LLM
# ---------------------------------------------------------------------------


def test_lint_l3_returns_findings_from_fake_llm(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    fake = _fake_llm_returning(
        '{"line": 3, "category": "how-leak", "severity": "MEDIUM", '
        '"snippet": "test snippet", "suggestion": "fix"}\n'
    )
    findings = lint_l3(tmp_path, llm=fake)
    assert len(findings) >= 1  # one per managed doc
    assert all(f.rule == "L3.how-leak" for f in findings)


def test_lint_l3_records_low_finding_on_llm_failure(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    findings = lint_l3(tmp_path, llm=_fake_llm_raising(RuntimeError))
    unavail = [f for f in findings if f.rule == "L3.unavailable"]
    assert len(unavail) >= 1
    assert all(f.severity == "LOW" for f in unavail)


def test_lint_l3_skips_when_llm_returns_none(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    findings = lint_l3(tmp_path, llm=_fake_llm_returning("NONE"))
    assert findings == []


# ---------------------------------------------------------------------------
# lint_with_semantic — combines L1 + L2 + L3
# ---------------------------------------------------------------------------


def test_lint_with_semantic_combines_layers(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    # Inject an L1 violation: misplaced doc
    misplaced = tmp_path / "wrong.md"
    misplaced.write_text(
        "---\ndoc-type: project\npurpose: x\nmust-not-contain: []\n---\nbody\n",
        encoding="utf-8",
    )
    findings = lint_with_semantic(
        tmp_path,
        llm=_fake_llm_returning("NONE"),
    )
    rules = [f.rule for f in findings]
    assert any(r == "L1.location.mismatch" for r in rules)
