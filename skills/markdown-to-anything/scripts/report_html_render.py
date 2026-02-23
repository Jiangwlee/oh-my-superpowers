#!/usr/bin/env python3
"""Markdown -> HTML renderer tuned for Chrome print-to-PDF and screenshots.

This module intentionally keeps the HTML/CSS simple and print-friendly.
It is designed to be stable for CJK text and emoji in PDF output.
"""

from __future__ import annotations

import base64
import html
import shutil
import subprocess
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
FONTS_DIR = SCRIPT_DIR / ".." / "assets" / "fonts"

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0;
    -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
body {
    font-family: 'Noto Sans SC Local', 'Noto Sans SC', 'PingFang SC', 'Hiragino Sans GB',
                 'Microsoft YaHei', sans-serif;
    font-size: 30px;
    line-height: 1.8;
    color: #1a1a1a;
    background: #ffffff;
    padding: 28px 22px 48px;
    max-width: 750px;
}
h1 {
    font-size: 38px;
    color: #0d47a1;
    border-bottom: 2px solid #0d47a1;
    padding-bottom: 8px;
    margin: 20px 0 14px;
}
h2 {
    font-size: 35px;
    color: #1565c0;
    margin: 22px 0 12px;
    padding-left: 10px;
    border-left: 4px solid #42a5f5;
}
h3 { font-size: 30px; color: #333; margin: 16px 0 8px; }
p { margin: 8px 0; }
ul, ol { padding-left: 22px; margin: 8px 0; }
li { margin: 5px 0; }
strong { color: #c62828; }
em { color: #5c6bc0; font-style: normal; font-weight: 500; }
table { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 27px; }
th {
    background: #e3f2fd; color: #0d47a1;
    padding: 8px 12px; text-align: left; border: 1px solid #bbdefb;
}
td { padding: 7px 12px; border: 1px solid #e0e0e0; vertical-align: top; }
tr:nth-child(even) td { background: #fafafa; }
code {
    background: #f3f3f3; padding: 2px 6px; border-radius: 3px;
    font-size: 27px; font-family: 'SF Mono', Menlo, Consolas, monospace;
}
pre {
    background: #f3f3f3; padding: 16px; border-radius: 6px;
    font-size: 25px; overflow-x: auto; margin: 12px 0;
    white-space: pre-wrap; word-break: break-all;
}
pre code { background: none; padding: 0; }
blockquote { border-left: 4px solid #90caf9; padding-left: 16px; color: #555; margin: 12px 0; }
hr { border: none; border-top: 1px solid #e8e8e8; margin: 18px 0; }
"""


def _get_font_data_url(font_file: str) -> str:
    """Read font file and return base64 data URL."""
    font_path = FONTS_DIR / font_file
    if font_path.exists():
        data = font_path.read_bytes()
        return f"data:font/truetype;base64,{base64.b64encode(data).decode()}"
    return ""


def _font_css() -> str:
    """Return inline @font-face CSS with base64-encoded local fonts."""
    regular_url = _get_font_data_url("NotoSansSC-Regular.ttf")
    medium_url = _get_font_data_url("NotoSansSC-Medium.ttf")
    bold_url = _get_font_data_url("NotoSansSC-Bold.ttf")

    css_parts = []
    if regular_url:
        css_parts.append(f"""
@font-face {{
  font-family: 'Noto Sans SC Local';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url({regular_url}) format('truetype');
}}""")
    if medium_url:
        css_parts.append(f"""
@font-face {{
  font-family: 'Noto Sans SC Local';
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url({medium_url}) format('truetype');
}}""")
    if bold_url:
        css_parts.append(f"""
@font-face {{
  font-family: 'Noto Sans SC Local';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url({bold_url}) format('truetype');
}}""")

    return "\n".join(css_parts)


def _md_fallback(md_path: Path) -> str:
    content = md_path.read_text(encoding="utf-8")
    return f'<pre style="white-space:pre-wrap;font-size:14px;">{html.escape(content)}</pre>'


def markdown_to_html(md_path: Path) -> tuple[str, str]:
    """Markdown -> full HTML document. Returns (html, engine_used)."""
    engine_used = "fallback"
    if shutil.which("pandoc"):
        try:
            result = subprocess.run(
                ["pandoc", "--from=markdown", "--to=html5", str(md_path)],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            body = result.stdout
            engine_used = "pandoc"
        except Exception:
            body = _md_fallback(md_path)
    else:
        body = _md_fallback(md_path)

    font_css = _font_css()

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{font_css}{_CSS}</style>
</head>
<body>{body}</body>
</html>"""
    return html_doc, engine_used
