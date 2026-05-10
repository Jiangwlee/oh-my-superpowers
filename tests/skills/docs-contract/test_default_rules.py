"""T1 测试：scripts/default_rules.py — 每个 DocType 必须有规则映射。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "skills" / "docs-contract")
)

from scripts.default_rules import (  # noqa: E402
    DEFAULT_MUST_NOT_CONTAIN,
    KNOWN_PATTERN_LABELS,
    default_for,
)
from scripts.schema import DocType  # noqa: E402


@pytest.mark.parametrize("dt", list(DocType))
def test_every_doctype_has_default_entry(dt: DocType) -> None:
    assert dt in DEFAULT_MUST_NOT_CONTAIN, f"missing default for {dt}"


@pytest.mark.parametrize("dt", list(DocType))
def test_default_for_returns_tuple(dt: DocType) -> None:
    labels = default_for(dt)
    assert isinstance(labels, tuple)


def test_all_default_labels_are_known() -> None:
    for dt, labels in DEFAULT_MUST_NOT_CONTAIN.items():
        for label in labels:
            assert (
                label in KNOWN_PATTERN_LABELS
            ), f"{dt.value}: unknown pattern label {label!r}"


def test_known_pattern_labels_are_unique() -> None:
    assert len(set(KNOWN_PATTERN_LABELS)) == len(KNOWN_PATTERN_LABELS)


def test_adr_has_no_default_constraints() -> None:
    """ADR 是历史事实记录，默认不施加 must-not-contain。"""
    assert default_for(DocType.ADR) == ()
