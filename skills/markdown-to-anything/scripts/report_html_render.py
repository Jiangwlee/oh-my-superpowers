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
    font-size: 14px;
    line-height: 1.55;
    color: #1a1a2e;
    background: #ffffff;
    padding: 0 4px;
    max-width: 750px;
}
h1 {
    font-size: 22px;
    font-weight: 700;
    color: #0d3880;
    border-bottom: 2px solid #1565c0;
    padding-bottom: 5px;
    margin: 14px 0 8px;
    letter-spacing: 0.01em;
}
h2 {
    font-size: 17px;
    font-weight: 700;
    color: #1565c0;
    margin: 18px 0 7px;
    padding-left: 9px;
    border-left: 3px solid #42a5f5;
}
h3 { font-size: 15px; font-weight: 600; color: #1a1a2e; margin: 12px 0 5px; }
p { margin: 5px 0; }
ul, ol { padding-left: 18px; margin: 5px 0; }
li { margin: 3px 0; }
strong { font-weight: 700; color: #0d3880; }
em { color: #1565c0; font-style: normal; font-weight: 500; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 13px; table-layout: auto; }
th {
    background: #e3f2fd; color: #0d3880;
    padding: 6px 8px; text-align: left; border: 1px solid #bbdefb;
    font-weight: 700; white-space: nowrap;
}
td {
    padding: 5px 8px; border: 1px solid #e0e0e0; vertical-align: top;
    word-break: break-word; overflow-wrap: break-word;
}
tr:nth-child(even) td { background: #f8fbff; }
code {
    background: #f3f3f3; padding: 1px 4px; border-radius: 3px;
    font-size: 12px; font-family: 'SF Mono', Menlo, Consolas, monospace;
}
pre {
    background: #f3f3f3; padding: 10px 12px; border-radius: 4px;
    font-size: 12px; overflow-x: auto; margin: 8px 0;
    white-space: pre-wrap; word-break: break-all;
}
pre code { background: none; padding: 0; }
blockquote { border-left: 3px solid #90caf9; padding-left: 12px; color: #555; margin: 8px 0; }
hr { border: none; border-top: 1px solid #e8e8e8; margin: 12px 0; }
@media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    h2, h3 { page-break-after: avoid; }
    table { page-break-inside: avoid; }
}
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
