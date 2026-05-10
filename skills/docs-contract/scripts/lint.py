"""docs-contract lint entry point.

Layer 1 (structural): frontmatter compliance, source-of-truth uniqueness,
defer-to link validity, doc-type/location matching, skeleton completeness.

Layer 2 (pattern) lands in PR3; layer 3 (semantic) lands in PR4.
"""

from __future__ import annotations

import fnmatch
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from scripts.frontmatter import FrontmatterError, read_frontmatter
from scripts.schema import (
    ContractBlock,
    ContractValidationError,
    DocType,
    parse,
)


@dataclass(frozen=True)
class Finding:
    severity: str             # CRITICAL | HIGH | MEDIUM | LOW
    file: Path | None         # absolute file path or None for project-level
    line: int | None          # 1-based line number or None
    rule: str                 # e.g. "L1.frontmatter.invalid"
    message: str


# Allowed file location for each doc-type, expressed as a path prefix
# relative to project root. Either an exact file path or a directory prefix.
DOCTYPE_LOCATIONS: dict[DocType, tuple[str, ...]] = {
    DocType.PROJECT: ("PROJECT.md",),
    DocType.LANGUAGE: ("LANGUAGE.md",),
    DocType.PRODUCT: ("PRODUCT.md",),
    DocType.DESIGN: ("DESIGN.md",),
    DocType.ARCHITECTURE: ("docs/architecture/architecture.md",),
    DocType.ADR: ("docs/architecture/decisions/",),
    DocType.UI: ("docs/architecture/ui/",),
    DocType.CONTRACT: ("docs/architecture/contracts/",),
    DocType.MODULE: ("docs/architecture/modules/",),
    DocType.PROCEDURE: ("docs/architecture/procedures/",),
    DocType.CLI: ("docs/architecture/cli/",),
    DocType.RELEASE: ("docs/architecture/release/",),
    DocType.CONCEPT: ("docs/architecture/concepts/",),
}

CORE_DOCTYPES: tuple[DocType, ...] = (
    DocType.PROJECT,
    DocType.LANGUAGE,
    DocType.PRODUCT,
    DocType.ARCHITECTURE,
)

_SKIP_DIRS: frozenset[str] = frozenset(
    {".git", "node_modules", ".venv", "__pycache__", "dist", "build", "stories"}
)


def lint_l1(
    project_root: Path,
    *,
    exempt_paths: tuple[str, ...] = (),
) -> list[Finding]:
    """Run L1 structural lint over all docs-contract managed files.

    Discovers files by reading frontmatter; files without ``doc-type`` are not
    lint targets. ``exempt_paths`` is a tuple of fnmatch globs (relative to
    project root) to skip.
    """
    findings: list[Finding] = []
    docs = _discover_docs(project_root, exempt_paths)
    sot_owners: dict[str, list[Path]] = defaultdict(list)

    for path, parsed in docs:
        if isinstance(parsed, Exception):
            findings.append(
                Finding(
                    severity="HIGH",
                    file=path,
                    line=None,
                    rule="L1.frontmatter.invalid",
                    message=str(parsed),
                )
            )
            continue

        rel = path.relative_to(project_root).as_posix()
        allowed = DOCTYPE_LOCATIONS.get(parsed.doc_type, ())
        if not any(rel == p or rel.startswith(p) for p in allowed):
            findings.append(
                Finding(
                    severity="HIGH",
                    file=path,
                    line=None,
                    rule="L1.location.mismatch",
                    message=(
                        f"doc-type {parsed.doc_type.value!r} expected under "
                        f"{list(allowed)!r}, found at {rel!r}"
                    ),
                )
            )

        for owner in parsed.source_of_truth_for:
            sot_owners[owner].append(path)

        for ref in parsed.defer_to:
            ref_path = (path.parent / ref).resolve()
            if not ref_path.exists():
                findings.append(
                    Finding(
                        severity="MEDIUM",
                        file=path,
                        line=None,
                        rule="L1.defer-to.broken",
                        message=f"defer-to target does not exist: {ref!r}",
                    )
                )

    for owner, owners in sot_owners.items():
        if len(owners) > 1:
            files_str = ", ".join(
                p.relative_to(project_root).as_posix() for p in owners
            )
            findings.append(
                Finding(
                    severity="CRITICAL",
                    file=None,
                    line=None,
                    rule="L1.sot.duplicate",
                    message=(
                        f"source-of-truth-for {owner!r} claimed by multiple "
                        f"files: {files_str}"
                    ),
                )
            )

    present_types = {
        block.doc_type for _, block in docs if isinstance(block, ContractBlock)
    }
    for required in CORE_DOCTYPES:
        if required not in present_types:
            target = DOCTYPE_LOCATIONS[required][0]
            findings.append(
                Finding(
                    severity="HIGH",
                    file=None,
                    line=None,
                    rule="L1.skeleton.missing",
                    message=(
                        f"core skeleton missing: doc-type {required.value!r} "
                        f"(expected at {target!r})"
                    ),
                )
            )

    return findings


def _discover_docs(
    project_root: Path,
    exempt_paths: tuple[str, ...],
) -> list[tuple[Path, ContractBlock | Exception]]:
    """Walk project for .md files carrying contract frontmatter."""
    results: list[tuple[Path, ContractBlock | Exception]] = []

    for md_path in _iter_markdown(project_root, exempt_paths):
        try:
            fm, _ = read_frontmatter(md_path)
        except FrontmatterError as exc:
            results.append((md_path, exc))
            continue
        if not fm or "doc-type" not in fm:
            continue
        try:
            block = parse(fm)
        except ContractValidationError as exc:
            results.append((md_path, exc))
            continue
        results.append((md_path, block))
    return results


def _iter_markdown(
    project_root: Path,
    exempt_paths: tuple[str, ...],
) -> Iterable[Path]:
    """Yield .md files under project_root, skipping common ignore dirs and exemptions."""
    for md in project_root.rglob("*.md"):
        rel = md.relative_to(project_root)
        if any(part in _SKIP_DIRS for part in rel.parts):
            continue
        rel_str = rel.as_posix()
        if any(fnmatch.fnmatch(rel_str, pattern) for pattern in exempt_paths):
            continue
        yield md
