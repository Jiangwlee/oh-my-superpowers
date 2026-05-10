"""Default ``must-not-contain`` rule labels per DocType.

Keys are DocType members; values are tuples of pattern labels.
The lint L2 implementation (later PR) maps each label to a regex / AST check.
The template generator uses these labels to populate frontmatter defaults.

Users may extend per-file via ``docs/.docs-contract.yml``
(``must_not_contain_extra``); the loader merges, keeping unknown labels as
warnings (forward-compatible).
"""

from __future__ import annotations

from scripts.schema import DocType


DEFAULT_MUST_NOT_CONTAIN: dict[DocType, tuple[str, ...]] = {
    DocType.PROJECT: ("function-name", "file-path", "code-block", "step-verb"),
    DocType.LANGUAGE: ("function-name", "file-path", "code-block"),
    DocType.PRODUCT: ("function-name", "file-path", "code-block", "step-verb"),
    DocType.DESIGN: ("function-name", "step-verb"),
    DocType.ARCHITECTURE: ("function-name", "file-path", "code-block", "step-verb"),
    DocType.MODULE: ("function-name", "file-path", "step-verb"),
    DocType.PROCEDURE: ("function-name", "file-path"),
    DocType.CONTRACT: ("step-verb",),
    DocType.ADR: (),
    DocType.UI: ("function-name", "file-path"),
    DocType.CLI: ("function-name",),
    DocType.RELEASE: ("function-name", "code-block"),
    DocType.CONCEPT: ("function-name", "file-path", "code-block", "step-verb"),
}


KNOWN_PATTERN_LABELS: tuple[str, ...] = (
    "function-name",
    "file-path",
    "code-block",
    "step-verb",
)


def default_for(doc_type: DocType) -> tuple[str, ...]:
    """Return the default ``must-not-contain`` labels for a given DocType."""
    return DEFAULT_MUST_NOT_CONTAIN[doc_type]
