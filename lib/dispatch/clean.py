"""ANSI escape sequence stripping."""

from __future__ import annotations

import re

# CSI (incl. DEC private mode `?`), OSC (BEL-terminated), G0/G1 designators
_ANSI_PATTERNS = [
    re.compile(r"\x1b\[\??[0-9;]*[a-zA-Z]"),
    re.compile(r"\x1b\][^\x07]*\x07"),
    re.compile(r"\x1b[\(\)][AB012]"),
]


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences and stray carriage returns."""
    for pattern in _ANSI_PATTERNS:
        text = pattern.sub("", text)
    return text.replace("\r", "")
