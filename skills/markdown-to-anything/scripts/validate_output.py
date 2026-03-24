#!/usr/bin/env python3
"""Basic output validator for markdown-to-anything."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PDF_SIGNATURE = b"%PDF"


@dataclass(slots=True)
class ValidateResult:
    ok: bool
    path: str
    kind: str
    size_bytes: int
    warnings: list[str]
    errors: list[str]


def validate_file(path: Path) -> ValidateResult:
    warnings: list[str] = []
    errors: list[str] = []
    if not path.exists():
        return ValidateResult(False, str(path), path.suffix.lstrip("."), 0, [], ["file does not exist"])

    size = path.stat().st_size
    kind = path.suffix.lower().lstrip(".")
    data = path.read_bytes()[:16]

    if size == 0:
        errors.append("file is empty")
    elif size < 1024:
        warnings.append("file is very small; output may be invalid")

    if kind == "png" and not data.startswith(PNG_SIGNATURE):
        errors.append("invalid PNG signature")
    if kind == "pdf" and not data.startswith(PDF_SIGNATURE):
        errors.append("invalid PDF signature")

    return ValidateResult(not errors, str(path), kind, size, warnings, errors)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate exported markdown-to-anything output")
    parser.add_argument("input", help="Output file to validate")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args()

    result = validate_file(Path(args.input).expanduser())
    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False))
    else:
        print(result.path)

    if not result.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
