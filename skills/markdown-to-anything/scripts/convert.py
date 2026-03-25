#!/usr/bin/env python3
"""CLI entrypoint for markdown-to-anything report rendering."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from inspect_input import inspect_markdown_file  # type: ignore  # noqa: E402
from normalize_input import normalize_markdown_file  # type: ignore  # noqa: E402
from report_render import (  # type: ignore  # noqa: E402
    MOBILE_PDF_PARAMS,
    render_html_to_pdf,
    render_html_to_png,
    render_markdown_to_html,
)
from validate_output import validate_file  # type: ignore  # noqa: E402

OPENCLAW_MEDIA_ROOT = Path.home() / ".openclaw" / "media" / "markdown-to-anything"


@dataclass(slots=True)
class ConvertManifest:
    ok: bool
    input: str
    mode: str
    format: str
    layout: str
    files: list[str]
    theme: str
    font_size: str
    template_used: str | None
    engine: dict[str, str]
    normalization: dict[str, object]
    inspection: dict[str, object]
    intermediate_files: list[str]
    render_ms: int
    warnings: list[str]
    errors: list[str]


def _default_output_base(input_path: Path) -> Path:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return OPENCLAW_MEDIA_ROOT / timestamp / input_path.stem


def _resolve_theme(explicit_theme: str | None, output_format: str) -> str:
    if explicit_theme:
        return explicit_theme
    if output_format == "png":
        return "light"
    return "blue"


def _resolve_pdf_backend(choice: str) -> str:
    if choice == "auto":
        return "html"
    return choice


def _check_dependencies(fmt: str) -> list[str]:
    warnings: list[str] = []
    if not shutil.which("python3"):
        raise RuntimeError("python3 not found")
    if not shutil.which("node"):
        raise RuntimeError("node not found")
    if not shutil.which("pandoc"):
        warnings.append("pandoc not found; markdown engine may fall back")
    if fmt in {"pdf", "png", "both"} and not shutil.which("chromium") and not shutil.which("google-chrome") and not Path("/snap/bin/chromium").exists():
        warnings.append("chrome/chromium not found in common paths; screenshot.js may fail")
    return warnings


def _resolve_output_base(input_path: Path, output: str | None, same_dir: bool) -> Path:
    if output:
        output_path = Path(output).expanduser()
        return output_path.with_suffix("") if output_path.suffix else output_path
    if same_dir:
        return input_path.with_suffix("")
    return _default_output_base(input_path)


def _derived_path(base: Path, extra: str, ext: str) -> Path:
    return base.parent / f"{base.name}{extra}{ext}"


def _render_report(
    input_path: Path,
    output_base: Path,
    requested_format: str,
    theme: str,
    font_size: str,
    prefer_engine: str,
    keep_html: bool,
    file_suffix: str,
    layout: str = "desktop",
) -> tuple[list[str], list[str], dict[str, str], list[str]]:
    files: list[str] = []
    intermediate_files: list[str] = []
    warnings: list[str] = []
    engine = {"markdown_to_html": "n/a", "html_to_pdf": "n/a", "html_to_png": "n/a"}

    html_path = _derived_path(output_base, file_suffix, ".html")
    markdown_engine, html_warnings = render_markdown_to_html(
        input_path,
        html_path,
        theme=theme,
        font_size=font_size,
        prefer_engine=prefer_engine,
        include_remote_fonts=False,
        layout=layout,
    )
    engine["markdown_to_html"] = markdown_engine
    warnings.extend(html_warnings)
    intermediate_files.append(str(html_path))

    # Determine PDF page dimensions based on layout
    pdf_width = int(MOBILE_PDF_PARAMS["viewport_width"]) if layout == "mobile" else 750
    paper_w = float(MOBILE_PDF_PARAMS["paper_width"]) if layout == "mobile" else 8.27
    paper_h = float(MOBILE_PDF_PARAMS["paper_height"]) if layout == "mobile" else 11.69

    if requested_format in {"pdf", "both"}:
        pdf_path = _derived_path(output_base, file_suffix, ".pdf")
        warnings.extend(render_html_to_pdf(html_path, pdf_path, width=pdf_width, paper_width=paper_w, paper_height=paper_h))
        validate = validate_file(pdf_path)
        warnings.extend(validate.warnings)
        if validate.errors:
            raise RuntimeError("; ".join(validate.errors))
        files.append(str(pdf_path))
        engine["html_to_pdf"] = "chromium"

    if requested_format in {"png", "both"}:
        png_path = _derived_path(output_base, file_suffix, ".png")
        warnings.extend(render_html_to_png(html_path, png_path, dpr=3, width=750, max_page_height=0))
        validate = validate_file(png_path)
        warnings.extend(validate.warnings)
        if validate.errors:
            raise RuntimeError("; ".join(validate.errors))
        files.append(str(png_path))
        engine["html_to_png"] = "chromium"

    if not keep_html and html_path.exists():
        html_path.unlink()
        intermediate_files = []

    return files, intermediate_files, engine, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Markdown to PNG/PDF report assets")
    parser.add_argument("input", help="Input Markdown path")
    parser.add_argument("--mode", choices=["auto", "report", "card"], default="auto")
    parser.add_argument("--format", choices=["png", "pdf", "html", "both"], help="Output format")
    parser.add_argument("--theme", choices=["dark", "blue", "light"])
    parser.add_argument("--font-size", choices=["small", "medium", "large"],
                        help="Font size tier (default: large for mobile, medium for desktop)")
    parser.add_argument("--layout", choices=["desktop", "mobile"], default="desktop",
                        help="Layout profile: desktop (A4) or mobile (iPhone 17, 4.0×8.67in)")
    parser.add_argument("--output", help="Output file or base path")
    parser.add_argument("--same-dir", action="store_true", help="Write outputs next to input file")
    parser.add_argument("--keep-html", action="store_true", help="Keep intermediate HTML")
    parser.add_argument("--keep-clean", action="store_true", help="Keep normalized markdown if generated")
    parser.add_argument("--stdout-manifest", action="store_true", help="Print JSON manifest")
    parser.add_argument("--engine", choices=["auto", "pandoc", "marked", "fallback"], default="auto")
    parser.add_argument("--normalize", choices=["auto", "always", "never"], default="auto")
    parser.add_argument("--pdf-backend", choices=["auto", "html"], default="auto")
    args = parser.parse_args()

    start = time.time()
    warnings: list[str] = []
    errors: list[str] = []
    files: list[str] = []
    intermediate_files: list[str] = []
    template_used: str | None = None
    engine = {"markdown_to_html": "n/a", "html_to_pdf": "n/a", "html_to_png": "n/a"}
    normalization: dict[str, object] = {"performed": False, "agent_required": False, "clean_file": None}
    inspection_payload: dict[str, object] = {}

    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    actual_mode = "report" if args.mode in {"auto", "report"} else "card"
    if actual_mode == "card":
        raise SystemExit("card mode is not implemented in this CLI yet; use SVG workflow from SKILL.md")

    # Default font-size: large for mobile layout, medium for desktop
    effective_font_size = args.font_size or ("large" if args.layout == "mobile" else "medium")

    requested_format = args.format or "pdf"
    if requested_format == "html":
        requested_format = "pdf" if args.mode == "auto" else "html"
    resolved_theme = _resolve_theme(args.theme, requested_format)
    _ = _resolve_pdf_backend(args.pdf_backend)

    output_base = _resolve_output_base(input_path, args.output, args.same_dir)
    output_base.parent.mkdir(parents=True, exist_ok=True)

    try:
        warnings.extend(_check_dependencies(requested_format))
        inspection = inspect_markdown_file(input_path)
        inspection_payload = asdict(inspection)
        warnings.extend(inspection.warnings)
        if not inspection.ok:
            raise RuntimeError("; ".join(inspection.errors))
        if inspection.cleanliness == "semantic_dirty":
            normalization["agent_required"] = True
            raise RuntimeError("input requires agent semantic cleanup before export")

        render_input = input_path
        if args.normalize == "always" or (args.normalize == "auto" and inspection.cleanliness == "light_dirty"):
            clean_path = _derived_path(output_base, ".clean", ".md")
            normalized = normalize_markdown_file(input_path, clean_path)
            normalization = {
                "performed": True,
                "agent_required": False,
                "clean_file": str(clean_path),
                "changed": normalized.changed,
                "actions": normalized.actions,
                "detected": normalized.detected,
            }
            warnings.extend(normalized.warnings)
            if not normalized.ok:
                raise RuntimeError("; ".join(normalized.errors))
            render_input = clean_path
            if not args.keep_clean and clean_path.exists():
                # remove after render later
                pass
        elif args.normalize == "never":
            normalization["skipped"] = True

        if requested_format == "html":
            html_path = _derived_path(output_base, "_report", ".html")
            markdown_engine, html_warnings = render_markdown_to_html(
                render_input,
                html_path,
                theme=resolved_theme,
                font_size=effective_font_size,
                prefer_engine=args.engine,
                include_remote_fonts=False,
                layout=args.layout,
            )
            engine["markdown_to_html"] = markdown_engine
            warnings.extend(html_warnings)
            files.append(str(html_path))
            intermediate_files = []
        else:
            files, intermediate_files, engine, render_warnings = _render_report(
                render_input,
                output_base,
                requested_format,
                resolved_theme,
                effective_font_size,
                args.engine,
                args.keep_html,
                "_report",
                layout=args.layout,
            )
            warnings.extend(render_warnings)

        clean_file = normalization.get("clean_file")
        if clean_file and not args.keep_clean:
            clean_path = Path(str(clean_file))
            if clean_path.exists():
                clean_path.unlink()
                normalization["clean_file"] = None

    except Exception as exc:
        errors.append(str(exc))

    duration_ms = int((time.time() - start) * 1000)
    manifest = ConvertManifest(
        ok=not errors,
        input=str(input_path),
        mode=actual_mode,
        format=requested_format,
        layout=args.layout,
        files=files,
        theme=resolved_theme,
        font_size=effective_font_size,
        template_used=template_used,
        engine=engine,
        normalization=normalization,
        inspection=inspection_payload,
        intermediate_files=intermediate_files,
        render_ms=duration_ms,
        warnings=warnings,
        errors=errors,
    )

    if args.stdout_manifest:
        print(json.dumps(asdict(manifest), ensure_ascii=False))
    else:
        for file_path in files:
            print(file_path)
        for msg in errors:
            print(f"ERROR: {msg}", file=sys.stderr)

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
