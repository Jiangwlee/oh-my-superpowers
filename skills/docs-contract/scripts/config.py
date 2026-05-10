"""Load project-level docs-contract configuration.

Schema is forward-compatible: unknown top-level / nested keys produce warnings
but never errors. Malformed YAML or wrong root type is fatal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


CONFIG_PATH_REL = Path("docs/.docs-contract.yml")

_KNOWN_TOP_KEYS: frozenset[str] = frozenset(
    {"must_not_contain_extra", "exempt_paths", "semantic_lint"}
)
_KNOWN_SEMANTIC_KEYS: frozenset[str] = frozenset({"trigger", "model"})


@dataclass(frozen=True)
class SemanticLintConfig:
    trigger: str = "manual"          # "on-diff" | "manual"
    model: str | None = None         # may contain ${ENV} placeholders, expanded by L3 consumer


@dataclass(frozen=True)
class DocsContractConfig:
    must_not_contain_extra: dict[str, tuple[str, ...]] = field(default_factory=dict)
    exempt_paths: tuple[str, ...] = ()
    semantic_lint: SemanticLintConfig = field(default_factory=SemanticLintConfig)
    warnings: tuple[str, ...] = ()


def load(project_root: Path) -> DocsContractConfig:
    """Load docs-contract config from <project_root>/docs/.docs-contract.yml.

    Returns a default config when the file is absent.
    """
    path = project_root / CONFIG_PATH_REL
    if not path.is_file():
        return DocsContractConfig()

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"failed to parse {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError(
            f"{path}: top-level must be a mapping, got {type(raw).__name__}"
        )

    warnings: list[str] = []
    for key in sorted(set(raw) - _KNOWN_TOP_KEYS):
        warnings.append(f"unknown config key: {key!r} (ignored)")

    must_not_contain_extra: dict[str, tuple[str, ...]] = {}
    raw_extra = raw.get("must_not_contain_extra", {})
    if isinstance(raw_extra, dict):
        for filename, labels in raw_extra.items():
            if isinstance(labels, list):
                must_not_contain_extra[str(filename)] = tuple(str(x) for x in labels)
            else:
                warnings.append(
                    f"must_not_contain_extra[{filename!r}] must be a list (ignored)"
                )
    elif raw_extra:
        warnings.append("must_not_contain_extra must be a mapping (ignored)")

    exempt_raw = raw.get("exempt_paths", [])
    if isinstance(exempt_raw, list):
        exempt_paths = tuple(str(x) for x in exempt_raw)
    else:
        exempt_paths = ()
        if exempt_raw:
            warnings.append("exempt_paths must be a list (ignored)")

    semantic_raw = raw.get("semantic_lint", {})
    if isinstance(semantic_raw, dict):
        for key in sorted(set(semantic_raw) - _KNOWN_SEMANTIC_KEYS):
            warnings.append(f"unknown semantic_lint key: {key!r} (ignored)")
        trigger = str(semantic_raw.get("trigger", "manual"))
        raw_model = semantic_raw.get("model")
        model = str(raw_model) if raw_model else None
        semantic = SemanticLintConfig(trigger=trigger, model=model)
    else:
        semantic = SemanticLintConfig()
        if semantic_raw:
            warnings.append("semantic_lint must be a mapping (ignored)")

    return DocsContractConfig(
        must_not_contain_extra=must_not_contain_extra,
        exempt_paths=exempt_paths,
        semantic_lint=semantic,
        warnings=tuple(warnings),
    )
