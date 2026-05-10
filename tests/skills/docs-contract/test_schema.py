"""T1 测试：scripts/schema.py 契约校验。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "skills" / "docs-contract")
)

from scripts.schema import (  # noqa: E402
    ALL_FIELDS,
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    ContractBlock,
    ContractValidationError,
    DocType,
    parse,
)


def _minimal(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "doc-type": "project",
        "purpose": "项目身份与开发约定的入口文档",
        "must-not-contain": ["function-name", "file-path"],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Schema invariants
# ---------------------------------------------------------------------------


def test_required_fields_are_three() -> None:
    assert REQUIRED_FIELDS == ("doc-type", "purpose", "must-not-contain")


def test_optional_fields_are_four() -> None:
    assert OPTIONAL_FIELDS == (
        "must-contain",
        "update-when",
        "source-of-truth-for",
        "defer-to",
    )


def test_all_fields_is_required_plus_optional() -> None:
    assert ALL_FIELDS == REQUIRED_FIELDS + OPTIONAL_FIELDS


def test_doctype_has_thirteen_members() -> None:
    assert len(list(DocType)) == 13


# ---------------------------------------------------------------------------
# parse() — happy paths
# ---------------------------------------------------------------------------


def test_parse_minimal_returns_contract_block() -> None:
    block = parse(_minimal())
    assert isinstance(block, ContractBlock)
    assert block.doc_type is DocType.PROJECT
    assert block.purpose == "项目身份与开发约定的入口文档"
    assert block.must_not_contain == ("function-name", "file-path")
    assert block.must_contain == ()
    assert block.update_when == ()
    assert block.source_of_truth_for == ()
    assert block.defer_to == ()


def test_parse_full_block_normalizes_lists_to_tuples() -> None:
    block = parse(
        _minimal(
            **{
                "must-contain": ["架构图"],
                "update-when": ["架构变更"],
                "source-of-truth-for": ["项目身份"],
                "defer-to": ["docs/architecture/architecture.md"],
            }
        )
    )
    assert block.must_contain == ("架构图",)
    assert block.update_when == ("架构变更",)
    assert block.source_of_truth_for == ("项目身份",)
    assert block.defer_to == ("docs/architecture/architecture.md",)


def test_parse_strips_purpose_whitespace() -> None:
    block = parse(_minimal(purpose="  项目身份  "))
    assert block.purpose == "项目身份"


@pytest.mark.parametrize("dt", list(DocType))
def test_parse_accepts_every_doctype(dt: DocType) -> None:
    block = parse(_minimal(**{"doc-type": dt.value}))
    assert block.doc_type is dt


# ---------------------------------------------------------------------------
# parse() — error paths
# ---------------------------------------------------------------------------


def test_parse_rejects_non_mapping_input() -> None:
    with pytest.raises(ContractValidationError, match="must be a mapping"):
        parse("not a dict")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "drop", ["doc-type", "purpose", "must-not-contain"]
)
def test_parse_rejects_missing_required(drop: str) -> None:
    raw = _minimal()
    raw.pop(drop)
    with pytest.raises(ContractValidationError, match="missing required fields"):
        parse(raw)


def test_parse_rejects_unknown_field() -> None:
    with pytest.raises(ContractValidationError, match="unknown fields"):
        parse(_minimal(unsupported="x"))


def test_parse_rejects_unknown_doctype() -> None:
    with pytest.raises(ContractValidationError, match="unknown doc-type"):
        parse(_minimal(**{"doc-type": "not-a-real-type"}))


@pytest.mark.parametrize("bad_purpose", ["", "   ", 42, None])
def test_parse_rejects_blank_or_non_string_purpose(bad_purpose: object) -> None:
    with pytest.raises(ContractValidationError, match="purpose must be"):
        parse(_minimal(purpose=bad_purpose))


@pytest.mark.parametrize(
    "field_name",
    ["must-not-contain", "must-contain", "update-when", "source-of-truth-for", "defer-to"],
)
def test_parse_rejects_non_list_for_list_fields(field_name: str) -> None:
    raw = _minimal(**{field_name: "not-a-list"})
    with pytest.raises(ContractValidationError, match=f"{field_name} must be a list"):
        parse(raw)


def test_parse_rejects_non_string_list_items() -> None:
    raw = _minimal(**{"must-not-contain": ["function-name", 123]})
    with pytest.raises(ContractValidationError, match="must be strings"):
        parse(raw)
