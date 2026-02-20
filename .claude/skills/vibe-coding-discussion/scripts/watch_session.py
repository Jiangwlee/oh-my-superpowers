#!/usr/bin/env python3
"""Watch a discussion session with TUI-style ANSI output and markdown rendering."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from common import ensure_layout, load_meta, read_jsonl, session_paths

# ---------------------------------------------------------------------------
# ANSI codes
# ---------------------------------------------------------------------------
R = "\033[0m"           # reset
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDER = "\033[4m"

# 256-color helpers
def _fg(n: int) -> str: return f"\033[38;5;{n}m"
def _bg(n: int) -> str: return f"\033[48;5;{n}m"

# Markdown element colors
_H1     = BOLD + _fg(33)   # bold bright blue
_H2     = BOLD + _fg(39)   # bold blue
_H3     = BOLD + _fg(45)   # bold cyan
_CODE_I = _bg(235) + _fg(220)   # inline code: dark bg, amber
_CODE_B = _bg(234) + _fg(252)   # code block: near-black bg, light grey
_RULE   = _fg(240)              # horizontal rule: dim grey
_BQUOTE = _fg(244)              # blockquote: mid grey
_BULL   = _fg(244)              # bullet/number: grey
_TBLSEP = _fg(238)              # table separator
_HL_KEY = BOLD + _fg(220)       # JSON key highlight

# Speaker badge colors (foreground)
_SPEAKER_COLORS: dict[str, str] = {
    "system":       DIM + _fg(244),
    "user":         BOLD + _fg(51),
    "codex":        BOLD + _fg(82),
    "claude-code":  BOLD + _fg(220),
    "opencode":     BOLD + _fg(141),
}

# Message type badge colors
_TYPE_COLORS: dict[str, str] = {
    "session_open": DIM + _fg(240),
    "comment":      _fg(252),
    "question":     _fg(227),
    "decision":     BOLD + _fg(120),
    "summary":      BOLD + _fg(81),
}

# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def _render_inline(text: str) -> str:
    """Apply inline markdown: bold, italic, inline-code, strikethrough."""
    text = re.sub(r'\*\*(.+?)\*\*', lambda m: f'{BOLD}{m.group(1)}{R}', text)
    text = re.sub(r'__(.+?)__',      lambda m: f'{BOLD}{m.group(1)}{R}', text)
    text = re.sub(
        r'(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)',
        lambda m: f'{ITALIC}{m.group(1)}{R}',
        text,
    )
    text = re.sub(r'(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)',
                  lambda m: f'{ITALIC}{m.group(1)}{R}', text)
    text = re.sub(r'`([^`\n]+)`',  lambda m: f'{_CODE_I} {m.group(1)} {R}', text)
    text = re.sub(r'~~(.+?)~~',    lambda m: f'{DIM}{m.group(1)}{R}', text)
    # Dim URLs/links
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', lambda m: f'{UNDER}{m.group(1)}{R}', text)
    return text


def render_markdown(text: str, indent: str = "  ", width: int = 76) -> str:
    """Render markdown to ANSI terminal string.

    Args:
        text: Raw markdown string.
        indent: Left-padding for every line.
        width: Content width (used for code-block background fill).

    Returns:
        ANSI-colored string ready for print().
    """
    lines = text.split("\n")
    out: list[str] = []
    in_code = False
    code_lang = ""
    fill_w = max(10, width - len(indent) - 2)

    for line in lines:
        # ── code fence ──────────────────────────────────────────────────────
        stripped_line = line.rstrip()
        if stripped_line.lstrip().startswith("```"):
            fence_content = stripped_line.lstrip()[3:].strip()
            if in_code:
                in_code = False
                out.append(f"{indent}{_fg(240)}└{'─' * (fill_w + 1)}{R}")
            else:
                in_code = True
                code_lang = fence_content
                label = f" {code_lang} " if code_lang else " code "
                dash_len = max(0, fill_w - len(label))
                out.append(f"{indent}{_fg(240)}┌─{label}{'─' * dash_len}{R}")
            continue

        if in_code:
            pad = fill_w - len(line)
            out.append(f"{indent}{_CODE_B}  {line}{' ' * max(0, pad)}{R}")
            continue

        # ── horizontal rule ────────────────────────────────────────────────
        if re.match(r'^[-*_]{3,}\s*$', stripped_line):
            out.append(f"{indent}{_RULE}{'─' * fill_w}{R}")
            continue

        # ── blockquote ─────────────────────────────────────────────────────
        bq_match = re.match(r'^(\s*)(>{1,}\s?)(.*)', stripped_line)
        if bq_match:
            inner = _render_inline(bq_match.group(3))
            out.append(f"{indent}{_BQUOTE}│ {inner}{R}")
            continue

        # ── headers ────────────────────────────────────────────────────────
        hdr = re.match(r'^(#{1,6})\s+(.*)', stripped_line)
        if hdr:
            level = len(hdr.group(1))
            content = _render_inline(hdr.group(2))
            raw_len = len(hdr.group(2))
            if level == 1:
                out.append(f"{indent}{_H1}{content}{R}")
                out.append(f"{indent}{_H1}{'═' * min(raw_len, fill_w)}{R}")
            elif level == 2:
                out.append(f"{indent}{_H2}{content}{R}")
                out.append(f"{indent}{_fg(39)}{'─' * min(raw_len, fill_w)}{R}")
            else:
                out.append(f"{indent}{_H3}{content}{R}")
            continue

        # ── table row ──────────────────────────────────────────────────────
        if re.match(r'^\s*\|', stripped_line):
            # separator row?
            if re.match(r'^[\s|:\-]+$', stripped_line):
                sep = _TBLSEP + "├" + "┼".join("─" * 10 for _ in stripped_line.split("|")[1:-1]) + "┤" + R
                out.append(f"{indent}{sep}")
            else:
                cells = stripped_line.strip("|").split("|")
                rendered = _TBLSEP + "│" + R
                for c in cells:
                    rendered += f" {_render_inline(c.strip())} {_TBLSEP}│{R}"
                out.append(f"{indent}{rendered}")
            continue

        # ── bullet list ────────────────────────────────────────────────────
        bl = re.match(r'^(\s*)[-*+]\s+(.*)', stripped_line)
        if bl:
            inner = _render_inline(bl.group(2))
            pad = bl.group(1)
            out.append(f"{indent}{pad}{_BULL}•{R} {inner}")
            continue

        # ── numbered list ──────────────────────────────────────────────────
        nl = re.match(r'^(\s*)(\d+)\.\s+(.*)', stripped_line)
        if nl:
            inner = _render_inline(nl.group(3))
            pad = nl.group(1)
            num = nl.group(2)
            out.append(f"{indent}{pad}{_BULL}{num}.{R} {inner}")
            continue

        # ── empty line ─────────────────────────────────────────────────────
        if not stripped_line:
            out.append("")
            continue

        # ── normal paragraph ───────────────────────────────────────────────
        out.append(f"{indent}{_render_inline(stripped_line)}")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Event rendering
# ---------------------------------------------------------------------------

def _ts_local(iso: str) -> str:
    """Convert UTC ISO to local HH:MM:SS string."""
    try:
        utc = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        local = utc.astimezone()
        return local.strftime("%H:%M:%S")
    except Exception:
        return iso[:8] if len(iso) >= 8 else iso


def _speaker_badge(speaker: str, width: int) -> str:
    """Return colored speaker badge string."""
    color = _SPEAKER_COLORS.get(speaker.lower(), BOLD + _fg(39))
    return f"{color}{speaker.upper()}{R}"


def _type_badge(msg_type: str) -> str:
    """Return colored message-type string."""
    color = _TYPE_COLORS.get(msg_type, _fg(252))
    return f"{color}{msg_type}{R}"


def _render_event(event: dict[str, Any], term_width: int) -> str:
    """Format one JSONL event as TUI block."""
    idx = event.get("index", "?")
    ts = _ts_local(event.get("timestamp", ""))
    speaker = str(event.get("speaker", "?"))
    msg_type = str(event.get("message_type", "comment"))
    message = str(event.get("message", ""))
    reply_to = event.get("reply_to_index")
    tags = event.get("tags") or []

    # ── header line ─────────────────────────────────────────────────────────
    spk_color = _SPEAKER_COLORS.get(speaker.lower(), BOLD + _fg(39))
    type_color = _TYPE_COLORS.get(msg_type, _fg(252))

    idx_str  = f"{DIM}#{idx}{R}"
    ts_str   = f"{_fg(240)}{ts}{R}"
    spk_str  = f"{spk_color}{speaker.upper()}{R}"
    type_str = f"{type_color}{msg_type}{R}"

    # fill the rest of the header line with dashes
    plain_header = f"  #{idx}  {ts}  {speaker.upper()}  {msg_type}"
    dash_count = max(2, term_width - len(plain_header) - 2)
    dash_str = f"{_fg(238)}{'─' * dash_count}{R}"

    header = f"  {idx_str}  {ts_str}  {spk_str}  {type_str}  {dash_str}"

    lines: list[str] = [header]

    # reply indicator
    if reply_to is not None:
        lines.append(f"  {_fg(240)}↩ reply to #{reply_to}{R}")

    # tags
    if tags:
        tag_str = "  ".join(f"{_fg(33)}#{t}{R}" for t in tags)
        lines.append(f"  {_fg(240)}tags: {tag_str}{R}")

    # body
    if message:
        lines.append("")
        # system short messages are rendered plainly
        if speaker == "system" or len(message) < 120 and "\n" not in message:
            lines.append(f"  {DIM}{_render_inline(message)}{R}")
        else:
            lines.append(render_markdown(message, indent="  ", width=term_width - 2))
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Session header box
# ---------------------------------------------------------------------------

def _render_session_header(meta: dict[str, Any], term_width: int, last_updated: str = "") -> str:
    """Render a top-of-screen box with session metadata."""
    session_id = meta.get("session_id", "")
    topic = meta.get("topic", "")
    participants = meta.get("participants", [])
    created_at = meta.get("created_at", "")

    title = "vibe-coding-discussion"
    top_border = f"{_fg(33)}╭─ {title} {'─' * max(2, term_width - len(title) - 5)}{R}"
    bot_border = f"{_fg(33)}╰{'─' * (term_width - 1)}{R}"
    bar = f"{_fg(33)}│{R}"

    def row(label: str, value: str) -> str:
        return f"{bar}  {BOLD}{label:<12}{R}  {value}"

    plist = "  ".join(
        f"{_SPEAKER_COLORS.get(p.lower(), _fg(39))}{p}{R}" for p in participants
    )
    rows = [
        top_border,
        row("Session", f"{BOLD}{session_id}{R}"),
        row("Topic", _render_inline(topic)),
        row("Agents", plist),
        row("Created", f"{_fg(240)}{created_at}{R}"),
    ]
    if last_updated:
        rows.append(row("Updated", f"{_fg(240)}{last_updated}{R}"))
    rows.append(bot_border)
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# List sessions (TUI)
# ---------------------------------------------------------------------------

def _list_sessions_tui(memory_root: str, limit: int, term_width: int) -> None:
    """Print all sessions sorted by last-update time."""
    import importlib.util, os as _os
    # Re-use list_sessions logic inline to avoid import path issues
    layout = ensure_layout(memory_root)
    sessions_dir = layout["sessions"]

    candidates: list[tuple[Path, float]] = []
    for entry in sessions_dir.iterdir():
        if not entry.is_dir():
            continue
        meta_path = entry / "meta.json"
        if not meta_path.exists():
            continue
        jsonl = entry / "session.jsonl"
        mtime = jsonl.stat().st_mtime if jsonl.exists() else meta_path.stat().st_mtime
        candidates.append((entry, mtime))
    candidates.sort(key=lambda t: t[1], reverse=True)

    title = "vibe-coding-discussion sessions"
    print(f"{_fg(33)}╭─ {title} {'─' * max(2, term_width - len(title) - 5)}{R}")
    print(f"{_fg(33)}│{R}  {DIM}sorted by last update — most recent first{R}")
    print(f"{_fg(33)}╰{'─' * (term_width - 1)}{R}")
    print()

    count = 0
    for entry, mtime in candidates:
        meta_path = entry / "meta.json"
        jsonl_path = entry / "session.jsonl"
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        count += 1
        sid = meta.get("session_id", entry.name)
        topic = meta.get("topic", "")
        updated = dt.datetime.fromtimestamp(mtime, tz=dt.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        msg_count = 0
        if jsonl_path.exists():
            with jsonl_path.open(encoding="utf-8") as fh:
                for ln in fh:
                    if ln.strip():
                        msg_count += 1

        num_str   = f"{_fg(240)}{count:>3}.{R}"
        sid_str   = f"{BOLD}{sid}{R}"
        topic_str = _render_inline(topic) if topic else f"{DIM}(no topic){R}"
        upd_str   = f"{_fg(244)}{updated}{R}"
        cnt_str   = f"{_fg(82)}{msg_count}{R} {_fg(240)}msgs{R}"

        print(f"  {num_str}  {sid_str}")
        print(f"       {_fg(240)}topic:{R}   {topic_str}")
        print(f"       {_fg(240)}updated:{R} {upd_str}  {cnt_str}")
        print()

        if limit > 0 and count >= limit:
            break

    if count == 0:
        print(f"  {DIM}No sessions found.{R}")
        print()

    print(
        f"  {_fg(240)}Run with{R} {_CODE_I} --session-id <id> {R} "
        f"{_fg(240)}to watch a session.{R}"
    )
    print()


# ---------------------------------------------------------------------------
# Main watch logic
# ---------------------------------------------------------------------------

def _get_last_updated_str(jsonl_path: Path) -> str:
    if not jsonl_path.exists():
        return ""
    try:
        mtime = jsonl_path.stat().st_mtime
        return dt.datetime.fromtimestamp(mtime, tz=dt.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    except Exception:
        return ""


def watch(args: argparse.Namespace) -> None:
    """Watch a specific session, rendering events with TUI formatting."""
    term_width = shutil.get_terminal_size((80, 24)).columns

    if not args.session_id:
        _list_sessions_tui(args.memory_root, args.limit, term_width)
        return

    paths = session_paths(args.memory_root, args.session_id)
    if not paths["root"].exists():
        print(json.dumps({"ok": False, "error": f"session not found: {args.session_id}"}))
        raise SystemExit(1)

    meta = load_meta(paths["meta"])

    # Compute effective since_index
    since = args.since_index
    if args.tail > 0:
        # tail mode: show last N events regardless of since_index
        since = -1  # we'll slice after loading

    events = read_jsonl(paths["jsonl"])
    if args.tail > 0:
        events = events[-args.tail:]
    else:
        events = [e for e in events if isinstance(e.get("index"), int) and int(e["index"]) > since]

    last_updated = _get_last_updated_str(paths["jsonl"])
    print(_render_session_header(meta, term_width, last_updated=last_updated))
    print()

    last_index = since
    for evt in events:
        print(_render_event(evt, term_width))
        if isinstance(evt.get("index"), int):
            last_index = int(evt["index"])

    if not args.follow:
        if not events:
            print(f"  {DIM}No events to display.{R}")
            print()
        return

    # ── follow mode ─────────────────────────────────────────────────────────
    sep = f"  {_fg(238)}{'┄' * (term_width - 4)}{R}"
    print(f"\n  {_fg(244)}⏳  watching {BOLD}{args.session_id}{R}{_fg(244)} "
          f"— press Ctrl-C to quit{R}\n")
    try:
        while True:
            time.sleep(args.interval)
            new_events = read_jsonl(paths["jsonl"])
            new_events = [e for e in new_events
                          if isinstance(e.get("index"), int) and int(e["index"]) > last_index]
            if new_events:
                print(sep)
                for evt in new_events:
                    print(_render_event(evt, term_width))
                    if isinstance(evt.get("index"), int):
                        last_index = int(evt["index"])
    except KeyboardInterrupt:
        print(f"\n  {_fg(244)}stopped.{R}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Watch a vibe-coding-discussion session with TUI-style output."
    )
    parser.add_argument("--memory-root", default=".memory",
                        help="Memory root directory. Default: .memory")
    parser.add_argument("--session-id", default="",
                        help="Session id to watch. Omit to list sessions.")
    parser.add_argument("--since-index", type=int, default=-1,
                        help="Show events with index > N. Default: show all (-1)")
    parser.add_argument("--tail", type=int, default=0,
                        help="Show last N events only (overrides --since-index)")
    parser.add_argument("--follow", "-f", action="store_true",
                        help="Keep watching and print new events as they arrive")
    parser.add_argument("--interval", type=float, default=1.5,
                        help="Poll interval in seconds for --follow mode. Default: 1.5")
    parser.add_argument("--limit", type=int, default=20,
                        help="Max sessions shown when listing. Default: 20")
    return parser


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        watch(args)
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
