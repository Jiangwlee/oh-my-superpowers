"""Inventory existing docs at the predicted skeleton paths.

Categorizes each doc-type's expected location into one of four buckets:

- managed   — file exists AND carries a contract block matching its doc-type
- unmanaged — file exists but lacks contract frontmatter (or the frontmatter
  fails schema validation); typical of MVP docs predating docs-contract
- suggested — predicted to be needed by feature detection but does not exist
- skipped   — not predicted and not present (no action required)

Inventory does NOT scan the whole repository; it only inspects the canonical
skeleton paths. Non-skeleton docs (README, CHANGELOG, LICENSE) are never
flagged as redundant by this report.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.detect import ProjectFeatures, detect, predict_doctypes
from scripts.frontmatter import FrontmatterError, read_frontmatter
from scripts.scaffold import TARGET_PATHS, TEMPLATE_NAMES
from scripts.schema import (
    ContractValidationError,
    DocType,
    parse,
)


# Categories — used as enum-like string constants for stable serialization.
MANAGED = "managed"
UNMANAGED = "unmanaged"
SUGGESTED = "suggested"
SKIPPED = "skipped"

ALL_CATEGORIES: tuple[str, ...] = (MANAGED, UNMANAGED, SUGGESTED, SKIPPED)


@dataclass(frozen=True)
class InventoryEntry:
    doc_type: DocType
    target: Path                # absolute path under project root
    category: str               # one of ALL_CATEGORIES
    detail: str = ""            # short reason / extra info


@dataclass(frozen=True)
class InventoryReport:
    project_root: Path
    features: ProjectFeatures
    entries: tuple[InventoryEntry, ...]

    def by_category(self, category: str) -> tuple[InventoryEntry, ...]:
        return tuple(e for e in self.entries if e.category == category)


def inventory(project_root: Path) -> InventoryReport:
    """Build an InventoryReport for the given project."""
    features = detect(project_root)
    suggestions = predict_doctypes(features)

    entries: list[InventoryEntry] = []
    for dt, default_target in TARGET_PATHS.items():
        target = project_root / default_target
        is_predicted = suggestions[dt]
        category, detail = _classify(dt, target)

        # If the slot is empty, downgrade to SUGGESTED only when prediction
        # said yes; else SKIPPED.
        if category == SUGGESTED and not is_predicted:
            category = SKIPPED
            detail = "not predicted, not present"

        entries.append(
            InventoryEntry(
                doc_type=dt,
                target=target,
                category=category,
                detail=detail,
            )
        )

    return InventoryReport(
        project_root=project_root,
        features=features,
        entries=tuple(entries),
    )


def _classify(dt: DocType, target: Path) -> tuple[str, str]:
    """Classify a single (doc-type, target) into (category, detail)."""
    template_name = TEMPLATE_NAMES[dt]
    if template_name is None:
        # directory-typed: presence = the directory has any non-dot file inside
        parent = target.parent
        if parent.is_dir() and any(
            child.name != ".gitkeep"
            and not child.name.startswith(".")
            for child in parent.iterdir()
        ):
            return UNMANAGED, "directory present (managed status not tracked)"
        if parent.is_dir():
            return UNMANAGED, "empty directory exists"
        return SUGGESTED, "directory missing"

    if not target.is_file():
        return SUGGESTED, "missing"

    # File exists — check frontmatter
    try:
        fm, _ = read_frontmatter(target)
    except FrontmatterError as exc:
        return UNMANAGED, f"frontmatter unparsable: {exc}"

    if not fm or "doc-type" not in fm:
        return UNMANAGED, "exists without contract frontmatter"

    try:
        block = parse(fm)
    except ContractValidationError as exc:
        return UNMANAGED, f"frontmatter fails schema: {exc}"

    if block.doc_type is not dt:
        return UNMANAGED, (
            f"doc-type mismatch: expected {dt.value!r}, got {block.doc_type.value!r}"
        )

    return MANAGED, "managed"
