"""T1 测试：scripts/config.py — .docs-contract.yml 加载与 forward-compat。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "skills" / "docs-contract")
)

from scripts.config import (  # noqa: E402
    CONFIG_PATH_REL,
    DocsContractConfig,
    SemanticLintConfig,
    load,
)


def _write_config(root: Path, content: str) -> None:
    cfg_path = root / CONFIG_PATH_REL
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(content, encoding="utf-8")


def test_load_returns_default_when_file_absent(tmp_path: Path) -> None:
    cfg = load(tmp_path)
    assert isinstance(cfg, DocsContractConfig)
    assert cfg.must_not_contain_extra == {}
    assert cfg.exempt_paths == ()
    assert cfg.semantic_lint == SemanticLintConfig()
    assert cfg.warnings == ()


def test_load_parses_full_config(tmp_path: Path) -> None:
    _write_config(
        tmp_path,
        "must_not_contain_extra:\n"
        "  PROJECT.md: [TODO, FIXME]\n"
        "exempt_paths:\n"
        "  - docs/architecture/archived/**\n"
        "semantic_lint:\n"
        "  trigger: on-diff\n"
        "  model: openai-codex/gpt-5.4-mini\n",
    )
    cfg = load(tmp_path)
    assert cfg.must_not_contain_extra == {"PROJECT.md": ("TODO", "FIXME")}
    assert cfg.exempt_paths == ("docs/architecture/archived/**",)
    assert cfg.semantic_lint.trigger == "on-diff"
    assert cfg.semantic_lint.model == "openai-codex/gpt-5.4-mini"
    assert cfg.warnings == ()


def test_load_warns_unknown_top_keys_does_not_error(tmp_path: Path) -> None:
    _write_config(tmp_path, "future_feature: 42\n")
    cfg = load(tmp_path)
    assert any("future_feature" in w for w in cfg.warnings)


def test_load_warns_unknown_semantic_keys(tmp_path: Path) -> None:
    _write_config(
        tmp_path,
        "semantic_lint:\n  trigger: manual\n  unknown: foo\n",
    )
    cfg = load(tmp_path)
    assert any("unknown" in w and "semantic_lint" in w for w in cfg.warnings)


def test_load_handles_must_not_contain_extra_wrong_value_type(tmp_path: Path) -> None:
    _write_config(tmp_path, "must_not_contain_extra:\n  PROJECT.md: not-a-list\n")
    cfg = load(tmp_path)
    assert "PROJECT.md" not in cfg.must_not_contain_extra
    assert any("must be a list" in w for w in cfg.warnings)


def test_load_rejects_malformed_yaml(tmp_path: Path) -> None:
    _write_config(tmp_path, "exempt_paths: [unclosed\n")
    with pytest.raises(ValueError, match="failed to parse"):
        load(tmp_path)


def test_load_rejects_non_mapping_root(tmp_path: Path) -> None:
    _write_config(tmp_path, "- a\n- b\n")
    with pytest.raises(ValueError, match="top-level must be a mapping"):
        load(tmp_path)
