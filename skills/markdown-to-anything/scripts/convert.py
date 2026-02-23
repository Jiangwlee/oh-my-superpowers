#!/usr/bin/env python3
"""CLI entrypoint for markdown-to-anything report rendering."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

# Allow direct script execution imports.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from report_render import render_markdown_to_pdf, render_markdown_to_png  # type: ignore  # noqa: E402
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


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Convert Markdown to PNG/PDF report assets")
    parser.add_argument("input", help="Input Markdown path")
    parser.add_argument("--mode", choices=["auto", "report"], default="auto")
    parser.add_argument("--format", choices=["png", "pdf", "both"], help="Output format")
    parser.add_argument("--theme", choices=["dark", "blue", "light"])
    parser.add_argument("--font-size", choices=["small", "medium", "large"], default="medium")
    parser.add_argument("--output", help="Output file or base path (without extension for both)")
    parser.add_argument("--stdout-manifest", action="store_true", help="Print JSON manifest")
    parser.add_argument("--engine", choices=["auto", "pandoc", "marked", "fallback"], default="auto")
    parser.add_argument(
        "--pdf-backend",
        choices=["auto", "html"],
        default="auto",
        help="PDF backend (auto currently uses html/chrome path)",
    )
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

    actual_mode = "report"
    requested_format = args.format or "pdf"
    resolved_theme = _resolve_theme(args.theme, requested_format)
    pdf_backend = _resolve_pdf_backend(args.pdf_backend)

    output_arg = Path(args.output).expanduser() if args.output else _default_output_base(input_path)
    if args.output and output_arg.suffix:
        output_base = output_arg.with_suffix("")
    else:
        output_base = output_arg
    output_base.parent.mkdir(parents=True, exist_ok=True)

    try:
        if requested_format in {"png", "both"}:
            png_path = output_base.with_name(output_base.name + "_report").with_suffix(".png")
            report_png_result = render_markdown_to_png(
                input_path,
                png_path,
                theme=resolved_theme,
                font_size=args.font_size,
                prefer_engine=args.engine,
            )
            markdown_engine = report_png_result.markdown_engine
            warnings.extend(report_png_result.warnings)
            files.append(str(png_path))

        if requested_format in {"pdf", "both"}:
            pdf_path = output_base.with_name(output_base.name + "_report").with_suffix(".pdf")
            report_result = render_markdown_to_pdf(
                input_path,
                pdf_path,
                theme=resolved_theme,
                font_size=args.font_size,
                prefer_engine=args.engine,
            )
            markdown_engine = report_result.markdown_engine
            warnings.extend(report_result.warnings)
            files.append(str(pdf_path))
        duration_ms = int((time.time() - start) * 1000)
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        errors.append(str(exc))

    manifest = ConvertManifest(
        mode=actual_mode,
        format=requested_format,
        files=files,
        theme=resolved_theme,
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
