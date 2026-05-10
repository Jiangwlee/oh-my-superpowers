"""T1 测试：scripts/inventory.py — 四类归类。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "skills" / "docs-contract")
)

from scripts.inventory import (  # noqa: E402
    ALL_CATEGORIES,
    MANAGED,
    SKIPPED,
    SUGGESTED,
    UNMANAGED,
    inventory,
)
from scripts.scaffold import apply as apply_scaffold, plan as build_plan  # noqa: E402
from scripts.schema import DocType  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3]
ASSETS_DIR = REPO_ROOT / "skills" / "docs-contract" / "assets"


def _scaffold(tmp_path: Path) -> None:
    apply_scaffold(build_plan(tmp_path, ASSETS_DIR))


def _by_doctype(report) -> dict[DocType, str]:
    return {e.doc_type: e.category for e in report.entries}


# ---------------------------------------------------------------------------
# Categories enumerated
# ---------------------------------------------------------------------------


def test_all_categories_constant_has_four_members() -> None:
    assert set(ALL_CATEGORIES) == {MANAGED, UNMANAGED, SUGGESTED, SKIPPED}


# ---------------------------------------------------------------------------
# Empty project
# ---------------------------------------------------------------------------


def test_empty_project_classifies_core_as_suggested(tmp_path: Path) -> None:
    cats = _by_doctype(inventory(tmp_path))
    for dt in (DocType.PROJECT, DocType.LANGUAGE, DocType.PRODUCT, DocType.ARCHITECTURE):
        assert cats[dt] == SUGGESTED


def test_empty_project_classifies_unsignaled_extensions_as_skipped(tmp_path: Path) -> None:
    cats = _by_doctype(inventory(tmp_path))
    for dt in (DocType.DESIGN, DocType.CONTRACT, DocType.PROCEDURE, DocType.CONCEPT):
        assert cats[dt] == SKIPPED


# ---------------------------------------------------------------------------
# Scaffolded project
# ---------------------------------------------------------------------------


def test_scaffolded_project_classifies_core_as_managed(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    cats = _by_doctype(inventory(tmp_path))
    for dt in (DocType.PROJECT, DocType.LANGUAGE, DocType.PRODUCT, DocType.ARCHITECTURE):
        assert cats[dt] == MANAGED


# ---------------------------------------------------------------------------
# Unmanaged: file exists without frontmatter
# ---------------------------------------------------------------------------


def test_existing_md_without_frontmatter_is_unmanaged(tmp_path: Path) -> None:
    (tmp_path / "PROJECT.md").write_text("# Hand-written\n", encoding="utf-8")
    cats = _by_doctype(inventory(tmp_path))
    assert cats[DocType.PROJECT] == UNMANAGED


def test_existing_md_with_wrong_doctype_is_unmanaged(tmp_path: Path) -> None:
    (tmp_path / "PROJECT.md").write_text(
        "---\ndoc-type: language\npurpose: x\nmust-not-contain: []\n---\n",
        encoding="utf-8",
    )
    cats = _by_doctype(inventory(tmp_path))
    assert cats[DocType.PROJECT] == UNMANAGED


def test_existing_md_with_invalid_frontmatter_is_unmanaged(tmp_path: Path) -> None:
    (tmp_path / "PROJECT.md").write_text(
        "---\ndoc-type: project\nfoobar: 1\n---\n",
        encoding="utf-8",
    )
    cats = _by_doctype(inventory(tmp_path))
    assert cats[DocType.PROJECT] == UNMANAGED


# ---------------------------------------------------------------------------
# by_category helper
# ---------------------------------------------------------------------------


def test_by_category_returns_filtered_entries(tmp_path: Path) -> None:
    _scaffold(tmp_path)
    report = inventory(tmp_path)
    managed_entries = report.by_category(MANAGED)
    assert len(managed_entries) >= 4
    assert all(e.category == MANAGED for e in managed_entries)


# ---------------------------------------------------------------------------
# Mixed real-ish project
# ---------------------------------------------------------------------------


def test_mixed_project_returns_each_category(tmp_path: Path) -> None:
    # Make it a frontend project (predicts DESIGN + UI as suggested)
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"react": "^18.0.0"}}', encoding="utf-8"
    )
    # Hand-written docs without frontmatter (UNMANAGED)
    (tmp_path / "PROJECT.md").write_text("# Existing project\n", encoding="utf-8")
    # Properly managed doc
    (tmp_path / "LANGUAGE.md").write_text(
        "---\ndoc-type: language\npurpose: terms\nmust-not-contain: []\n---\nbody\n",
        encoding="utf-8",
    )

    report = inventory(tmp_path)
    cats = _by_doctype(report)
    # PROJECT exists w/o frontmatter -> unmanaged
    assert cats[DocType.PROJECT] == UNMANAGED
    # LANGUAGE proper -> managed
    assert cats[DocType.LANGUAGE] == MANAGED
    # PRODUCT predicted, missing -> suggested
    assert cats[DocType.PRODUCT] == SUGGESTED
    # DESIGN predicted (frontend signal) and missing -> suggested
    assert cats[DocType.DESIGN] == SUGGESTED
    # CONTRACT not signaled, not present -> skipped
    assert cats[DocType.CONTRACT] == SKIPPED
