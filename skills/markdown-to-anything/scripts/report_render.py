#!/usr/bin/env python3
"""Render Markdown to HTML/PDF for markdown-to-anything full-report channel."""

from __future__ import annotations

import argparse
import html
import json
import platform
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
    "dark": {"bg": "#0d1117", "text": "#e6edf3", "muted": "#8b949e", "accent": "#58a6ff", "card": "#161b22"},
    "blue": {"bg": "#f6fbff", "text": "#0f2740", "muted": "#4f6f8f", "accent": "#1976d2", "card": "#ffffff"},
    "light": {"bg": "#f8fafd", "text": "#111827", "muted": "#6b7280", "accent": "#2563eb", "card": "#ffffff"},
}
FONT_SIZE_PX = {"small": 24, "medium": 28, "large": 32}


@dataclass(slots=True)
class ReportRenderResult:
    """Report render result."""

    html_path: str | None
    pdf_path: str | None
    png_path: str | None
    markdown_engine: str
    warnings: list[str]


def _font_family() -> str:
    is_linux = platform.system() == "Linux"
    emoji = "'Apple Color Emoji','Segoe UI Emoji','Noto Color Emoji'"
    if is_linux:
        return f"'Noto Sans CJK SC','Noto Sans SC','WenQuanYi Micro Hei',{emoji},sans-serif"
    # macOS print-to-PDF is generally more stable with system CJK fonts first.
    return f"'PingFang SC','Hiragino Sans GB','Microsoft YaHei','Noto Sans SC',{emoji},sans-serif"


def _font_link_html(enable_remote_fonts: bool = True) -> str:
    if not enable_remote_fonts:
        return ""
    return (
        "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">"
        "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>"
        "<link href=\"https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap\" rel=\"stylesheet\">"
    )


def _build_css(theme: str, font_size: str) -> str:
    tokens = THEMES[theme]
    body = FONT_SIZE_PX[font_size]
    table = max(20, int(round(body * 0.82)))
    meta = max(20, int(round(body * 0.79)))
    line_height = "1.60" if font_size == "large" else "1.65"
    return f"""
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  width: 750px;
  max-width: 750px;
  margin: 0 auto;
  padding: 24px 20px 40px;
  background: {tokens['bg']};
  color: {tokens['text']};
  font-family: {_font_family()};
  font-size: {body}px;
  line-height: {line_height};
  -webkit-text-size-adjust: 100%;
  text-size-adjust: 100%;
}}
article {{ background: {tokens['card']}; border-radius: 20px; padding: 28px 24px 36px; box-shadow: 0 8px 32px rgba(0,0,0,.08); }}
h1,h2,h3 {{ line-height: 1.25; margin: 1.1em 0 .45em; }}
h1 {{ font-size: calc({body}px * 1.75); color: {tokens['accent']}; border-bottom: 2px solid rgba(25,118,210,.25); padding-bottom: .28em; }}
h2 {{ font-size: calc({body}px * 1.42); color: {tokens['accent']}; border-left: 4px solid {tokens['accent']}; padding-left: .45em; }}
h3 {{ font-size: calc({body}px * 1.21); color: {tokens['text']}; }}
p, ul, ol, pre, table, blockquote {{ margin: .5em 0; }}
ul, ol {{ padding-left: 1.2em; }}
li {{ margin: .25em 0; }}
a {{ color: {tokens['accent']}; }}
strong {{ font-weight: 700; }}
code {{ background: rgba(127,127,127,.14); border-radius: 6px; padding: .08em .28em; font-size: {table}px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
pre {{ background: rgba(127,127,127,.14); padding: .7em .8em; border-radius: 10px; overflow-x: auto; white-space: pre-wrap; word-break: break-word; }}
pre code {{ background: transparent; padding: 0; font-size: {table}px; }}
table {{ border-collapse: collapse; width: 100%; font-size: {table}px; }}
th, td {{ border: 1px solid rgba(127,127,127,.25); padding: .35em .45em; text-align: left; vertical-align: top; }}
th {{ background: rgba(25,118,210,.10); }}
blockquote {{ border-left: 4px solid {tokens['accent']}; padding-left: .7em; color: {tokens['muted']}; }}
hr {{ border: none; border-top: 1px solid rgba(127,127,127,.25); margin: 1em 0; }}
.meta {{ color: {tokens['muted']}; font-size: {meta}px; }}
/* Browser PDF exports may omit page backgrounds; force readable print contrast. */
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
  code, pre {{
    color: #111827 !important;
  }}
  a {{
    color: #0f4c81 !important;
  }}
}}
@page {{ size: A4; margin: 0.4in; }}
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
        out.append("<pre><code>" + _escape_html("\n".join(code_lines)) + "</code></pre>")
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
            out.append(f"<blockquote>{_inline_text_markup(stripped[2:].strip())}</blockquote>")
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
                numbered = idx > 0 and stripped[:idx].isdigit() and len(stripped) > idx + 1 and stripped[idx + 1] == " "
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
            out.append(f"<p class=\"meta\">{_inline_text_markup(stripped)}</p>")
            continue

        paragraph.append(stripped)

    if in_code:
        flush_code()
    flush_paragraph()
    close_lists()
    return "\n".join(out)


def _build_marked_shell(md_text: str, theme: str, font_size: str, include_remote_fonts: bool = True) -> str:
    md_source = _escape_html(md_text)
    js_source = VENDOR_MARKED.read_text(encoding="utf-8") if VENDOR_MARKED.exists() else "window.marked={parse:(s)=>'<pre>'+s+'</pre>'};"
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


def _build_static_html(body_html: str, theme: str, font_size: str, include_remote_fonts: bool = True) -> str:
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
            html_doc = _build_static_html(proc.stdout, theme, font_size, include_remote_fonts=include_remote_fonts)
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


def render_html_to_pdf(html_path: Path, output_pdf: Path, width: int = 750) -> list[str]:
    """Render HTML to PDF using `screenshot.js` backend."""
    warnings: list[str] = []
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node not found; cannot render PDF")
    if not SCREENSHOT_JS.exists():
        raise RuntimeError(f"screenshot.js not found: {SCREENSHOT_JS}")
    proc = subprocess.run(
        [node, str(SCREENSHOT_JS), "--pdf", str(html_path.resolve()), str(output_pdf.resolve()), str(width)],
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
    with tempfile.NamedTemporaryFile(prefix="mta_report_", suffix=".html", delete=False) as tmp:
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
    with tempfile.NamedTemporaryFile(prefix="mta_report_", suffix=".html", delete=False) as tmp:
        tmp_html = Path(tmp.name)
    try:
        html_doc, engine = report_markdown_to_html(markdown_path)
        tmp_html.write_text(html_doc, encoding="utf-8")
        warnings.append("png render uses report html renderer for stability")
        warnings.extend(render_html_to_png(tmp_html, output_png, dpr=3, width=750, max_page_height=0))
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
    parser = argparse.ArgumentParser(description="Render Markdown to HTML/PDF for markdown-to-anything")
    parser.add_argument("input", help="Input Markdown file")
    parser.add_argument("--output", required=True, help="Output path (.html or .pdf)")
    parser.add_argument("--format", choices=["html", "pdf", "png"], default="html")
    parser.add_argument("--theme", choices=["dark", "blue", "light"], default="dark")
    parser.add_argument("--font-size", choices=["small", "medium", "large"], default="medium")
    parser.add_argument("--engine", choices=["auto", "pandoc", "marked", "fallback"], default="auto")
    parser.add_argument("--stdout-result", action="store_true", help="Print JSON result")
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
