"""Parse YAML frontmatter from markdown files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


_DELIM = "---"


class FrontmatterError(ValueError):
    """Raised when frontmatter is malformed or YAML-invalid."""


def split_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    """Split markdown text into (frontmatter dict, body).

    Returns (None, text) if the file does not begin with a frontmatter delimiter.
    Raises FrontmatterError when the delimiter is opened but not closed, when
    YAML is malformed, or when the parsed value is not a mapping.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != _DELIM:
        return None, text

    end_idx: int | None = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == _DELIM:
            end_idx = i
            break

    if end_idx is None:
        raise FrontmatterError("frontmatter opened but not closed")

    yaml_text = "".join(lines[1:end_idx])
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"YAML parse error: {exc}") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise FrontmatterError(
            f"frontmatter must be a mapping, got {type(data).__name__}"
        )

    body = "".join(lines[end_idx + 1 :])
    return data, body


def read_frontmatter(path: Path) -> tuple[dict[str, Any] | None, str]:
    """Read a file and split its frontmatter.

    Args:
        path: Markdown file to read.

    Returns:
        (frontmatter dict or None, body text).
    """
    return split_frontmatter(path.read_text(encoding="utf-8"))
