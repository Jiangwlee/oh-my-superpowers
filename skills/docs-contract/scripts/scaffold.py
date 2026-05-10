"""Scaffold project documentation skeleton from templates.

Inversion (predict candidates from project features) + Generator (write
templates with skip-if-exists default).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from scripts.detect import ProjectFeatures, detect, predict_doctypes
from scripts.schema import DocType


# Each doc-type's default target path under project root.
# For doc-types backed by a file template (PROJECT, LANGUAGE, ...) the path
# is the file. For directory-typed entries (UI, MODULE, ...) the path is a
# `.gitkeep` inside the directory so the empty dir survives in git.
TARGET_PATHS: dict[DocType, Path] = {
    DocType.PROJECT: Path("PROJECT.md"),
    DocType.LANGUAGE: Path("LANGUAGE.md"),
    DocType.PRODUCT: Path("PRODUCT.md"),
    DocType.DESIGN: Path("DESIGN.md"),
    DocType.ARCHITECTURE: Path("docs/architecture/architecture.md"),
    DocType.ADR: Path("docs/architecture/decisions/0000-template.md"),
    DocType.UI: Path("docs/architecture/ui/.gitkeep"),
    DocType.CONTRACT: Path("docs/architecture/contracts/.gitkeep"),
    DocType.MODULE: Path("docs/architecture/modules/.gitkeep"),
    DocType.PROCEDURE: Path("docs/architecture/procedures/.gitkeep"),
    DocType.CLI: Path("docs/architecture/cli/.gitkeep"),
    DocType.RELEASE: Path("docs/architecture/release/.gitkeep"),
    DocType.CONCEPT: Path("docs/architecture/concepts/.gitkeep"),
}

# Each doc-type's template name relative to assets/. None means directory-only
# (no template seed beyond .gitkeep).
TEMPLATE_NAMES: dict[DocType, str | None] = {
    DocType.PROJECT: "PROJECT.md.tmpl",
    DocType.LANGUAGE: "LANGUAGE.md.tmpl",
    DocType.PRODUCT: "PRODUCT.md.tmpl",
    DocType.DESIGN: "DESIGN.md.tmpl",
    DocType.ARCHITECTURE: "architecture.md.tmpl",
    DocType.ADR: "decisions/0000-template.md",
    DocType.UI: None,
    DocType.CONTRACT: None,
    DocType.MODULE: None,
    DocType.PROCEDURE: None,
    DocType.CLI: None,
    DocType.RELEASE: None,
    DocType.CONCEPT: None,
}


@dataclass(frozen=True)
class ScaffoldEntry:
    doc_type: DocType
    target: Path                  # absolute path under project root
    template: Path | None         # absolute path to template file, or None
    suggested: bool               # True if predicted or force-included
    exists: bool                  # True if target file or its parent dir exists


@dataclass(frozen=True)
class ScaffoldPlan:
    project_root: Path
    features: ProjectFeatures
    entries: tuple[ScaffoldEntry, ...]


def plan(
    project_root: Path,
    assets_dir: Path,
    *,
    include: Iterable[DocType] = (),
    exclude: Iterable[DocType] = (),
) -> ScaffoldPlan:
    """Build a scaffold plan: which entries are suggested, which already exist."""
    features = detect(project_root)
    suggestions = predict_doctypes(features)
    include_set = set(include)
    exclude_set = set(exclude)

    entries: list[ScaffoldEntry] = []
    for dt, default_target in TARGET_PATHS.items():
        is_suggested = suggestions[dt]
        if dt in exclude_set:
            is_suggested = False
        if dt in include_set:
            is_suggested = True
        target = project_root / default_target
        tmpl_name = TEMPLATE_NAMES[dt]
        template = (assets_dir / tmpl_name) if tmpl_name else None
        if tmpl_name is None:
            exists = target.parent.is_dir() and any(target.parent.iterdir())
        else:
            exists = target.exists()
        entries.append(
            ScaffoldEntry(
                doc_type=dt,
                target=target,
                template=template,
                suggested=is_suggested,
                exists=exists,
            )
        )

    return ScaffoldPlan(
        project_root=project_root,
        features=features,
        entries=tuple(entries),
    )


def apply(plan_obj: ScaffoldPlan, *, force: bool = False) -> tuple[list[Path], list[Path]]:
    """Apply a scaffold plan; return (written, skipped) absolute paths.

    Skip-if-exists is the default; pass ``force=True`` to overwrite. Directory-
    typed entries write a `.gitkeep` to seed the empty directory.
    """
    written: list[Path] = []
    skipped: list[Path] = []

    for entry in plan_obj.entries:
        if not entry.suggested:
            continue

        if entry.template is None:
            target_dir = entry.target.parent
            target_dir.mkdir(parents=True, exist_ok=True)
            if entry.target.exists() and not force:
                skipped.append(entry.target)
                continue
            entry.target.write_text("", encoding="utf-8")
            written.append(entry.target)
            continue

        if entry.target.exists() and not force:
            skipped.append(entry.target)
            continue
        entry.target.parent.mkdir(parents=True, exist_ok=True)
        entry.target.write_text(
            entry.template.read_text(encoding="utf-8"), encoding="utf-8"
        )
        written.append(entry.target)

    return written, skipped
