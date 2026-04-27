"""ANSI escape stripping."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from dispatch.clean import strip_ansi


def test_strip_csi_color():
    assert strip_ansi("\x1b[31mred\x1b[0m") == "red"


def test_strip_csi_cursor_movement():
    assert strip_ansi("foo\x1b[2Kbar") == "foobar"


def test_strip_dec_private_mode():
    assert strip_ansi("\x1b[?25lhidden\x1b[?25h") == "hidden"


def test_strip_osc_title():
    assert strip_ansi("\x1b]0;window-title\x07hello") == "hello"


def test_strip_g0_designator():
    assert strip_ansi("\x1b(B\x1b(0lqk") == "lqk"


def test_strip_carriage_return():
    assert strip_ansi("line1\r\nline2") == "line1\nline2"


def test_plain_text_passthrough():
    assert strip_ansi("hello world\n") == "hello world\n"


def test_empty_input():
    assert strip_ansi("") == ""
