#!/usr/bin/env python3
"""Render Markdown to HTML/PDF for markdown-to-anything full-report channel."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from report_html_render import markdown_to_html as report_markdown_to_html  # type: ignore  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
VENDOR_MARKED = SCRIPT_DIR / "vendor" / "marked.min.js"
SCREENSHOT_JS = SCRIPT_DIR / "screenshot.js"

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0d1117",
        "text": "#e6edf3",
        "muted": "#8b949e",
        "accent": "#58a6ff",
        "card": "#161b22",
    },
    "blue": {
        "bg": "#f6fbff",
        "text": "#0f2740",
        "muted": "#4f6f8f",
        "accent": "#1976d2",
        "card": "#ffffff",
    },
    "light": {
        "bg": "#f8fafd",
        "text": "#111827",
        "muted": "#6b7280",
        "accent": "#2563eb",
        "card": "#ffffff",
    },
}
FONT_SIZE_PX = {"small": 13, "medium": 15, "large": 18}


@dataclass(slots=True)
class ReportRenderResult:
    """Report render result."""

    html_path: str | None
    pdf_path: str | None
    png_path: str | None
    markdown_engine: str
    warnings: list[str]


SCRIPT_DIR = Path(__file__).resolve().parent
FONTS_DIR = SCRIPT_DIR / ".." / "assets" / "fonts"


def _font_family() -> str:
    """Return font-family string with local fonts as primary."""
    emoji = "'Apple Color Emoji','Segoe UI Emoji','Noto Color Emoji'"
    return f"'Noto Sans SC Local','Noto Sans SC','PingFang SC','Hiragino Sans GB','Microsoft YaHei',{emoji},sans-serif"


def _get_font_data_url(font_file: str) -> str:
    """Read font file and return base64 data URL."""
    font_path = FONTS_DIR / font_file
    if font_path.exists():
        import base64

        data = font_path.read_bytes()
        return f"data:font/truetype;base64,{base64.b64encode(data).decode()}"
    return ""


def _font_css_inline() -> str:
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


def _font_link_html(enable_remote_fonts: bool = False) -> str:
    """Return font CSS - now using inline local fonts only, no CDN."""
    return f"<style>{_font_css_inline()}</style>"


def _build_css(theme: str, font_size: str) -> str:
    tokens = THEMES[theme]
    body = FONT_SIZE_PX[font_size]
    table = max(11, int(round(body * 0.87)))
    meta = max(10, int(round(body * 0.80)))
    line_height = "1.55"
    return f"""
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  width: 750px;
  max-width: 750px;
  margin: 0 auto;
  padding: 0 4px;
  background: {tokens["bg"]};
  color: {tokens["text"]};
  font-family: {_font_family()};
  font-size: {body}px;
  line-height: {line_height};
  -webkit-text-size-adjust: 100%;
  text-size-adjust: 100%;
}}
article {{ background: {tokens["card"]}; border-radius: 12px; padding: 20px 18px 28px; box-shadow: 0 4px 20px rgba(0,0,0,.06); }}
h1,h2,h3 {{ line-height: 1.2; }}
h1 {{ font-size: calc({body}px * 1.55); font-weight: 700; color: {tokens["accent"]}; border-bottom: 2px solid rgba(25,118,210,.3); padding-bottom: .22em; margin: 10px 0 8px; }}
h2 {{ font-size: calc({body}px * 1.22); font-weight: 700; color: {tokens["accent"]}; border-left: 3px solid {tokens["accent"]}; padding-left: .5em; margin: 16px 0 6px; }}
h3 {{ font-size: calc({body}px * 1.07); font-weight: 600; color: {tokens["text"]}; margin: 10px 0 4px; }}
p, ul, ol, pre, table, blockquote {{ margin: .35em 0; }}
ul, ol {{ padding-left: 1.15em; }}
li {{ margin: .2em 0; }}
a {{ color: {tokens["accent"]}; }}
strong {{ font-weight: 700; color: {tokens["accent"]}; }}
code {{ background: rgba(127,127,127,.12); border-radius: 4px; padding: .06em .22em; font-size: {table}px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
pre {{ background: rgba(127,127,127,.12); padding: .5em .7em; border-radius: 6px; overflow-x: auto; white-space: pre-wrap; word-break: break-word; }}
pre code {{ background: transparent; padding: 0; font-size: {table}px; }}
table {{ border-collapse: collapse; width: 100%; font-size: {table}px; table-layout: auto; margin: .4em 0; }}
th {{ border: 1px solid rgba(25,118,210,.25); padding: 5px 7px; text-align: left; vertical-align: top; background: rgba(25,118,210,.08); font-weight: 700; white-space: nowrap; }}
td {{ border: 1px solid rgba(127,127,127,.2); padding: 4px 7px; text-align: left; vertical-align: top; word-break: break-word; overflow-wrap: break-word; }}
tr:nth-child(even) td {{ background: rgba(25,118,210,.03); }}
blockquote {{ border-left: 3px solid {tokens["accent"]}; padding-left: .6em; color: {tokens["muted"]}; }}
hr {{ border: none; border-top: 1px solid rgba(127,127,127,.2); margin: .8em 0; }}
.meta {{ color: {tokens["muted"]}; font-size: {meta}px; }}
@media print {{
  html, body {{
    background: #ffffff !important;
    color: #111827 !important;
    font-family: {_font_family()} !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  body {{
    width: auto;
    max-width: none;
    margin: 0 !important;
    padding: 0 !important;
  }}
  article {{
    background: #ffffff !important;
    color: #111827 !important;
    font-family: {_font_family()} !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    padding: 0 !important;
  }}
  h1, h2 {{
    color: #0f4c81 !important;
  }}
  h1, h2, h3, p, li, td, th, blockquote, .meta {{
    color: #111827 !important;
    font-family: {_font_family()} !important;
  }}
  strong {{ color: #0f4c81 !important; }}
  code, pre {{
    color: #111827 !important;
  }}
  a {{
    color: #0f4c81 !important;
  }}
  h2, h3 {{ page-break-after: avoid; }}
  table {{ page-break-inside: avoid; }}
}}
"""


def _escape_html(text: str) -> str:
    return html.escape(text, quote=True)


def _inline_text_markup(text: str) -> str:
    # Minimal inline markup without regex.
    out = _escape_html(text)
    # Keep simple for MVP; no inline emphasis parsing to avoid brittle parser logic.
    return out


def _simple_markdown_to_html(md_text: str) -> str:
    """Very small Markdown fallback renderer (no external deps)."""
    lines = md_text.splitlines()
    out: list[str] = []
    in_code = False
    in_ul = False
    in_ol = False
    code_lines: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            out.append(f"<p>{_inline_text_markup(' '.join(paragraph).strip())}</p>")
            paragraph = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def flush_code() -> None:
        nonlocal code_lines
        out.append(
            "<pre><code>" + _escape_html("\n".join(code_lines)) + "</code></pre>"
        )
        code_lines = []

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            close_lists()
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
                code_lines = []
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            flush_paragraph()
            close_lists()
            continue

        if stripped.startswith("# "):
            flush_paragraph()
            close_lists()
            out.append(f"<h1>{_inline_text_markup(stripped[2:].strip())}</h1>")
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            close_lists()
            out.append(f"<h2>{_inline_text_markup(stripped[3:].strip())}</h2>")
            continue
        if stripped.startswith("### "):
            flush_paragraph()
            close_lists()
            out.append(f"<h3>{_inline_text_markup(stripped[4:].strip())}</h3>")
            continue
        if stripped.startswith("> "):
            flush_paragraph()
            close_lists()
            out.append(
                f"<blockquote>{_inline_text_markup(stripped[2:].strip())}</blockquote>"
            )
            continue
        if stripped in {"---", "***"}:
            flush_paragraph()
            close_lists()
            out.append("<hr />")
            continue

        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_inline_text_markup(stripped[2:].strip())}</li>")
            continue

        numbered = False
        for idx, ch in enumerate(stripped):
            if ch == ".":
                numbered = (
                    idx > 0
                    and stripped[:idx].isdigit()
                    and len(stripped) > idx + 1
                    and stripped[idx + 1] == " "
                )
                break
            if not ch.isdigit():
                break
        if numbered:
            flush_paragraph()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            content = stripped.split(".", 1)[1].strip()
            out.append(f"<li>{_inline_text_markup(content)}</li>")
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            close_lists()
            out.append(f'<p class="meta">{_inline_text_markup(stripped)}</p>')
            continue

        paragraph.append(stripped)

    if in_code:
        flush_code()
    flush_paragraph()
    close_lists()
    return "\n".join(out)


def _build_marked_shell(
    md_text: str, theme: str, font_size: str, include_remote_fonts: bool = True
) -> str:
    md_source = _escape_html(md_text)
    js_source = (
        VENDOR_MARKED.read_text(encoding="utf-8")
        if VENDOR_MARKED.exists()
        else "window.marked={parse:(s)=>'<pre>'+s+'</pre>'};"
    )
    css = _build_css(theme, font_size)
    return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
{_font_link_html(include_remote_fonts)}
<style>{css}</style>
</head>
<body>
<article id=\"report\"></article>
<script>{js_source}</script>
<script type=\"text/plain\" id=\"md-source\">{md_source}</script>
<script>
(function() {{
  const src = document.getElementById('md-source');
  const report = document.getElementById('report');
  const md = src ? src.textContent : '';
  report.innerHTML = (window.marked && window.marked.parse) ? window.marked.parse(md) : '<pre>' + md + '</pre>';
  window.__md_rendered = true;
}})();
</script>
</body>
</html>"""


def _build_static_html(
    body_html: str, theme: str, font_size: str, include_remote_fonts: bool = True
) -> str:
    css = _build_css(theme, font_size)
    return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
{_font_link_html(include_remote_fonts)}
<style>{css}</style>
</head>
<body><article>{body_html}</article><script>window.__md_rendered=true;</script></body>
</html>"""


def render_markdown_to_html(
    markdown_path: Path,
    output_html: Path,
    theme: str = "dark",
    font_size: str = "medium",
    prefer_engine: str = "auto",
    include_remote_fonts: bool = True,
) -> tuple[str, list[str]]:
    """Render Markdown file to HTML.

    Args:
        markdown_path: Source Markdown path.
        output_html: Destination HTML path.
        theme: Theme token set.
        font_size: Font-size tier.
        prefer_engine: `auto`, `pandoc`, `marked`, or `fallback`.

    Returns:
        Tuple of (engine_used, warnings).
    """
    warnings: list[str] = []
    md_text = markdown_path.read_text(encoding="utf-8")
    engine_used = "fallback"
    html_doc = ""

    pandoc_available = shutil.which("pandoc") is not None
    if prefer_engine in {"auto", "pandoc"} and pandoc_available:
        try:
            proc = subprocess.run(
                ["pandoc", "--from=markdown", "--to=html5", str(markdown_path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            html_doc = _build_static_html(
                proc.stdout, theme, font_size, include_remote_fonts=include_remote_fonts
            )
            engine_used = "pandoc"
        except Exception as exc:
            warnings.append(f"pandoc failed, fallback used: {exc}")
            if prefer_engine == "pandoc":
                html_doc = _build_static_html(
                    _simple_markdown_to_html(md_text),
                    theme,
                    font_size,
                    include_remote_fonts=include_remote_fonts,
                )
                engine_used = "fallback"

    if not html_doc and prefer_engine in {"auto", "marked"}:
        if VENDOR_MARKED.exists():
            html_doc = _build_marked_shell(
                md_text,
                theme,
                font_size,
                include_remote_fonts=include_remote_fonts,
            )
            engine_used = "marked"
        else:
            warnings.append("vendor/marked.min.js missing, using fallback renderer")

    if not html_doc:
        html_doc = _build_static_html(
            _simple_markdown_to_html(md_text),
            theme,
            font_size,
            include_remote_fonts=include_remote_fonts,
        )
        engine_used = "fallback"

    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html_doc, encoding="utf-8")
    return engine_used, warnings


def render_html_to_pdf(
    html_path: Path, output_pdf: Path, width: int = 750
) -> list[str]:
    """Render HTML to PDF using `screenshot.js` backend."""
    warnings: list[str] = []
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node not found; cannot render PDF")
    if not SCREENSHOT_JS.exists():
        raise RuntimeError(f"screenshot.js not found: {SCREENSHOT_JS}")
    proc = subprocess.run(
        [
            node,
            str(SCREENSHOT_JS),
            "--pdf",
            str(html_path.resolve()),
            str(output_pdf.resolve()),
            str(width),
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "screenshot.js --pdf failed")
    if proc.stderr.strip():
        warnings.append(proc.stderr.strip())
    return warnings


def render_html_to_png(
    html_path: Path,
    output_png: Path,
    dpr: int = 3,
    width: int = 750,
    max_page_height: int = 0,
) -> list[str]:
    """Render HTML to PNG using `screenshot.js` backend."""
    warnings: list[str] = []
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node not found; cannot render PNG")
    if not SCREENSHOT_JS.exists():
        raise RuntimeError(f"screenshot.js not found: {SCREENSHOT_JS}")
    proc = subprocess.run(
        [
            node,
            str(SCREENSHOT_JS),
            "--png",
            str(html_path.resolve()),
            str(output_png.resolve()),
            str(dpr),
            str(width),
            str(max_page_height),
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "screenshot.js --png failed")
    if proc.stderr.strip():
        warnings.append(proc.stderr.strip())
    return warnings


def render_markdown_to_pdf(
    markdown_path: Path,
    output_pdf: Path,
    theme: str = "dark",
    font_size: str = "medium",
    prefer_engine: str = "auto",
) -> ReportRenderResult:
    """Render Markdown to PDF (with intermediate HTML temp file)."""
    warnings: list[str] = []
    with tempfile.NamedTemporaryFile(
        prefix="mta_report_", suffix=".html", delete=False
    ) as tmp:
        tmp_html = Path(tmp.name)
    try:
        html_doc, engine = report_markdown_to_html(markdown_path)
        tmp_html.write_text(html_doc, encoding="utf-8")
        warnings.append("pdf render uses report html renderer for stability")
        warnings.extend(render_html_to_pdf(tmp_html, output_pdf))
        return ReportRenderResult(
            html_path=str(tmp_html),
            pdf_path=str(output_pdf),
            png_path=None,
            markdown_engine=engine,
            warnings=warnings,
        )
    except Exception:
        tmp_html.unlink(missing_ok=True)
        raise


def render_markdown_to_png(
    markdown_path: Path,
    output_png: Path,
    theme: str = "light",
    font_size: str = "medium",
    prefer_engine: str = "auto",
) -> ReportRenderResult:
    """Render Markdown to PNG (with intermediate HTML temp file)."""
    warnings: list[str] = []
    with tempfile.NamedTemporaryFile(
        prefix="mta_report_", suffix=".html", delete=False
    ) as tmp:
        tmp_html = Path(tmp.name)
    try:
        html_doc, engine = report_markdown_to_html(markdown_path)
        tmp_html.write_text(html_doc, encoding="utf-8")
        warnings.append("png render uses report html renderer for stability")
        warnings.extend(
            render_html_to_png(
                tmp_html, output_png, dpr=3, width=750, max_page_height=0
            )
        )
        return ReportRenderResult(
            html_path=str(tmp_html),
            pdf_path=None,
            png_path=str(output_png),
            markdown_engine=engine,
            warnings=warnings,
        )
    except Exception:
        tmp_html.unlink(missing_ok=True)
        raise


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Render Markdown to HTML/PDF for markdown-to-anything"
    )
    parser.add_argument("input", help="Input Markdown file")
    parser.add_argument("--output", required=True, help="Output path (.html or .pdf)")
    parser.add_argument("--format", choices=["html", "pdf", "png"], default="html")
    parser.add_argument("--theme", choices=["dark", "blue", "light"], default="dark")
    parser.add_argument(
        "--font-size", choices=["small", "medium", "large"], default="medium"
    )
    parser.add_argument(
        "--engine", choices=["auto", "pandoc", "marked", "fallback"], default="auto"
    )
    parser.add_argument(
        "--stdout-result", action="store_true", help="Print JSON result"
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    output_path = Path(args.output).expanduser()

    if args.format == "html":
        engine, warnings = render_markdown_to_html(
            input_path,
            output_path,
            theme=args.theme,
            font_size=args.font_size,
            prefer_engine=args.engine,
        )
        result = ReportRenderResult(
            html_path=str(output_path),
            pdf_path=None,
            png_path=None,
            markdown_engine=engine,
            warnings=warnings,
        )
    elif args.format == "pdf":
        result = render_markdown_to_pdf(
            input_path,
            output_path,
            theme=args.theme,
            font_size=args.font_size,
            prefer_engine=args.engine,
        )
    else:
        result = render_markdown_to_png(
            input_path,
            output_path,
            theme=args.theme,
            font_size=args.font_size,
            prefer_engine=args.engine,
        )

    if args.stdout_result:
        print(json.dumps(asdict(result), ensure_ascii=False))
    else:
        print(result.pdf_path or result.png_path or result.html_path)


if __name__ == "__main__":
    main()
