"""T1 测试：scripts/lint.py L1 — 结构 lint。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "skills" / "docs-contract")
)

from scripts.lint import lint_l1  # noqa: E402
from scripts.scaffold import apply as apply_scaffold, plan as build_plan  # noqa: E402
from scripts.schema import DocType  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3]
ASSETS_DIR = REPO_ROOT / "skills" / "docs-contract" / "assets"


def _scaffold_clean_project(root: Path) -> None:
    """Generate a clean core-layer skeleton for testing."""
    plan_obj = build_plan(root, ASSETS_DIR)
    apply_scaffold(plan_obj)


def _write_doc(path: Path, frontmatter: str, body: str = "# Body\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_lint_clean_project_has_no_findings(tmp_path: Path) -> None:
    _scaffold_clean_project(tmp_path)
    findings = lint_l1(tmp_path)
    assert findings == []


def test_lint_skips_non_managed_md_files(tmp_path: Path) -> None:
    _scaffold_clean_project(tmp_path)
    (tmp_path / "README.md").write_text("# Readme without frontmatter\n", encoding="utf-8")
    findings = lint_l1(tmp_path)
    assert findings == []


# ---------------------------------------------------------------------------
# Skeleton completeness
# ---------------------------------------------------------------------------


def test_lint_reports_missing_core_skeleton(tmp_path: Path) -> None:
    findings = lint_l1(tmp_path)
    rules = {f.rule for f in findings}
    assert "L1.skeleton.missing" in rules
    missing_types = {f.message for f in findings if f.rule == "L1.skeleton.missing"}
    assert any("'project'" in m for m in missing_types)
    assert any("'language'" in m for m in missing_types)
    assert any("'product'" in m for m in missing_types)
    assert any("'architecture'" in m for m in missing_types)


# ---------------------------------------------------------------------------
# Frontmatter validation
# ---------------------------------------------------------------------------


def test_lint_reports_invalid_frontmatter(tmp_path: Path) -> None:
    _scaffold_clean_project(tmp_path)
    _write_doc(
        tmp_path / "PROJECT.md",
        "doc-type: not-a-real-type\npurpose: x\nmust-not-contain: []\n",
    )
    findings = lint_l1(tmp_path)
    rules = [f.rule for f in findings]
    assert "L1.frontmatter.invalid" in rules


# ---------------------------------------------------------------------------
# Location matching
# ---------------------------------------------------------------------------


def test_lint_reports_location_mismatch(tmp_path: Path) -> None:
    _scaffold_clean_project(tmp_path)
    misplaced = tmp_path / "wrong-place.md"
    _write_doc(
        misplaced,
        "doc-type: project\npurpose: x\nmust-not-contain: []\n",
    )
    findings = lint_l1(tmp_path)
    location_findings = [f for f in findings if f.rule == "L1.location.mismatch"]
    assert len(location_findings) >= 1
    assert any(f.file == misplaced for f in location_findings)


# ---------------------------------------------------------------------------
# SoT uniqueness
# ---------------------------------------------------------------------------


def test_lint_reports_sot_duplicate(tmp_path: Path) -> None:
    _scaffold_clean_project(tmp_path)
    # PROJECT.md already claims `项目身份` per template; add a second claimer
    _write_doc(
        tmp_path / "PRODUCT.md",
        "doc-type: product\npurpose: x\n"
        "must-not-contain: []\nsource-of-truth-for: [项目身份]\n",
    )
    findings = lint_l1(tmp_path)
    sot_findings = [f for f in findings if f.rule == "L1.sot.duplicate"]
    assert len(sot_findings) == 1
    assert sot_findings[0].severity == "CRITICAL"
    assert "项目身份" in sot_findings[0].message


def test_lint_allows_distinct_sots(tmp_path: Path) -> None:
    _scaffold_clean_project(tmp_path)
    findings = lint_l1(tmp_path)
    assert not any(f.rule == "L1.sot.duplicate" for f in findings)


# ---------------------------------------------------------------------------
# defer-to link validity
# ---------------------------------------------------------------------------


def test_lint_reports_broken_defer_to(tmp_path: Path) -> None:
    _scaffold_clean_project(tmp_path)
    # Overwrite architecture.md with a bad defer-to
    _write_doc(
        tmp_path / "docs/architecture/architecture.md",
        "doc-type: architecture\npurpose: x\nmust-not-contain: []\n"
        "defer-to: [decisions/, nonexistent-target.md]\n",
    )
    findings = lint_l1(tmp_path)
    broken = [f for f in findings if f.rule == "L1.defer-to.broken"]
    assert len(broken) == 1
    assert "nonexistent-target.md" in broken[0].message


# ---------------------------------------------------------------------------
# Exempt paths
# ---------------------------------------------------------------------------


def test_lint_respects_exempt_paths(tmp_path: Path) -> None:
    _scaffold_clean_project(tmp_path)
    archived = tmp_path / "docs/architecture/archived/old.md"
    _write_doc(
        archived,
        "doc-type: project\npurpose: stale\nmust-not-contain: []\n",
    )
    findings = lint_l1(
        tmp_path, exempt_paths=("docs/architecture/archived/**",)
    )
    assert not any(f.file == archived for f in findings)


# ---------------------------------------------------------------------------
# Discovery dir-skip
# ---------------------------------------------------------------------------


def test_lint_skips_node_modules_and_venv(tmp_path: Path) -> None:
    _scaffold_clean_project(tmp_path)
    bad_locations = (
        tmp_path / "node_modules" / "evil.md",
        tmp_path / ".venv" / "lib" / "evil.md",
        tmp_path / "stories" / "active" / "evil.md",
    )
    for bad in bad_locations:
        _write_doc(
            bad, "doc-type: project\npurpose: hidden\nmust-not-contain: []\n"
        )
    findings = lint_l1(tmp_path)
    for bad in bad_locations:
        assert not any(f.file == bad for f in findings)
