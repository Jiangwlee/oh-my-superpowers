#!/usr/bin/env python3
"""Render Markdown into a summary-card SVG using template skeletons."""

from __future__ import annotations

import argparse
import json
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = SCRIPT_DIR.parent / "templates"

# Register SVG as the default namespace so ElementTree writes clean <element> tags
# and so ET.SubElement tspan tags are correctly namespaced.
_SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", _SVG_NS)


THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "BG": "#0d1117",
        "BG2": "#161b22",
        "CARD_BG": "#1c2432",
        "ACCENT": "#58a6ff",
        "ACCENT_SOFT": "#1c2432",
        "TEXT": "#e6edf3",
        "MUTED": "#8b949e",
    },
    "blue": {
        "BG": "#0a1628",
        "BG2": "#10253e",
        "CARD_BG": "#0d2137",
        "ACCENT": "#4fc3f7",
        "ACCENT_SOFT": "#0d2137",
        "TEXT": "#e8f4fd",
        "MUTED": "#7bafd4",
    },
}

FONT_SIZES: dict[str, dict[str, int]] = {
    "small": {"BODY": 36, "H1": 54, "H2": 45, "H3": 40, "META": 28},
    "medium": {"BODY": 44, "H1": 66, "H2": 55, "H3": 48, "META": 34},
    "large": {"BODY": 52, "H1": 78, "H2": 65, "H3": 57, "META": 40},
}


@dataclass(slots=True)
class CardSpec:
    """Structured card data (LLM output equivalent for MVP)."""

    template: str
    title: str
    subtitle: str
    bullets: list[str]
    highlight: str
    theme: str = "dark"
    font_size: str = "medium"
    sections: list[dict[str, Any]] | None = None
    metrics: list[dict[str, str]] | None = None


@dataclass(slots=True)
class CardRenderResult:
    """Card SVG rendering result."""

    svg_path: str
    template_used: str
    warnings: list[str]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _iter_elements(root: ET.Element):
    for el in root.iter():
        yield el


def _char_units(ch: str) -> float:
    if ch in {" ", "\t"}:
        return 0.45
    if unicodedata.east_asian_width(ch) in {"W", "F"}:
        return 1.0
    return 0.58


def _truncate_to_units(text: str, max_units: float) -> str:
    total = 0.0
    out: list[str] = []
    for ch in text:
        unit = _char_units(ch)
        if total + unit > max_units:
            if out:
                return "".join(out).rstrip() + "…"
            return "…"
        out.append(ch)
        total += unit
    return "".join(out)


def _wrap_text(text: str, max_units_per_line: float, max_lines: int) -> list[str]:
    lines: list[str] = []
    current: list[str] = []
    current_units = 0.0
    for ch in text.strip():
        if ch == "\n":
            lines.append("".join(current).strip())
            current = []
            current_units = 0.0
            if len(lines) >= max_lines:
                return lines
            continue
        unit = _char_units(ch)
        if current and current_units + unit > max_units_per_line:
            lines.append("".join(current).strip())
            current = [ch]
            current_units = unit
            if len(lines) >= max_lines:
                break
        else:
            current.append(ch)
            current_units += unit
    if len(lines) < max_lines and current:
        lines.append("".join(current).strip())
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    if not lines:
        return [""]
    if len(lines) == max_lines:
        lines[-1] = _truncate_to_units(lines[-1], max_units_per_line)
    return lines


def _find_by_id(root: ET.Element, elem_id: str) -> ET.Element | None:
    for el in _iter_elements(root):
        if el.attrib.get("id") == elem_id:
            return el
    return None


def _set_text_lines(element: ET.Element, text: str, max_units: float, max_lines: int = 1) -> None:
    y_attr = element.attrib.get("y", "0")
    x_attr = element.attrib.get("x", "0")
    font_size = float(element.attrib.get("font-size", "44"))
    base_y = float(y_attr)
    lines = _wrap_text(text, max_units_per_line=max_units, max_lines=max_lines)
    element.text = None
    for child in list(element):
        element.remove(child)
    if len(lines) == 1:
        element.text = lines[0]
        return
    for i, line in enumerate(lines):
        tspan = ET.SubElement(element, f"{{{_SVG_NS}}}tspan")
        tspan.set("x", x_attr)
        tspan.set("y", str(base_y + i * (font_size * 1.35)))
        tspan.text = line


def _hide_element(root: ET.Element, elem_id: str) -> None:
    el = _find_by_id(root, elem_id)
    if el is None:
        return
    style = el.attrib.get("style", "")
    if style and not style.endswith(";"):
        style += ";"
    el.attrib["style"] = style + "display:none"


def _extract_card_spec_from_markdown(text: str, template: str, theme: str, font_size: str) -> CardSpec:
    title = "Markdown Summary"
    subtitle = "Auto-generated card"
    bullets: list[str] = []
    headings: list[str] = []
    paragraphs: list[str] = []
    metrics: list[dict[str, str]] = []

    in_code = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line:
            continue
        if line.startswith("# ") and title == "Markdown Summary":
            title = line[2:].strip() or title
            continue
        if line.startswith("## ") or line.startswith("### "):
            headings.append(line.split(" ", 1)[1].strip())
            continue
        if line.startswith("- ") or line.startswith("* "):
            bullets.append(line[2:].strip())
            continue
        if "|" in line and not line.startswith("|"):
            # likely prose with vertical bars; ignore as metric source.
            paragraphs.append(line)
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2 and all(cells):
                if any(ch not in {":", "-", " "} for ch in "".join(cells)):
                    metrics.append({"label": cells[0][:20], "value": cells[1][:20]})
                continue
        paragraphs.append(line)

    if headings and subtitle == "Auto-generated card":
        subtitle = headings[0]
    elif paragraphs:
        subtitle = paragraphs[0][:40]

    if not bullets:
        bullets = paragraphs[:4]
    if not bullets:
        bullets = ["(No bullets found)"]

    highlight = paragraphs[1] if len(paragraphs) > 1 else (bullets[0] if bullets else "")
    highlight = highlight[:80] if highlight else "No highlight"

    sections: list[dict[str, Any]] | None = None
    if template == "headline-list":
        sections = []
        bucket_names = headings[:3] if headings else ["Section A", "Section B", "Section C"]
        if len(bucket_names) < 3:
            bucket_names.extend([f"Section {chr(ord('A') + i)}" for i in range(len(bucket_names), 3)])
        for idx in range(3):
            items = bullets[idx * 3 : (idx + 1) * 3]
            if not items:
                items = paragraphs[idx * 2 : idx * 2 + 2]
            sections.append({"title": bucket_names[idx], "items": items[:4]})

    if template == "metrics-grid":
        if not metrics:
            metrics = []
            seeds = headings + bullets + paragraphs
            for idx in range(4):
                label = f"Metric {idx + 1}"
                value = seeds[idx][:10] if idx < len(seeds) else "--"
                metrics.append({"label": label, "value": value})
        metrics = metrics[:4]
        if len(metrics) < 4:
            metrics.extend({"label": f"Metric {i+1}", "value": "--"} for i in range(len(metrics), 4))

    return CardSpec(
        template=template,
        title=title,
        subtitle=subtitle,
        bullets=bullets[:6],
        highlight=highlight,
        theme=theme,
        font_size=font_size,
        sections=sections,
        metrics=metrics if metrics else None,
    )


def _load_template_text(template_name: str, theme: str, font_size: str) -> str:
    template_path = TEMPLATE_DIR / f"{template_name}.svg"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    text = template_path.read_text(encoding="utf-8")
    tokens = {}
    tokens.update(THEMES[theme])
    tokens.update({k: str(v) for k, v in FONT_SIZES[font_size].items()})
    for key, value in tokens.items():
        text = text.replace("{{" + key + "}}", value)
    # Optional token used by some templates.
    text = text.replace("{{BG2}}", THEMES[theme].get("BG", "#000000"))
    return text


def render_card_svg(spec: CardSpec, output_path: Path) -> CardRenderResult:
    """Render a card SVG from a structured spec.

    Args:
        spec: Card specification.
        output_path: SVG output path.

    Returns:
        Render result containing output path and warnings.
    """
    warnings: list[str] = []
    if spec.theme not in THEMES:
        raise ValueError(f"Unsupported theme: {spec.theme}")
    if spec.font_size not in FONT_SIZES:
        raise ValueError(f"Unsupported font size: {spec.font_size}")

    svg_text = _load_template_text(spec.template, spec.theme, spec.font_size)
    root = ET.fromstring(svg_text)

    # Compute max character-units per line based on actual available pixel width.
    # The validator uses width = max_units * font_size, so to stay within bounds:
    #   max_units <= (right_edge - x_start - pad) / font_size_px
    fs = FONT_SIZES[spec.font_size]

    def _mu(right_px: int, x_px: int, font_key: str, pad: int = 12) -> int:
        """Max character-units for a text element at x_px within right_px."""
        avail = right_px - x_px - pad
        return max(6, int(avail / fs[font_key]))

    # Canvas = 1080. Safe right boundary (56px right pad) = 1024.
    R = 1024

    title_el = _find_by_id(root, "title")
    if title_el is None:
        raise ValueError(f"Template missing required element id=title: {spec.template}")
    title_x = int(float(title_el.attrib.get("x", "96")))
    _set_text_lines(title_el, spec.title, _mu(R, title_x, "H1"), 2)

    subtitle_el = _find_by_id(root, "subtitle")
    if subtitle_el is not None:
        sub_x = int(float(subtitle_el.attrib.get("x", "96")))
        _set_text_lines(subtitle_el, spec.subtitle, _mu(R, sub_x, "META"), 2)

    template = spec.template
    if template == "hero-summary":
        for idx in range(6):
            bullet_el = _find_by_id(root, f"bullet_{idx + 1}")
            if bullet_el is None:
                continue
            if idx < len(spec.bullets):
                bx = int(float(bullet_el.attrib.get("x", "148")))
                _set_text_lines(bullet_el, spec.bullets[idx], _mu(R, bx, "BODY"), 2)
            else:
                _hide_element(root, f"bullet_{idx + 1}")
                _hide_element(root, f"bullet_dot_{idx + 1}")
        highlight_el = _find_by_id(root, "highlight")
        if highlight_el is not None:
            # highlight box: x=96, width=888 → right=984
            hx = int(float(highlight_el.attrib.get("x", "136")))
            _set_text_lines(highlight_el, spec.highlight, _mu(984, hx, "H3"), 3)
    elif template == "headline-list":
        sections = spec.sections or []
        for idx in range(3):
            sec = sections[idx] if idx < len(sections) else {"title": "", "items": []}
            section_el = _find_by_id(root, f"section_{idx + 1}")
            items_el = _find_by_id(root, f"items_{idx + 1}")
            if section_el is not None:
                sx = int(float(section_el.attrib.get("x", "88")))
                _set_text_lines(section_el, str(sec.get("title", "")), _mu(R, sx, "H3"), 1)
            if items_el is not None:
                ix = int(float(items_el.attrib.get("x", "88")))
                items = sec.get("items", [])
                joined = "\n".join(f"• {str(item)}" for item in items[:5])
                _set_text_lines(items_el, joined, _mu(R, ix, "BODY"), 6)
    elif template == "metrics-grid":
        metrics = spec.metrics or []
        # Left column cards: x=72 w=450 → right=522; text starts at x=108
        # Right column cards: x=558 w=450 → right=1008; text starts at x=594
        card_rights = [522, 1008, 522, 1008]
        card_text_xs = [108, 594, 108, 594]
        for idx in range(4):
            data = metrics[idx] if idx < len(metrics) else {"label": f"Metric {idx+1}", "value": "--"}
            label_el = _find_by_id(root, f"metric_label_{idx + 1}")
            value_el = _find_by_id(root, f"metric_value_{idx + 1}")
            cr = card_rights[idx]
            cx = card_text_xs[idx]
            if label_el is not None:
                _set_text_lines(label_el, str(data.get("label", "")), _mu(cr, cx, "META"), 2)
            if value_el is not None:
                _set_text_lines(value_el, str(data.get("value", "")), _mu(cr, cx, "H2"), 2)
        # Big lower box: x=72 w=936 → right=1008; text at x=108
        bullets_el = _find_by_id(root, "bullets")
        if bullets_el is not None:
            bx = int(float(bullets_el.attrib.get("x", "108")))
            joined = "\n".join(f"• {line}" for line in spec.bullets[:6])
            _set_text_lines(bullets_el, joined, _mu(1008, bx, "BODY"), 10)
        highlight_el = _find_by_id(root, "highlight")
        if highlight_el is not None:
            hx = int(float(highlight_el.attrib.get("x", "108")))
            _set_text_lines(highlight_el, spec.highlight, _mu(1008, hx, "H3"), 2)
    elif template == "quote-and-bullets":
        # Quote box: x=64 w=952 → right=1016; text at x=136
        highlight_el = _find_by_id(root, "highlight")
        if highlight_el is not None:
            hx = int(float(highlight_el.attrib.get("x", "136")))
            _set_text_lines(highlight_el, spec.highlight, _mu(1016, hx, "H2"), 5)
        bullets_el = _find_by_id(root, "bullets")
        if bullets_el is not None:
            bx = int(float(bullets_el.attrib.get("x", "72")))
            joined = "\n".join(f"• {line}" for line in spec.bullets[:8])
            _set_text_lines(bullets_el, joined, _mu(R, bx, "BODY"), 14)
    else:
        warnings.append(f"Unknown template-specific layout handler: {template}")

    footer_el = _find_by_id(root, "footer")
    if footer_el is not None:
        footer_el.text = f"markdown-to-anything · {spec.template}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)
    return CardRenderResult(svg_path=str(output_path), template_used=spec.template, warnings=warnings)


def render_markdown_to_card_svg(
    markdown_path: Path,
    output_svg: Path,
    template: str,
    theme: str = "dark",
    font_size: str = "medium",
) -> CardRenderResult:
    """Render Markdown file to SVG card using deterministic MVP extraction."""
    spec = _extract_card_spec_from_markdown(
        markdown_path.read_text(encoding="utf-8"),
        template=template,
        theme=theme,
        font_size=font_size,
    )
    return render_card_svg(spec, output_svg)


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Render markdown summary card SVG")
    parser.add_argument("input", help="Input Markdown path")
    parser.add_argument("--output", required=True, help="Output SVG path")
    parser.add_argument("--template", default="hero-summary", choices=[
        "hero-summary", "headline-list", "metrics-grid", "quote-and-bullets"
    ])
    parser.add_argument("--theme", default="dark", choices=["dark", "blue"])
    parser.add_argument("--font-size", default="medium", choices=["small", "medium", "large"])
    parser.add_argument("--spec-json", help="Optional JSON spec file to bypass markdown extraction")
    parser.add_argument("--stdout-result", action="store_true", help="Print result JSON")
    args = parser.parse_args()

    output_path = Path(args.output).expanduser()
    if args.spec_json:
        raw = json.loads(Path(args.spec_json).expanduser().read_text(encoding="utf-8"))
        spec = CardSpec(**raw)
        result = render_card_svg(spec, output_path)
    else:
        result = render_markdown_to_card_svg(
            Path(args.input).expanduser(),
            output_path,
            template=args.template,
            theme=args.theme,
            font_size=args.font_size,
        )
    if args.stdout_result:
        print(json.dumps(asdict(result), ensure_ascii=False))
    else:
        print(result.svg_path)


if __name__ == "__main__":
    main()
