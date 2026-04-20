#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer"]
# ///
"""omp handoff — Context handoff helpers for compaction lifecycle.

Commands:
  check         PreCompact hook: block if .handover.md missing
  mark-pending  PostCompact hook: set pending=true in .handover.md
  restore       UserPromptSubmit hook: inject .handover.md if pending=true
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="handoff",
    help="Context handoff helpers for compaction lifecycle.",
    no_args_is_help=True,
    add_completion=False,
)

HANDOVER_FILE = ".handover.md"


def _handover_path(source: str) -> Path:
    """Return the absolute path to .handover.md under source."""
    return Path(source) / HANDOVER_FILE


def _parse_frontmatter(text: str) -> tuple[dict[str, str | bool | int], str]:
    """Parse YAML frontmatter from a markdown string.

    Args:
        text: Raw file content starting with optional ---...--- block.

    Returns:
        Tuple of (meta dict, body string). meta is empty if no frontmatter found.
        Supports bool, int, and string values.
    """
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm_lines = text[4:end].splitlines()
    body = text[end + 5:]
    meta: dict[str, str | bool | int] = {}
    for line in fm_lines:
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        val = raw.strip().strip('"').strip("'")
        if val.lower() == "true":
            meta[key.strip()] = True
        elif val.lower() == "false":
            meta[key.strip()] = False
        else:
            try:
                meta[key.strip()] = int(val)
            except ValueError:
                meta[key.strip()] = val
    return meta, body


def _serialize(meta: dict[str, str | bool | int], body: str) -> str:
    """Serialize meta dict + body back to frontmatter markdown.

    Args:
        meta: Ordered dict of frontmatter fields.
        body: Markdown body (everything after closing ---).

    Returns:
        Complete file content with frontmatter.
    """
    lines: list[str] = []
    for k, v in meta.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            lines.append(f"{k}: {v}")
    return "---\n" + "\n".join(lines) + "\n---\n" + body


@app.command()
def check(
    source: str = typer.Option(".", "--source", help="Project root directory."),
) -> None:
    """PreCompact hook: block compaction if .handover.md is missing."""
    if not _handover_path(source).exists():
        print(json.dumps(
            {
                "decision": "block",
                "reason": (
                    "No .handover.md found. "
                    "Run /handoff to save context first, then /compact."
                ),
            },
            ensure_ascii=False,
        ))


@app.command(name="mark-pending")
def mark_pending(
    source: str = typer.Option(".", "--source", help="Project root directory."),
) -> None:
    """PostCompact hook: set pending=true in .handover.md frontmatter."""
    path = _handover_path(source)
    if not path.exists():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    meta, body = _parse_frontmatter(text)
    meta["pending"] = True
    path.write_text(_serialize(meta, body), encoding="utf-8")
    print(json.dumps(
        {"systemMessage": "📋 Handover marked — context will auto-restore on your next message."},
        ensure_ascii=False,
    ))


@app.command()
def restore(
    source: str = typer.Option(".", "--source", help="Project root directory."),
) -> None:
    """UserPromptSubmit hook: inject .handover.md content if pending=true, then clear flag."""
    path = _handover_path(source)
    if not path.exists():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    meta, body = _parse_frontmatter(text)
    if not meta.get("pending"):
        return
    meta["pending"] = False
    try:
        path.write_text(_serialize(meta, body), encoding="utf-8")
    except OSError:
        pass  # best-effort clear; still inject content
    print(json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": text,
            },
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    app()
