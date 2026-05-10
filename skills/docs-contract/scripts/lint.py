"""docs-contract lint entry point.

Layer 1 (structural): frontmatter compliance, source-of-truth uniqueness,
defer-to link validity, doc-type/location matching, skeleton completeness.

Layer 2 (pattern): per-document regex / AST scans of must-not-contain labels;
respects inline exemptions. Layer 3 (semantic) lands in PR4.
"""

from __future__ import annotations

import fnmatch
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from scripts.frontmatter import FrontmatterError, read_frontmatter
from scripts.patterns import (
    DETECTORS,
    Match,
    is_exempt,
    parse_exemptions,
)
from scripts.schema import (
    ContractBlock,
    ContractValidationError,
    DocType,
    parse,
)
from scripts.semantic_lint import (
    LLMCaller,
    build_prompt,
    call_pi_via_dispatch,
    changed_md_files,
    parse_response,
    resolve_model,
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


def lint_l2(
    project_root: Path,
    *,
    exempt_paths: tuple[str, ...] = (),
    must_not_contain_extra: dict[str, tuple[str, ...]] | None = None,
) -> list[Finding]:
    """Run L2 pattern lint over docs-contract managed files.

    Each document's ``must-not-contain`` labels (frontmatter + per-file
    extras from config) are checked. Inline exemption markers
    (``<!-- docs-contract: allow-<label> -->``) suppress findings within
    their paragraph scope.

    Unknown labels (not in ``patterns.DETECTORS``) are silently ignored;
    they may originate from forward-compat config and lint refuses to fail
    on them.
    """
    must_not_contain_extra = must_not_contain_extra or {}
    findings: list[Finding] = []

    for path, parsed in _discover_docs(project_root, exempt_paths):
        if not isinstance(parsed, ContractBlock):
            continue

        labels = list(parsed.must_not_contain)
        rel_name = path.relative_to(project_root).as_posix()
        for extra in (
            must_not_contain_extra.get(rel_name, ())
            or must_not_contain_extra.get(path.name, ())
        ):
            if extra not in labels:
                labels.append(extra)
        if not labels:
            continue

        try:
            _, body = read_frontmatter(path)
        except FrontmatterError:
            continue

        exemptions = parse_exemptions(body)

        for label in labels:
            detector = DETECTORS.get(label)
            if detector is None:
                continue
            for match in detector(body):
                if is_exempt(label, match.line, exemptions):
                    continue
                findings.append(
                    Finding(
                        severity="MEDIUM",
                        file=path,
                        line=match.line,
                        rule=f"L2.{label}",
                        message=f"{match.snippet} — {match.hint}",
                    )
                )

    return findings


def lint_all(
    project_root: Path,
    *,
    exempt_paths: tuple[str, ...] = (),
    must_not_contain_extra: dict[str, tuple[str, ...]] | None = None,
) -> list[Finding]:
    """Run L1 + L2 lint and return combined findings."""
    return [
        *lint_l1(project_root, exempt_paths=exempt_paths),
        *lint_l2(
            project_root,
            exempt_paths=exempt_paths,
            must_not_contain_extra=must_not_contain_extra,
        ),
    ]


def lint_l3(
    project_root: Path,
    *,
    exempt_paths: tuple[str, ...] = (),
    model: str | None = None,
    timeout: int = 300,
    only_changed: bool = False,
    llm: LLMCaller = call_pi_via_dispatch,
) -> list[Finding]:
    """Run L3 semantic lint (LLM-based) over docs-contract managed files.

    Args:
        project_root: Project root.
        exempt_paths: Glob patterns to skip.
        model: Override default model (else fall back to env / dispatch default).
        timeout: Seconds per LLM call.
        only_changed: If True and git diff is available, lint only changed .md files.
        llm: Injectable LLM caller — defaults to omp dispatch run pi.

    Returns Finding objects with rule ``L3.<category>`` (e.g. ``L3.how-leak``).
    LLM-call failures are recorded as a single LOW finding per file rather
    than aborting the run.
    """
    findings: list[Finding] = []
    docs = _discover_docs(project_root, exempt_paths)

    changed: set[Path] | None = None
    if only_changed:
        changed = changed_md_files(project_root)

    for path, parsed in docs:
        if not isinstance(parsed, ContractBlock):
            continue
        if changed is not None and path.resolve() not in changed:
            continue

        try:
            _, body = read_frontmatter(path)
        except FrontmatterError:
            continue

        prompt = build_prompt(path, parsed.doc_type.value, body)
        try:
            response = llm(prompt, model, timeout)
        except Exception as exc:  # noqa: BLE001 — degrade gracefully on any LLM error
            findings.append(
                Finding(
                    severity="LOW",
                    file=path,
                    line=None,
                    rule="L3.unavailable",
                    message=f"LLM call failed: {type(exc).__name__}",
                )
            )
            continue

        for sf in parse_response(response, path):
            severity = sf.severity if sf.severity in {"CRITICAL", "HIGH", "MEDIUM", "LOW"} else "MEDIUM"
            findings.append(
                Finding(
                    severity=severity,
                    file=sf.file,
                    line=sf.line,
                    rule=f"L3.{sf.category}",
                    message=f"{sf.snippet} — {sf.suggestion}",
                )
            )

    return findings


def lint_with_semantic(
    project_root: Path,
    *,
    exempt_paths: tuple[str, ...] = (),
    must_not_contain_extra: dict[str, tuple[str, ...]] | None = None,
    model: str | None = None,
    timeout: int = 300,
    only_changed: bool = False,
    llm: LLMCaller = call_pi_via_dispatch,
) -> list[Finding]:
    """Run L1 + L2 + L3 lint and return combined findings."""
    return [
        *lint_all(
            project_root,
            exempt_paths=exempt_paths,
            must_not_contain_extra=must_not_contain_extra,
        ),
        *lint_l3(
            project_root,
            exempt_paths=exempt_paths,
            model=model,
            timeout=timeout,
            only_changed=only_changed,
            llm=llm,
        ),
    ]


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
