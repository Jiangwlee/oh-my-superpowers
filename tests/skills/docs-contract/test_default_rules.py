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


# ---------------------------------------------------------------------------
# Templates ↔ default_rules consistency
# ---------------------------------------------------------------------------


def test_templates_must_not_contain_matches_default_rules() -> None:
    """Each shipped template's frontmatter must-not-contain must equal
    default_for(doc_type). Drift between templates and default_rules.py
    breaks the "single source of truth for label sets" intent.
    """
    import yaml  # noqa: PLC0415 — local import keeps test deps minimal

    from scripts.scaffold import TARGET_PATHS, TEMPLATE_NAMES  # noqa: PLC0415

    repo_root = Path(__file__).resolve().parents[3]
    assets_dir = repo_root / "skills" / "docs-contract" / "assets"

    drift: list[str] = []
    for dt in DocType:
        tmpl_name = TEMPLATE_NAMES[dt]
        if tmpl_name is None:
            continue  # directory-typed entries have no template
        tmpl_path = assets_dir / tmpl_name
        text = tmpl_path.read_text(encoding="utf-8")
        # Extract the YAML between the first two `---` lines
        parts = text.split("---", 2)
        if len(parts) < 3:
            drift.append(f"{tmpl_name}: missing frontmatter")
            continue
        fm = yaml.safe_load(parts[1]) or {}
        actual = tuple(fm.get("must-not-contain", []))
        expected = default_for(dt)
        if actual != expected:
            drift.append(f"{tmpl_name}: template={actual} default_rules={expected}")

    assert not drift, "templates drifted from default_rules:\n  " + "\n  ".join(drift)
