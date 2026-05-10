"""T1 测试：scripts/scaffold.py — plan + apply + skip-if-exists。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "skills" / "docs-contract")
)

from scripts.scaffold import (  # noqa: E402
    TARGET_PATHS,
    TEMPLATE_NAMES,
    apply as apply_scaffold,
    plan as build_plan,
)
from scripts.schema import DocType  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3]
ASSETS_DIR = REPO_ROOT / "skills" / "docs-contract" / "assets"


def test_target_and_template_maps_cover_all_doctypes() -> None:
    assert set(TARGET_PATHS) == set(DocType)
    assert set(TEMPLATE_NAMES) == set(DocType)


def test_plan_marks_core_layer_as_suggested(tmp_path: Path) -> None:
    plan_obj = build_plan(tmp_path, ASSETS_DIR)
    by_type = {e.doc_type: e for e in plan_obj.entries}
    for dt in (
        DocType.PROJECT,
        DocType.LANGUAGE,
        DocType.PRODUCT,
        DocType.ARCHITECTURE,
        DocType.ADR,
    ):
        assert by_type[dt].suggested is True


def test_plan_excludes_optional_when_no_signal(tmp_path: Path) -> None:
    plan_obj = build_plan(tmp_path, ASSETS_DIR)
    by_type = {e.doc_type: e for e in plan_obj.entries}
    for dt in (
        DocType.DESIGN,
        DocType.CONTRACT,
        DocType.CLI,
        DocType.RELEASE,
    ):
        assert by_type[dt].suggested is False


def test_plan_include_overrides_to_true(tmp_path: Path) -> None:
    plan_obj = build_plan(tmp_path, ASSETS_DIR, include=[DocType.DESIGN])
    by_type = {e.doc_type: e for e in plan_obj.entries}
    assert by_type[DocType.DESIGN].suggested is True


def test_plan_exclude_overrides_to_false(tmp_path: Path) -> None:
    plan_obj = build_plan(tmp_path, ASSETS_DIR, exclude=[DocType.LANGUAGE])
    by_type = {e.doc_type: e for e in plan_obj.entries}
    assert by_type[DocType.LANGUAGE].suggested is False


def test_apply_writes_suggested_files(tmp_path: Path) -> None:
    plan_obj = build_plan(tmp_path, ASSETS_DIR)
    written, skipped = apply_scaffold(plan_obj)
    assert (tmp_path / "PROJECT.md").is_file()
    assert (tmp_path / "LANGUAGE.md").is_file()
    assert (tmp_path / "PRODUCT.md").is_file()
    assert (tmp_path / "docs/architecture/architecture.md").is_file()
    assert (tmp_path / "docs/architecture/decisions/0000-template.md").is_file()
    assert skipped == []
    assert len(written) >= 5


def test_apply_skip_if_exists_default(tmp_path: Path) -> None:
    project = tmp_path / "PROJECT.md"
    project.write_text("# already here\n", encoding="utf-8")

    plan_obj = build_plan(tmp_path, ASSETS_DIR)
    written, skipped = apply_scaffold(plan_obj)
    assert project in skipped
    assert project.read_text(encoding="utf-8") == "# already here\n"


def test_apply_force_overwrites_existing(tmp_path: Path) -> None:
    project = tmp_path / "PROJECT.md"
    project.write_text("# stale\n", encoding="utf-8")

    plan_obj = build_plan(tmp_path, ASSETS_DIR)
    written, _ = apply_scaffold(plan_obj, force=True)
    assert project in written
    assert "doc-type: project" in project.read_text(encoding="utf-8")


def test_apply_does_not_write_unsuggested(tmp_path: Path) -> None:
    plan_obj = build_plan(tmp_path, ASSETS_DIR)
    apply_scaffold(plan_obj)
    assert not (tmp_path / "DESIGN.md").exists()
    assert not (tmp_path / "docs/architecture/contracts/.gitkeep").exists()


def test_apply_creates_dir_typed_gitkeep_when_suggested(tmp_path: Path) -> None:
    plan_obj = build_plan(tmp_path, ASSETS_DIR, include=[DocType.MODULE])
    apply_scaffold(plan_obj)
    assert (tmp_path / "docs/architecture/modules/.gitkeep").is_file()


def test_template_files_exist_for_every_template_name() -> None:
    """Each non-None TEMPLATE_NAMES entry must point at a real asset."""
    for dt, name in TEMPLATE_NAMES.items():
        if name is None:
            continue
        template_path = ASSETS_DIR / name
        assert template_path.is_file(), f"missing template for {dt.value}: {template_path}"
