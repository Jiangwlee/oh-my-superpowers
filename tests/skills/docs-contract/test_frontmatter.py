"""T1 测试：scripts/frontmatter.py — YAML frontmatter 解析。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "skills" / "docs-contract")
)

from scripts.frontmatter import (  # noqa: E402
    FrontmatterError,
    read_frontmatter,
    split_frontmatter,
)


def test_split_frontmatter_returns_dict_and_body() -> None:
    text = "---\ndoc-type: project\npurpose: foo\n---\n# Body\n"
    fm, body = split_frontmatter(text)
    assert fm == {"doc-type": "project", "purpose": "foo"}
    assert body == "# Body\n"


def test_split_frontmatter_no_delimiter_returns_none() -> None:
    fm, body = split_frontmatter("# No frontmatter here\n")
    assert fm is None
    assert body == "# No frontmatter here\n"


def test_split_frontmatter_empty_returns_none() -> None:
    fm, body = split_frontmatter("")
    assert fm is None
    assert body == ""


def test_split_frontmatter_unclosed_raises() -> None:
    with pytest.raises(FrontmatterError, match="not closed"):
        split_frontmatter("---\ndoc-type: project\n# never closed\n")


def test_split_frontmatter_invalid_yaml_raises() -> None:
    with pytest.raises(FrontmatterError, match="YAML parse"):
        split_frontmatter("---\nfoo: [unclosed\n---\n")


def test_split_frontmatter_non_mapping_raises() -> None:
    with pytest.raises(FrontmatterError, match="must be a mapping"):
        split_frontmatter("---\n- a\n- b\n---\nbody\n")


def test_split_frontmatter_empty_block_returns_empty_dict() -> None:
    fm, body = split_frontmatter("---\n---\nbody\n")
    assert fm == {}
    assert body == "body\n"


def test_read_frontmatter_round_trips(tmp_path: Path) -> None:
    p = tmp_path / "doc.md"
    p.write_text("---\nkey: value\n---\nhello\n", encoding="utf-8")
    fm, body = read_frontmatter(p)
    assert fm == {"key": "value"}
    assert body == "hello\n"
