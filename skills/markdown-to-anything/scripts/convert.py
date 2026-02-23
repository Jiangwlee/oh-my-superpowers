#!/usr/bin/env python3
"""CLI entrypoint for markdown-to-anything dual-channel rendering."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

# Allow direct script execution imports.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze import analyze_markdown_file  # type: ignore  # noqa: E402
from card_render import render_markdown_to_card_svg  # type: ignore  # noqa: E402
from report_render import render_markdown_to_html, render_markdown_to_pdf  # type: ignore  # noqa: E402
from validator import validate_svg_file, try_cdp_bbox_validate  # type: ignore  # noqa: E402


SCREENSHOT_JS = SCRIPT_DIR / "screenshot.js"
OPENCLAW_MEDIA_ROOT = Path.home() / ".openclaw" / "media" / "markdown-to-anything"


@dataclass(slots=True)
class ConvertManifest:
    """stdout manifest structure."""

    mode: str
    format: str
    files: list[str]
    theme: str
    font_size: str
    template_used: str | None
    markdown_engine: str
    render_ms: int
    warnings: list[str]
    errors: list[str]


def _default_output_base(input_path: Path) -> Path:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return OPENCLAW_MEDIA_ROOT / timestamp / input_path.stem


def _render_svg_to_png(svg_path: Path, output_png: Path) -> list[str]:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node not found; cannot render SVG to PNG")
    if not SCREENSHOT_JS.exists():
        raise RuntimeError(f"screenshot.js not found: {SCREENSHOT_JS}")
    proc = subprocess.run(
        [node, str(SCREENSHOT_JS), "--png", str(svg_path.resolve()), str(output_png.resolve()), "3", "1080", "0"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "screenshot.js --png failed")
    return [str(output_png)]


def _mode_to_default_format(mode: str) -> str:
    return "png" if mode == "card" else "pdf"


def _normalize_requested_format(mode: str, requested_format: str | None) -> str:
    if requested_format:
        return requested_format
    return _mode_to_default_format(mode)


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Convert Markdown to PNG/PDF summary/report assets")
    parser.add_argument("input", help="Input Markdown path")
    parser.add_argument("--mode", choices=["auto", "card", "report"], default="auto")
    parser.add_argument("--format", choices=["png", "pdf", "both"], help="Output format")
    parser.add_argument("--theme", choices=["dark", "blue"], default="dark")
    parser.add_argument("--font-size", choices=["small", "medium", "large"], default="medium")
    parser.add_argument("--output", help="Output file or base path (without extension for both)")
    parser.add_argument("--stdout-manifest", action="store_true", help="Print JSON manifest")
    parser.add_argument("--template", help="Force card template")
    parser.add_argument("--prefer-cdp-validator", action="store_true")
    parser.add_argument("--engine", choices=["auto", "pandoc", "marked", "fallback"], default="auto")
    args = parser.parse_args()

    start = time.time()
    warnings: list[str] = []
    errors: list[str] = []
    files: list[str] = []
    template_used: str | None = None
    markdown_engine = "n/a"

    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    analysis = analyze_markdown_file(input_path)
    actual_mode = analysis.mode_auto if args.mode == "auto" else args.mode
    requested_format = _normalize_requested_format(actual_mode, args.format)

    if actual_mode == "card" and requested_format == "pdf":
        warnings.append("card mode with pdf requested: generating report PDF instead")
        actual_mode = "report"
    if actual_mode == "report" and requested_format == "png":
        warnings.append("report mode with png requested: generating card PNG instead")
        actual_mode = "card"

    output_arg = Path(args.output).expanduser() if args.output else _default_output_base(input_path)
    if args.output and output_arg.suffix:
        output_base = output_arg.with_suffix("")
    else:
        output_base = output_arg
    output_base.parent.mkdir(parents=True, exist_ok=True)

    try:
        if actual_mode == "card":
            template_used = args.template or analysis.template_auto
            svg_path = output_base.with_name(output_base.name + "_card").with_suffix(".svg")
            card_result = render_markdown_to_card_svg(
                input_path,
                svg_path,
                template=template_used,
                theme=args.theme,
                font_size=args.font_size,
            )
            warnings.extend(card_result.warnings)
            validator_result = None
            if args.prefer_cdp_validator:
                validator_result = try_cdp_bbox_validate(svg_path)
            if validator_result is None:
                validator_result = validate_svg_file(svg_path)
            warnings.extend(issue.message for issue in validator_result.warnings)
            if not validator_result.ok:
                # Validation issues are non-fatal: warn and proceed to render.
                for issue in validator_result.errors:
                    warnings.append(f"[layout] {issue.message} (id={issue.element_id})")

            if requested_format in {"png", "both"}:
                png_path = output_base.with_name(output_base.name + "_card").with_suffix(".png")
                files.extend(_render_svg_to_png(svg_path, png_path))
            else:
                files.append(str(svg_path))

            if requested_format == "both":
                pdf_path = output_base.with_name(output_base.name + "_report").with_suffix(".pdf")
                report_result = render_markdown_to_pdf(
                    input_path,
                    pdf_path,
                    theme=args.theme,
                    font_size=args.font_size,
                    prefer_engine=args.engine,
                )
                markdown_engine = report_result.markdown_engine
                warnings.extend(report_result.warnings)
                files.append(str(pdf_path))
            else:
                markdown_engine = "n/a"

        else:
            if requested_format in {"pdf", "both"}:
                pdf_path = output_base.with_name(output_base.name + "_report").with_suffix(".pdf")
                report_result = render_markdown_to_pdf(
                    input_path,
                    pdf_path,
                    theme=args.theme,
                    font_size=args.font_size,
                    prefer_engine=args.engine,
                )
                markdown_engine = report_result.markdown_engine
                warnings.extend(report_result.warnings)
                files.append(str(pdf_path))
            else:
                html_path = output_base.with_name(output_base.name + "_report").with_suffix(".html")
                engine, html_warnings = render_markdown_to_html(
                    input_path,
                    html_path,
                    theme=args.theme,
                    font_size=args.font_size,
                    prefer_engine=args.engine,
                )
                markdown_engine = engine
                warnings.extend(html_warnings)
                files.append(str(html_path))

            if requested_format == "both":
                template_used = args.template or analysis.template_auto
                svg_path = output_base.with_name(output_base.name + "_card").with_suffix(".svg")
                render_markdown_to_card_svg(
                    input_path,
                    svg_path,
                    template=template_used,
                    theme=args.theme,
                    font_size=args.font_size,
                )
                validator_result = validate_svg_file(svg_path)
                warnings.extend(issue.message for issue in validator_result.warnings)
                if validator_result.ok:
                    png_path = output_base.with_name(output_base.name + "_card").with_suffix(".png")
                    files.insert(0, str(png_path))
                    _render_svg_to_png(svg_path, png_path)
                else:
                    warnings.append("card validation failed in report/both path; skipped PNG")
        duration_ms = int((time.time() - start) * 1000)
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        errors.append(str(exc))

    manifest = ConvertManifest(
        mode=actual_mode,
        format=requested_format,
        files=files,
        theme=args.theme,
        font_size=args.font_size,
        template_used=template_used,
        markdown_engine=markdown_engine,
        render_ms=duration_ms,
        warnings=warnings,
        errors=errors,
    )

    if args.stdout_manifest:
        print(json.dumps(asdict(manifest), ensure_ascii=False))
    else:
        for file_path in files:
            print(file_path)
        if errors:
            for msg in errors:
                print(f"ERROR: {msg}", file=sys.stderr)

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
