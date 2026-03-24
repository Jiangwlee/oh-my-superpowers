#!/usr/bin/env python3
"""Deterministic Markdown input normalizer for markdown-to-anything."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

ASSISTANT_PREAMBLE_PATTERNS = [
    "现在我已经读取了",
    "让我基于这些数据生成",
    "下面是我整理的",
    "下面进入设计阶段",
]


@dataclass(slots=True)
class NormalizeResult:
    ok: bool
    input: str
    output: str
    changed: bool
    text: str
    detected: dict[str, bool]
    actions: list[str]
    warnings: list[str]
    errors: list[str]


def _strip_bom(text: str) -> tuple[str, bool]:
    if text.startswith("\ufeff"):
        return text.lstrip("\ufeff"), True
    return text, False


def _normalize_newlines(text: str) -> tuple[str, bool]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized, normalized != text


def _extract_fenced_markdown(text: str) -> tuple[str, bool]:
    match = re.search(r"```(?:markdown|md)?\s*\n([\s\S]*?)\n```", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip("\n") + "\n", True
    return text, False


def _trim_to_first_heading(text: str) -> tuple[str, bool]:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            trimmed = "\n".join(lines[idx:]).strip() + "\n"
            return trimmed, idx > 0
    return text, False


def _looks_like_assistant_preamble(text: str) -> bool:
    head = "\n".join(text.splitlines()[:8])
    return any(token in head for token in ASSISTANT_PREAMBLE_PATTERNS)


def normalize_markdown_text(text: str) -> NormalizeResult:
    original = text
    actions: list[str] = []
    warnings: list[str] = []

    text, had_bom = _strip_bom(text)
    if had_bom:
        actions.append("removed_bom")

    text, newline_changed = _normalize_newlines(text)
    if newline_changed:
        actions.append("normalized_newlines")

    detected_fence = bool(re.search(r"```(?:markdown|md)?\s*\n", text, flags=re.IGNORECASE))
    text, extracted_fence = _extract_fenced_markdown(text)
    if extracted_fence:
        actions.append("extracted_fenced_markdown")

    detected_preamble = _looks_like_assistant_preamble(text)
    if detected_preamble and not extracted_fence:
        text, trimmed = _trim_to_first_heading(text)
        if trimmed:
            actions.append("removed_assistant_preamble")

    stripped = text.strip()
    if stripped != text:
        text = stripped + "\n"
        actions.append("trimmed_outer_whitespace")

    if not stripped:
        warnings.append("normalized markdown is empty")

    detected = {
        "bom": had_bom,
        "fenced_markdown": detected_fence,
        "assistant_preamble": detected_preamble,
    }
    return NormalizeResult(
        ok=bool(stripped),
        input="",
        output="",
        changed=text != original,
        text=text,
        detected=detected,
        actions=actions,
        warnings=warnings,
        errors=[] if stripped else ["empty markdown after normalization"],
    )


def normalize_markdown_file(input_path: Path, output_path: Path) -> NormalizeResult:
    text = input_path.read_text(encoding="utf-8")
    result = normalize_markdown_text(text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.text, encoding="utf-8")
    return NormalizeResult(
        ok=result.ok,
        input=str(input_path),
        output=str(output_path),
        changed=result.changed,
        text=result.text,
        detected=result.detected,
        actions=result.actions,
        warnings=result.warnings,
        errors=result.errors,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize Markdown input")
    parser.add_argument("input", help="Input markdown file")
    parser.add_argument("--output", required=True, help="Output clean markdown file")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args()

    result = normalize_markdown_file(Path(args.input).expanduser(), Path(args.output).expanduser())
    payload = asdict(result)
    payload.pop("text", None)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(result.output)

    if not result.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
