"""T1 测试：scripts/detect.py — 项目特征探测与 doc-type 预测。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "skills" / "docs-contract")
)

from scripts.detect import (  # noqa: E402
    ProjectFeatures,
    detect,
    predict_doctypes,
)
from scripts.schema import DocType  # noqa: E402


def test_detect_empty_project(tmp_path: Path) -> None:
    features = detect(tmp_path)
    assert features == ProjectFeatures()


def test_detect_frontend_via_react_dependency(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"react": "^18.0.0"}}),
        encoding="utf-8",
    )
    assert detect(tmp_path).has_frontend is True


def test_detect_frontend_via_components_dir(tmp_path: Path) -> None:
    (tmp_path / "components").mkdir()
    assert detect(tmp_path).has_frontend is True


def test_detect_frontend_false_when_no_signal(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"lodash": "^4.0.0"}}),
        encoding="utf-8",
    )
    assert detect(tmp_path).has_frontend is False


def test_detect_openapi_via_openapi_yaml(tmp_path: Path) -> None:
    (tmp_path / "openapi.yaml").write_text("openapi: 3.0.0\n", encoding="utf-8")
    assert detect(tmp_path).has_openapi is True


def test_detect_openapi_via_proto(tmp_path: Path) -> None:
    (tmp_path / "schema.proto").write_text("syntax = \"proto3\";", encoding="utf-8")
    assert detect(tmp_path).has_openapi is True


def test_detect_cli_via_cli_dir(tmp_path: Path) -> None:
    cli_dir = tmp_path / "cli"
    cli_dir.mkdir()
    (cli_dir / "main.py").write_text("# noop", encoding="utf-8")
    assert detect(tmp_path).has_cli is True


def test_detect_cli_false_when_dir_empty(tmp_path: Path) -> None:
    (tmp_path / "cli").mkdir()
    assert detect(tmp_path).has_cli is False


def test_detect_changelog(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text("# 0.1.0\n", encoding="utf-8")
    assert detect(tmp_path).has_changelog is True


def test_detect_src_top_level_dirs(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    for name in ("a", "b", "c", "d"):
        (src / name).mkdir()
    (src / ".hidden").mkdir()
    assert detect(tmp_path).src_top_level_dirs == 4


def test_predict_core_layer_always_true() -> None:
    features = ProjectFeatures()
    pred = predict_doctypes(features)
    for dt in (
        DocType.PROJECT,
        DocType.LANGUAGE,
        DocType.PRODUCT,
        DocType.ARCHITECTURE,
        DocType.ADR,
    ):
        assert pred[dt] is True


def test_predict_extensions_off_by_default() -> None:
    features = ProjectFeatures()
    pred = predict_doctypes(features)
    for dt in (
        DocType.DESIGN,
        DocType.UI,
        DocType.CONTRACT,
        DocType.MODULE,
        DocType.CLI,
        DocType.RELEASE,
        DocType.PROCEDURE,
        DocType.CONCEPT,
    ):
        assert pred[dt] is False


def test_predict_design_and_ui_when_frontend() -> None:
    pred = predict_doctypes(ProjectFeatures(has_frontend=True))
    assert pred[DocType.DESIGN] is True
    assert pred[DocType.UI] is True


def test_predict_module_when_three_src_dirs() -> None:
    assert predict_doctypes(ProjectFeatures(src_top_level_dirs=3))[DocType.MODULE] is True
    assert predict_doctypes(ProjectFeatures(src_top_level_dirs=2))[DocType.MODULE] is False


def test_predict_release_via_changelog_or_tags() -> None:
    assert predict_doctypes(ProjectFeatures(has_changelog=True))[DocType.RELEASE] is True
    assert predict_doctypes(ProjectFeatures(git_tag_count=3))[DocType.RELEASE] is True
    assert predict_doctypes(ProjectFeatures(git_tag_count=2))[DocType.RELEASE] is False


def test_predict_procedure_and_concept_always_opt_in() -> None:
    pred = predict_doctypes(ProjectFeatures(has_frontend=True, has_openapi=True))
    assert pred[DocType.PROCEDURE] is False
    assert pred[DocType.CONCEPT] is False
