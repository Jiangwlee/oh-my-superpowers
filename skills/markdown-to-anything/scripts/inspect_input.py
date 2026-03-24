#!/usr/bin/env python3
"""Inspect markdown input cleanliness for markdown-to-anything."""

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
class InspectResult:
    ok: bool
    kind: str
    cleanliness: str
    signals: dict[str, bool]
    recommended_path: str
    warnings: list[str]
    errors: list[str]


def inspect_markdown_text(text: str) -> InspectResult:
    stripped = text.strip()
    if not stripped:
        return InspectResult(False, "unknown", "invalid", {}, "stop", [], ["input is empty"])

    has_fenced_markdown = bool(re.search(r"```(?:markdown|md)?\s*\n", text, flags=re.IGNORECASE))
    head = "\n".join(text.splitlines()[:12])
    has_assistant_preamble = any(token in head for token in ASSISTANT_PREAMBLE_PATTERNS)
    has_heading = any(line.lstrip().startswith("#") for line in text.splitlines())
    has_markdown_signals = has_heading or "|" in text or "- " in text or "```" in text

    needs_agent_cleanup = False
    if has_assistant_preamble and not has_heading and not has_fenced_markdown:
        needs_agent_cleanup = True

    if needs_agent_cleanup:
        cleanliness = "semantic_dirty"
        recommended_path = "agent_cleanup_first"
    elif has_fenced_markdown or has_assistant_preamble:
        cleanliness = "light_dirty"
        recommended_path = "normalize_then_render"
    else:
        cleanliness = "clean"
        recommended_path = "render_direct"

    return InspectResult(
        ok=True,
        kind="markdown" if has_markdown_signals else "text",
        cleanliness=cleanliness,
        signals={
            "has_fenced_markdown": has_fenced_markdown,
            "has_assistant_preamble": has_assistant_preamble,
            "has_heading": has_heading,
            "needs_agent_cleanup": needs_agent_cleanup,
        },
        recommended_path=recommended_path,
        warnings=[] if has_markdown_signals else ["input has weak markdown signals"],
        errors=[],
    )


def inspect_markdown_file(path: Path) -> InspectResult:
    return inspect_markdown_text(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect markdown input")
    parser.add_argument("input", help="Input markdown file")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args()

    result = inspect_markdown_file(Path(args.input).expanduser())
    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False))
    else:
        print(result.cleanliness)

    if not result.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
