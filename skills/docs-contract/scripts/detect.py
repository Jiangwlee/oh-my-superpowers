"""Detect project features to predict skeleton candidates."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scripts.schema import DocType


_FRONTEND_DEP_HINTS: tuple[str, ...] = (
    "react",
    "vue",
    "next",
    "svelte",
    "@angular/core",
    "solid-js",
    "nuxt",
    "remix",
)


@dataclass(frozen=True)
class ProjectFeatures:
    """Detected project features used to predict skeleton candidates."""

    has_frontend: bool = False
    has_openapi: bool = False
    has_cli: bool = False
    has_changelog: bool = False
    git_tag_count: int = 0
    src_top_level_dirs: int = 0


def detect(project_root: Path) -> ProjectFeatures:
    """Inspect the project root and return detected features.

    All checks are read-only; no command execution beyond a single `git tag` count.
    """
    return ProjectFeatures(
        has_frontend=_detect_frontend(project_root),
        has_openapi=_detect_openapi(project_root),
        has_cli=_detect_cli(project_root),
        has_changelog=_detect_changelog(project_root),
        git_tag_count=_count_git_tags(project_root),
        src_top_level_dirs=_count_src_top_level_dirs(project_root),
    )


def _detect_frontend(root: Path) -> bool:
    pkg_json = root / "package.json"
    if pkg_json.is_file():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        deps: dict[str, str] = {}
        deps.update(data.get("dependencies", {}) or {})
        deps.update(data.get("devDependencies", {}) or {})
        if any(name in deps for name in _FRONTEND_DEP_HINTS):
            return True
    for d in ("app", "components", "pages", "src/components", "src/pages"):
        if (root / d).is_dir():
            return True
    return False


def _detect_openapi(root: Path) -> bool:
    for name in ("openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.json"):
        if (root / name).is_file():
            return True
    # any .proto file at any depth (capped to first hit)
    for _ in root.rglob("*.proto"):
        return True
    # json-schema convention
    for _ in root.glob("schemas/*.json"):
        return True
    return False


def _detect_cli(root: Path) -> bool:
    for d in ("cli", "bin"):
        p = root / d
        if p.is_dir() and any(p.iterdir()):
            return True
    return False


def _detect_changelog(root: Path) -> bool:
    for name in ("CHANGELOG.md", "CHANGELOG", "CHANGELOG.rst", "HISTORY.md"):
        if (root / name).is_file():
            return True
    return False


def _count_git_tags(root: Path) -> int:
    if not (root / ".git").exists():
        return 0
    try:
        out = subprocess.run(
            ["git", "tag", "--list"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 0
    if out.returncode != 0:
        return 0
    return sum(1 for line in out.stdout.splitlines() if line.strip())


def _count_src_top_level_dirs(root: Path) -> int:
    src = root / "src"
    if not src.is_dir():
        return 0
    return sum(
        1
        for child in src.iterdir()
        if child.is_dir() and not child.name.startswith(".")
    )


def predict_doctypes(features: ProjectFeatures) -> dict[DocType, bool]:
    """Map detected features to doc-type recommendations.

    Core layer (PROJECT/LANGUAGE/PRODUCT/ARCHITECTURE/ADR) is always True.
    Extension layer is feature-driven.
    """
    return {
        DocType.PROJECT: True,
        DocType.LANGUAGE: True,
        DocType.PRODUCT: True,
        DocType.ARCHITECTURE: True,
        DocType.ADR: True,
        DocType.DESIGN: features.has_frontend,
        DocType.UI: features.has_frontend,
        DocType.CONTRACT: features.has_openapi,
        DocType.MODULE: features.src_top_level_dirs >= 3,
        DocType.PROCEDURE: False,
        DocType.CLI: features.has_cli,
        DocType.RELEASE: features.has_changelog or features.git_tag_count >= 3,
        DocType.CONCEPT: False,
    }
