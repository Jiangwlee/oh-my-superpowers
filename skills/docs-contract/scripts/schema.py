"""docs-contract frontmatter schema — single source of truth.

Lint, default rules, and template generators all import DocType / parse() from
this module. Do not duplicate the enum or field list elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DocType(str, Enum):
    """Canonical doc-type vocabulary used across the skeleton."""

    PROJECT = "project"
    LANGUAGE = "language"
    PRODUCT = "product"
    DESIGN = "design"
    ARCHITECTURE = "architecture"
    MODULE = "module"
    PROCEDURE = "procedure"
    CONTRACT = "contract"
    ADR = "adr"
    UI = "ui"
    CLI = "cli"
    RELEASE = "release"
    CONCEPT = "concept"


REQUIRED_FIELDS: tuple[str, ...] = ("doc-type", "purpose", "must-not-contain")
OPTIONAL_FIELDS: tuple[str, ...] = (
    "must-contain",
    "update-when",
    "source-of-truth-for",
    "defer-to",
)
ALL_FIELDS: tuple[str, ...] = REQUIRED_FIELDS + OPTIONAL_FIELDS


@dataclass(frozen=True)
class ContractBlock:
    """Parsed and validated frontmatter contract block."""

    doc_type: DocType
    purpose: str
    must_not_contain: tuple[str, ...]
    must_contain: tuple[str, ...] = ()
    update_when: tuple[str, ...] = ()
    source_of_truth_for: tuple[str, ...] = ()
    defer_to: tuple[str, ...] = ()


class ContractValidationError(ValueError):
    """Raised when a frontmatter mapping fails contract schema validation."""


def parse(mapping: dict[str, Any]) -> ContractBlock:
    """Validate and parse a YAML frontmatter mapping into a ContractBlock.

    Args:
        mapping: Raw frontmatter dict (already parsed from YAML).

    Returns:
        Validated ContractBlock with normalized list fields.

    Raises:
        ContractValidationError: 任何字段缺失、类型错或 doc-type 未知。
    """
    if not isinstance(mapping, dict):
        raise ContractValidationError(
            f"frontmatter must be a mapping, got {type(mapping).__name__}"
        )

    missing = [f for f in REQUIRED_FIELDS if f not in mapping]
    if missing:
        raise ContractValidationError(f"missing required fields: {missing}")

    unknown = [f for f in mapping if f not in ALL_FIELDS]
    if unknown:
        raise ContractValidationError(f"unknown fields: {unknown}")

    raw_type = mapping["doc-type"]
    try:
        doc_type = DocType(raw_type)
    except ValueError as exc:
        valid = [d.value for d in DocType]
        raise ContractValidationError(
            f"unknown doc-type {raw_type!r}; valid: {valid}"
        ) from exc

    purpose = mapping["purpose"]
    if not isinstance(purpose, str) or not purpose.strip():
        raise ContractValidationError("purpose must be a non-empty string")

    return ContractBlock(
        doc_type=doc_type,
        purpose=purpose.strip(),
        must_not_contain=_to_str_tuple(mapping["must-not-contain"], "must-not-contain"),
        must_contain=_to_str_tuple(mapping.get("must-contain", []), "must-contain"),
        update_when=_to_str_tuple(mapping.get("update-when", []), "update-when"),
        source_of_truth_for=_to_str_tuple(
            mapping.get("source-of-truth-for", []), "source-of-truth-for"
        ),
        defer_to=_to_str_tuple(mapping.get("defer-to", []), "defer-to"),
    )


def _to_str_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ContractValidationError(f"{field_name} must be a list")
    for item in value:
        if not isinstance(item, str):
            raise ContractValidationError(
                f"{field_name} items must be strings, got {type(item).__name__}"
            )
    return tuple(value)
