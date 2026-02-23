#!/usr/bin/env python3
"""Validate generated SVG card layout (approximate + optional CDP bbox check)."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCREENSHOT_JS = SCRIPT_DIR / "screenshot.js"


@dataclass(slots=True)
class ValidationIssue:
    """Single validation issue."""

    level: str
    code: str
    message: str
    element_id: str | None = None


@dataclass(slots=True)
class ValidationResult:
    """Layout validation result."""

    ok: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    source: str


@dataclass(slots=True)
class BBox:
    """Simple rectangle."""

    x: float
    y: float
    width: float
    height: float


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _char_units(ch: str) -> float:
    if ch in {" ", "\t"}:
        return 0.45
    if unicodedata.east_asian_width(ch) in {"W", "F"}:
        return 1.0
    return 0.58


def _estimate_text_bbox(el: ET.Element) -> BBox | None:
    x = _parse_float(el.attrib.get("x", "0"))
    y = _parse_float(el.attrib.get("y", "0"))
    font_size = _parse_float(el.attrib.get("font-size", "44"), 44.0)
    style = el.attrib.get("style", "")
    if "display:none" in style:
        return None

    lines: list[str] = []
    if el.text and el.text.strip():
        lines.append(el.text)
    for child in list(el):
        if _local_name(child.tag) != "tspan":
            continue
        if child.text is not None:
            lines.append(child.text)
    if not lines:
        return None

    max_units = 0.0
    for line in lines:
        units = sum(_char_units(ch) for ch in line)
        if units > max_units:
            max_units = units
    width = max_units * font_size
    height = max(1, len(lines)) * font_size * 1.35
    top = y - font_size * 0.9
    return BBox(x=x, y=top, width=width, height=height)


def _estimate_shape_bbox(el: ET.Element) -> BBox | None:
    style = el.attrib.get("style", "")
    if "display:none" in style:
        return None
    tag = _local_name(el.tag)
    if tag == "rect":
        return BBox(
            x=_parse_float(el.attrib.get("x", "0")),
            y=_parse_float(el.attrib.get("y", "0")),
            width=_parse_float(el.attrib.get("width", "0")),
            height=_parse_float(el.attrib.get("height", "0")),
        )
    if tag == "circle":
        cx = _parse_float(el.attrib.get("cx", "0"))
        cy = _parse_float(el.attrib.get("cy", "0"))
        r = _parse_float(el.attrib.get("r", "0"))
        return BBox(x=cx - r, y=cy - r, width=r * 2, height=r * 2)
    if tag == "line":
        x1 = _parse_float(el.attrib.get("x1", "0"))
        x2 = _parse_float(el.attrib.get("x2", "0"))
        y1 = _parse_float(el.attrib.get("y1", "0"))
        y2 = _parse_float(el.attrib.get("y2", "0"))
        return BBox(x=min(x1, x2), y=min(y1, y2), width=abs(x2 - x1), height=max(1.0, abs(y2 - y1)))
    return None


def _intersect_area(a: BBox, b: BBox) -> float:
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(a.x + a.width, b.x + b.width)
    y2 = min(a.y + a.height, b.y + b.height)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return (x2 - x1) * (y2 - y1)


def validate_svg_file(svg_path: Path, overlap_threshold: float = 0.10) -> ValidationResult:
    """Validate SVG with approximate bounding boxes.

    Args:
        svg_path: SVG file path.
        overlap_threshold: Error if overlap / min(area_a, area_b) exceeds threshold.

    Returns:
        Validation result.
    """
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))

    width = _parse_float(root.attrib.get("width", "1080"), 1080.0)
    height = _parse_float(root.attrib.get("height", "1920"), 1920.0)

    boxes: list[tuple[str | None, str, BBox]] = []
    for el in root.iter():
        tag = _local_name(el.tag)
        bbox: BBox | None = None
        if tag == "text":
            bbox = _estimate_text_bbox(el)
        elif tag in {"rect", "circle", "line"}:
            bbox = _estimate_shape_bbox(el)
        if bbox is None:
            continue
        elem_id = el.attrib.get("id")
        boxes.append((elem_id, tag, bbox))
        if bbox.x < 0 or bbox.y < 0 or bbox.x + bbox.width > width or bbox.y + bbox.height > height:
            errors.append(
                ValidationIssue(
                    level="error",
                    code="out_of_bounds",
                    message=f"{tag} exceeds canvas bounds",
                    element_id=elem_id,
                )
            )

    for idx, (id_a, tag_a, box_a) in enumerate(boxes):
        area_a = max(1.0, box_a.width * box_a.height)
        if tag_a != "text":
            continue
        for id_b, tag_b, box_b in boxes[idx + 1 :]:
            if tag_b != "text":
                continue
            if id_a == id_b and id_a is not None:
                continue
            inter = _intersect_area(box_a, box_b)
            if inter <= 0:
                continue
            area_b = max(1.0, box_b.width * box_b.height)
            ratio = inter / min(area_a, area_b)
            if ratio > overlap_threshold:
                errors.append(
                    ValidationIssue(
                        level="error",
                        code="overlap",
                        message=f"Elements overlap ratio {ratio:.2f} > {overlap_threshold:.2f}",
                        element_id=id_a or id_b,
                    )
                )

    size_bytes = svg_path.stat().st_size
    if size_bytes > 3 * 1024 * 1024:
        warnings.append(
            ValidationIssue(level="warning", code="file_size", message="SVG file size exceeds 3MB")
        )

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings, source="approx")


def try_cdp_bbox_validate(svg_path: Path) -> ValidationResult | None:
    """Try optional Chrome/CDP validation via screenshot.js `--svg-validate`."""
    node = shutil.which("node")
    if not node or not SCREENSHOT_JS.exists():
        return None
    try:
        proc = subprocess.run(
            [node, str(SCREENSHOT_JS), "--svg-validate", str(svg_path.resolve())],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except Exception:
        return None
    errors = [ValidationIssue(level="error", **item) for item in data.get("errors", [])]
    warnings = [ValidationIssue(level="warning", **item) for item in data.get("warnings", [])]
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings, source="cdp")


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Validate markdown-to-anything SVG layout")
    parser.add_argument("input", help="SVG file path")
    parser.add_argument("--prefer-cdp", action="store_true", help="Use screenshot.js --svg-validate when available")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    svg_path = Path(args.input).expanduser()
    result = try_cdp_bbox_validate(svg_path) if args.prefer_cdp else None
    if result is None:
        result = validate_svg_file(svg_path)

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False))
    else:
        print(f"ok={result.ok} source={result.source} errors={len(result.errors)} warnings={len(result.warnings)}")
        for issue in result.errors + result.warnings:
            print(f"{issue.level}:{issue.code}:{issue.element_id or '-'}:{issue.message}")


if __name__ == "__main__":
    main()
