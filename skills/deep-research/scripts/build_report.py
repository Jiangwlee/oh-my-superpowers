"""Persist reports and render the HTML page for a deep-research workspace.

Usage:
    omp deep-research build-report --workspace "<workspace>" \
        --brief-file "<brief_md>" --full-report-file "<full_report_md>" \
        [--sources-file "<sources_json>"]
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from common import dump_json, ensure_workspace_dirs, load_json, resolve_workspace

URL_RE = re.compile(r"https?://[^\s)）>]+")
TRAILING_URL_PUNCT = ".,;:!?，。；：！？、"
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)、]\s+)(.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\[[ xX✓-]\]\s*")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Persist reports and render workspace HTML.")
    parser.add_argument("--workspace", required=True, help="Workspace directory.")
    parser.add_argument("--brief-file", help="Markdown file for brief output.")
    parser.add_argument("--full-report-file", help="Markdown file for full report output.")
    parser.add_argument("--brief", help="Inline brief markdown.")
    parser.add_argument("--full-report", help="Inline full report markdown.")
    parser.add_argument("--sources-file", help="JSON file containing sources array.")
    return parser.parse_args()


def resolve_text(file_arg: str | None, text_arg: str | None, label: str) -> str:
    """Return text from a file or inline argument."""

    if file_arg:
        return Path(file_arg).read_text(encoding="utf-8")
    if text_arg is not None:
        return text_arg
    raise ValueError(f"either --{label}-file or --{label} is required")


def load_sources(sources_file: str | None) -> list[dict[str, Any]]:
    """Load sources array from a JSON file, or return an empty list."""

    if not sources_file:
        return []
    path = Path(sources_file).expanduser().resolve()
    if not path.exists():
        print(f"warning: sources file not found: {path}", file=sys.stderr)
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"warning: failed to read sources file: {exc}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        print("warning: sources file must contain a JSON array", file=sys.stderr)
        return []
    return [item for item in data if isinstance(item, dict)]


def _template_path() -> Path:
    """Return the bundled HTML template path."""

    return Path(__file__).resolve().parents[1] / "assets" / "report-page-template.html"


def _escape(value: Any) -> str:
    """Escape a value for HTML text or attribute contexts."""

    return html.escape(str(value or ""), quote=True)


def _url_lookup_keys(url: str) -> list[str]:
    """Return URL variants that should resolve to the same source title."""

    cleaned = url.strip().rstrip(TRAILING_URL_PUNCT)
    if not cleaned:
        return []
    keys = [cleaned]
    if cleaned.endswith("/"):
        keys.append(cleaned.rstrip("/"))
    else:
        keys.append(f"{cleaned}/")
    return list(dict.fromkeys(keys))


def _source_title_map(sources: list[dict[str, Any]]) -> dict[str, str]:
    """Map source URLs to their recorded webpage titles."""

    titles: dict[str, str] = {}
    for source in sources:
        url = str(source.get("url") or "").strip()
        title = str(source.get("title") or "").strip()
        if not url or not title or title in _url_lookup_keys(url):
            continue
        for key in _url_lookup_keys(url):
            titles.setdefault(key, title)
    return titles


def _fallback_link_label(url: str) -> str:
    """Return a readable non-URL label when source metadata lacks a title."""

    parsed = urlsplit(url)
    if not parsed.netloc:
        return "Source link"
    slug = unquote(parsed.path.rstrip("/").rsplit("/", 1)[-1]) if parsed.path.rstrip("/") else ""
    if slug:
        slug = re.sub(r"[-_]+", " ", slug).strip()
        return f"{parsed.netloc} — {slug}" if slug else parsed.netloc
    return parsed.netloc


def _link_label(url: str, link_titles: dict[str, str] | None) -> str:
    """Return the best visible label for a link."""

    for key in _url_lookup_keys(url):
        if link_titles and key in link_titles:
            return link_titles[key]
    return _fallback_link_label(url)


def _escape_with_links(text: str, link_titles: dict[str, str] | None = None) -> str:
    """Escape text and turn bare URLs into safe external links with title labels."""

    parts: list[str] = []
    last = 0
    for match in URL_RE.finditer(text):
        parts.append(_escape(text[last : match.start()]))
        raw_url = match.group(0)
        url = raw_url.rstrip(TRAILING_URL_PUNCT)
        trailing = raw_url[len(url) :]
        label = _link_label(url, link_titles)
        parts.append(f'<a href="{_escape(url)}" target="_blank" rel="noreferrer">{_escape(label)}</a>')
        parts.append(_escape(trailing))
        last = match.end()
    parts.append(_escape(text[last:]))
    return "".join(parts)


def _heading_title(markdown: str, fallback: str) -> str:
    """Extract the first H1 title from Markdown."""

    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or fallback
    return fallback


def _section(markdown: str, names: list[str]) -> str:
    """Extract a level-2 Markdown section by exact or prefix heading name."""

    capture = False
    lines: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            if capture:
                break
            capture = any(title == name or title.startswith(name) for name in names)
            continue
        if capture:
            lines.append(line)
    return "\n".join(lines).strip()


def _list_items(markdown: str) -> list[str]:
    """Extract simple bullet or ordered-list items from Markdown text."""

    items: list[str] = []
    for line in markdown.splitlines():
        match = LIST_ITEM_RE.match(line)
        if not match:
            continue
        item = CHECKBOX_RE.sub("", match.group(1).strip())
        if item:
            items.append(item)
    return items


def _plain_text(markdown: str) -> str:
    """Return a compact plain-text approximation of a Markdown fragment."""

    text = re.sub(r"`([^`]+)`", r"\1", markdown)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_>#]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _truncate(text: str, limit: int) -> str:
    """Truncate text without adding noise to short strings."""

    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _first_clause(text: str) -> str:
    """Distill a conclusion into a compact card title."""

    cleaned = _plain_text(text)
    cleaned = re.sub(r"（来源[:：].*?）", "", cleaned)
    cleaned = re.sub(r"\(source[:：].*?\)", "", cleaned, flags=re.IGNORECASE)
    for sep in ["。", "；", ";", "，", ",", ":", "：", "—", " - "]:
        if sep in cleaned:
            cleaned = cleaned.split(sep, 1)[0]
            break
    return _truncate(cleaned.strip(" .。；;，,"), 28) or "Conclusion"


def _markdown_fragment(
    markdown: str,
    empty: str = "Not reported.",
    link_titles: dict[str, str] | None = None,
) -> str:
    """Render a small Markdown fragment as semantic HTML."""

    items = _list_items(markdown)
    if items:
        return "<ul>" + "".join(f"<li>{_escape_with_links(item, link_titles)}</li>" for item in items) + "</ul>"
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", markdown) if part.strip()]
    if not paragraphs:
        return f"<p>{_escape(empty)}</p>"
    return "".join(f"<p>{_escape_with_links(_plain_text(part), link_titles)}</p>" for part in paragraphs)


def _list_items_html(
    items: list[str],
    empty: str = "Not reported.",
    link_titles: dict[str, str] | None = None,
) -> str:
    """Render list items for a template marker already inside a ul."""

    if not items:
        return f"<li>{_escape(empty)}</li>"
    return "".join(f"<li>{_escape_with_links(item, link_titles)}</li>" for item in items)


def _conclusion_cards(brief_text: str, link_titles: dict[str, str] | None = None) -> str:
    """Render conclusion cards from the brief core-conclusions section."""

    section = _section(brief_text, ["核心结论", "Core Conclusions", "Conclusions"])
    conclusions = _list_items(section)
    if not conclusions:
        return '<div class="conclusion-card"><strong>Not reported</strong><p>No conclusions were reported.</p></div>'
    cards = []
    for conclusion in conclusions:
        cards.append(
            '<div class="conclusion-card">'
            f"<strong>{_escape(_first_clause(conclusion))}</strong>"
            f"<p>{_escape_with_links(_plain_text(conclusion), link_titles)}</p>"
            "</div>"
        )
    return "\n        ".join(cards)


def _source_evidence_from_report(full_report_text: str) -> dict[str, str]:
    """Extract source evidence summaries from the full-report source table."""

    section = _section(full_report_text, ["关键来源汇总", "Sources", "Source Summary"])
    evidence: dict[str, str] = {}
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"来源", "Source", "url", "URL"}:
            continue
        evidence[cells[0]] = cells[2]
    return evidence


def _source_rows(sources: list[dict[str, Any]], full_report_text: str) -> str:
    """Render source rows from state sources and full-report evidence summaries."""

    if not sources:
        return '<tr><td colspan="3">No sources reported.</td></tr>'
    evidence_map = _source_evidence_from_report(full_report_text)
    rows: list[str] = []
    for source in sources:
        url = str(source.get("url") or "").strip()
        if not url:
            continue
        title = str(source.get("title") or url).strip()
        platform = str(source.get("platform") or "unknown").strip()
        evidence = str(
            source.get("evidence_value")
            or source.get("evidence")
            or source.get("summary")
            or evidence_map.get(url)
            or "Source metadata recorded; see full report for context."
        ).strip()
        rows.append(
            "<tr>"
            f'<td><a href="{_escape(url)}" target="_blank" rel="noreferrer">{_escape(title)}</a></td>'
            f'<td class="platform">{_escape(platform)}</td>'
            f"<td>{_escape(evidence)}</td>"
            "</tr>"
        )
    if not rows:
        return '<tr><td colspan="3">No valid source URLs reported.</td></tr>'
    return "\n          ".join(rows)


def _language_for(text: str) -> str:
    """Infer the HTML language from visible CJK content."""

    return "zh-CN" if re.search(r"[\u4e00-\u9fff]", text) else "en"


def render_report_html(
    *,
    workspace: Path,
    brief_text: str,
    full_report_text: str,
    state: dict[str, Any],
    sources: list[dict[str, Any]],
) -> str:
    """Render the bundled HTML report template for a completed workspace."""

    template = _template_path()
    if not template.exists():
        raise FileNotFoundError(f"report template not found: {template}")

    topic = str(state.get("topic") or _heading_title(brief_text, workspace.name))
    goal = _section(full_report_text, ["研究目标", "Research Goal", "Goal"])
    risks = _list_items(_section(brief_text, ["关键分歧 / 风险", "关键分歧", "风险", "Risks"]))
    unresolved = _list_items(_section(full_report_text, ["未解决问题", "Open Questions", "Unresolved Questions"]))
    completed_at = str(state.get("completed_at") or datetime.now().isoformat(timespec="seconds"))
    deck = _truncate(_plain_text(goal), 180) if goal else "Readable projection of the completed deep-research workspace."
    link_titles = _source_title_map(sources)
    audit_note = (
        "Canonical audit artifacts: plan.md, reports/brief.md, reports/full-report.md, state.json. "
        f"Workspace: {workspace.name}."
    )

    replacements = {
        "{{LANG}}": _language_for(topic + brief_text + full_report_text),
        "{{REPORT_TITLE}}": _escape(topic),
        "{{REPORT_DECK}}": _escape(deck),
        "{{GENERATED_AT}}": _escape(completed_at),
        "{{SOURCE_COUNT}}": _escape(len(sources)),
        "{{STATUS}}": _escape(state.get("status") or "reported"),
        "{{RESEARCH_GOAL}}": _markdown_fragment(goal, link_titles=link_titles),
        "{{CONCLUSION_CARDS}}": _conclusion_cards(brief_text, link_titles),
        "{{RISK_ITEMS}}": _list_items_html(risks, link_titles=link_titles),
        "{{UNRESOLVED_ITEMS}}": _list_items_html(unresolved, link_titles=link_titles),
        "{{SOURCE_TABLE_ROWS}}": _source_rows(sources, full_report_text),
        "{{AUDIT_NOTE}}": _escape(audit_note),
    }

    rendered = template.read_text(encoding="utf-8")
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, str(value))
    leftovers = sorted(set(re.findall(r"{{[A-Z_]+}}", rendered)))
    if leftovers:
        raise RuntimeError(f"unreplaced report template markers: {', '.join(leftovers)}")
    return rendered


def main() -> None:
    """Write report files, render HTML, persist sources, and update state.json."""

    args = parse_args()
    workspace = resolve_workspace(args.workspace)
    paths = ensure_workspace_dirs(workspace)

    brief_text = resolve_text(args.brief_file, args.brief, "brief")
    full_report_text = resolve_text(args.full_report_file, args.full_report, "full-report")

    brief_file = paths.reports_dir / "brief.md"
    full_report_file = paths.reports_dir / "full-report.md"
    html_file = paths.reports_dir / "report.html"
    brief_file.write_text(brief_text, encoding="utf-8")
    full_report_file.write_text(full_report_text, encoding="utf-8")

    sources = load_sources(args.sources_file)
    if not sources:
        print("warning: no sources provided, report audit trail will be incomplete", file=sys.stderr)

    state = load_json(paths.state_file, default={})
    state["sources"] = sources
    state["completed_at"] = datetime.now().isoformat(timespec="seconds")
    state["status"] = "reported"
    rendered_html = render_report_html(
        workspace=workspace,
        brief_text=brief_text,
        full_report_text=full_report_text,
        state=state,
        sources=sources,
    )
    html_file.write_text(rendered_html, encoding="utf-8")
    state["report_files"] = {
        "brief": str(brief_file),
        "full_report": str(full_report_file),
        "html": str(html_file),
    }
    dump_json(paths.state_file, state)

    print(
        json.dumps(
            {
                "status": "ok",
                "brief_file": str(brief_file),
                "full_report_file": str(full_report_file),
                "html_file": str(html_file),
                "sources_count": len(sources),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
