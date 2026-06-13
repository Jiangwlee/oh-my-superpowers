#!/usr/bin/env python3
"""Render a filled skill-review Markdown report as a static HTML artifact.

Input:  a validated skill-review Markdown report.
Output: one static HTML file, optionally published under html-serve.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

OMP_HOME = Path(os.environ.get("OMP_HOME", str(Path(__file__).resolve().parents[3])))
sys.path.insert(0, str(OMP_HOME / "lib"))

from html_serve.core import build_url, resolve_config  # noqa: E402
from validate_review import collect_issues

CHECKBOX_PATTERN = re.compile(r"^- \[([✓✗—])\] (.+?)(?: → (.*))?$")
DIMENSION_PATTERN = re.compile(r"^###\s+([AB]\d+)\.\s+(.+?)\s+—\s+(.+?)\s*$")
SUBITEM_PATTERN = re.compile(r"^\s+- \*\*(标签|影响|修复|验证)\*\*[:：]\s*(.*)\s*$")
TITLE_PATTERN = re.compile(r"^#\s+skill-review:\s+(.+?)\s*$")
MECH_COUNT_PATTERN = re.compile(
    r"(?:机械检查原始计数|findings)：\s*(\d+)\s+CRITICAL\s+·\s+(\d+)\s+WARNING\s+·\s+(\d+)\s+SUGGESTION",
)


@dataclass
class Finding:
    """One failed checklist item extracted from the review report."""

    dimension: str
    dimension_title: str
    title: str
    evidence: str = ""
    tags: str = ""
    impact: str = ""
    fix: str = ""
    validation: str = ""
    lane: str = "Practice"


@dataclass
class ReviewReport:
    """Structured subset of a filled skill-review report."""

    skill_name: str
    review_path: str = ""
    review_scope: str = ""
    mechanical_counts: tuple[int, int, int] = (0, 0, 0)
    checkbox_counts: dict[str, int] = field(default_factory=lambda: {"pass": 0, "fail": 0, "na": 0})
    dimension_states: list[tuple[str, str, str]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


HTML_TEMPLATE = """<!doctype html>
<html lang=\"zh-CN\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>{title}</title>
<style>
:root {{
  --bg: #ffffff;
  --outer: #f5f5f5;
  --fg: #171717;
  --muted: #4d4d4d;
  --meta: #808080;
  --border: #e5e5e5;
  --soft: #fafafa;
  --accent: #0070f3;
  --danger: #d92d20;
  --warn: #b54708;
  --ok: #087443;
  --radius: 8px;
  --shadow: 0 0 0 1px rgba(0,0,0,.08), 0 8px 24px rgba(0,0,0,.04);
  --font-body: Inter, -apple-system, BlinkMacSystemFont, \"PingFang SC\", \"Segoe UI\", sans-serif;
  --font-mono: \"JetBrains Mono\", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--outer);
  color: var(--fg);
  font-family: var(--font-body);
  line-height: 1.55;
}}
.page {{
  width: min(1080px, calc(100vw - 32px));
  margin: 28px auto;
  background: var(--bg);
  box-shadow: var(--shadow);
  border-radius: 14px;
  overflow: hidden;
}}
header {{ padding: 46px 46px 34px; border-bottom: 1px solid var(--border); }}
.eyebrow {{
  font: 700 11px/1 var(--font-mono);
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--meta);
  margin-bottom: 16px;
}}
h1 {{
  max-width: 780px;
  margin: 0;
  font-size: clamp(36px, 5vw, 58px);
  line-height: .98;
  letter-spacing: -.055em;
}}
.deck {{ max-width: 720px; margin: 18px 0 0; color: var(--muted); font-size: 18px; }}
.score-row {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; padding: 22px 46px; border-bottom: 1px solid var(--border); background: var(--soft); }}
.metric {{ background: #fff; box-shadow: 0 0 0 1px rgba(0,0,0,.06), 0 2px 2px rgba(0,0,0,.03); border-radius: var(--radius); padding: 16px; }}
.metric strong {{ display: block; font: 700 28px/1 var(--font-mono); letter-spacing: -.04em; }}
.metric span {{ display: block; margin-top: 7px; color: var(--muted); font-size: 13px; }}
.metric.fail strong {{ color: var(--danger); }}
.metric.warn strong {{ color: var(--warn); }}
.metric.ok strong {{ color: var(--ok); }}
main {{ padding: 42px 46px 52px; }}
section + section {{ margin-top: 44px; }}
h2 {{ margin: 0 0 18px; font-size: 30px; line-height: 1.1; letter-spacing: -.035em; }}
.summary {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
.summary-card {{ border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; }}
.summary-card b {{ display: block; margin-bottom: 8px; }}
.summary-card p {{ margin: 0; color: var(--muted); font-size: 14px; }}
.findings {{ display: grid; gap: 12px; }}
.finding {{ border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; background: #fff; box-shadow: 0 0 0 1px rgba(0,0,0,.03); }}
.finding-head {{ display: grid; grid-template-columns: 112px minmax(0, 1fr); gap: 16px; }}
.severity {{ font: 700 11px/1 var(--font-mono); letter-spacing: .1em; text-transform: uppercase; }}
.severity.spec {{ color: var(--danger); }}
.severity.policy {{ color: var(--warn); }}
.severity.practice {{ color: var(--accent); }}
.finding h3 {{ margin: 0; font-size: 18px; line-height: 1.25; }}
.finding-meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
.pill {{ border: 1px solid var(--border); border-radius: 999px; padding: 4px 9px; color: var(--muted); font-size: 12px; }}
.detail-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }}
.detail {{ background: var(--soft); border-radius: var(--radius); padding: 12px; }}
.detail b {{ display: block; margin-bottom: 5px; font-size: 12px; color: var(--meta); text-transform: uppercase; letter-spacing: .08em; }}
.detail p {{ margin: 0; color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }}
.empty {{ border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; background: var(--soft); color: var(--muted); }}
.dimensions {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
.dimension {{ display: flex; justify-content: space-between; gap: 12px; border: 1px solid var(--border); border-radius: var(--radius); padding: 12px; font-size: 13px; }}
.state {{ font: 700 11px/1 var(--font-mono); letter-spacing: .08em; text-transform: uppercase; color: var(--meta); }}
.state.finding {{ color: var(--warn); }}
.state.pass {{ color: var(--ok); }}
footer {{ border-top: 1px solid var(--border); padding: 20px 46px; color: var(--meta); font-size: 12px; }}
@media (max-width: 820px) {{
  .page {{ width: min(100vw - 18px, 1080px); margin: 9px auto; }}
  header, main {{ padding-left: 22px; padding-right: 22px; }}
  .score-row {{ grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 18px 22px; }}
  .summary, .detail-grid, .dimensions, .finding-head {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<article class=\"page\">
  <header>
    <div class=\"eyebrow\">skill-review · default html artifact</div>
    <h1>{heading}</h1>
    <p class=\"deck\">Review summary for scanning filled checklist findings and follow-up actions.</p>
  </header>
  <div class=\"score-row\">
    <div class=\"metric {readiness_class}\"><strong>{readiness}</strong><span>Readiness score</span></div>
    <div class=\"metric fail\"><strong>{fail_count}</strong><span>Failed checks</span></div>
    <div class=\"metric ok\"><strong>{pass_count}</strong><span>Passed checks</span></div>
    <div class=\"metric warn\"><strong>{mechanical_total}</strong><span>Mechanical findings</span></div>
  </div>
  <main>
    <section>
      <h2>Review summary</h2>
      <div class=\"summary\">{summary_cards}</div>
    </section>
    <section>
      <h2>Findings</h2>
      <div class=\"findings\">{findings}</div>
    </section>
    <section>
      <h2>Dimension status</h2>
      <div class=\"dimensions\">{dimensions}</div>
    </section>
  </main>
  <footer>Generated by <code>omp skill-review render-html</code>. Markdown remains the source of truth.</footer>
</article>
</body>
</html>
"""


def _strip_markdown(text: str) -> str:
    """Remove light Markdown markers for card titles."""
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    return text.strip()


def _escape(text: str) -> str:
    """Escape text for HTML."""
    return html.escape(_strip_markdown(text), quote=True)


def parse_report(text: str) -> ReviewReport:
    """Parse the stable parts of a filled skill-review Markdown report."""
    skill_name = "unknown-skill"
    report = ReviewReport(skill_name=skill_name)
    current_dimension = ""
    current_dimension_title = ""
    current_finding: Finding | None = None

    for line in text.splitlines():
        title_match = TITLE_PATTERN.match(line)
        if title_match:
            report.skill_name = _strip_markdown(title_match.group(1))
            continue

        if line.startswith("审查路径："):
            report.review_path = _strip_markdown(line.split("：", 1)[1])
            continue
        if line.startswith("审查范围："):
            report.review_scope = _strip_markdown(line.split("：", 1)[1])
            continue

        count_match = MECH_COUNT_PATTERN.search(line)
        if count_match:
            report.mechanical_counts = tuple(int(count_match.group(i)) for i in range(1, 4))  # type: ignore[assignment]
            continue

        dimension_match = DIMENSION_PATTERN.match(line)
        if dimension_match:
            current_dimension = dimension_match.group(1)
            current_dimension_title = _strip_markdown(dimension_match.group(2))
            state = _strip_markdown(dimension_match.group(3))
            report.dimension_states.append((current_dimension, current_dimension_title, state))
            current_finding = None
            continue

        checkbox_match = CHECKBOX_PATTERN.match(line)
        if checkbox_match:
            marker, item, evidence = checkbox_match.groups()
            if marker == "✓":
                report.checkbox_counts["pass"] += 1
                current_finding = None
            elif marker == "—":
                report.checkbox_counts["na"] += 1
                current_finding = None
            elif marker == "✗":
                report.checkbox_counts["fail"] += 1
                current_finding = Finding(
                    dimension=current_dimension,
                    dimension_title=current_dimension_title,
                    title=_strip_markdown(item),
                    evidence=_strip_markdown(evidence or ""),
                )
                report.findings.append(current_finding)
            continue

        subitem_match = SUBITEM_PATTERN.match(line)
        if subitem_match and current_finding is not None:
            key, value = subitem_match.groups()
            value = _strip_markdown(value)
            if key == "标签":
                current_finding.tags = value
                current_finding.lane = _lane_from_tags(value)
            elif key == "影响":
                current_finding.impact = value
            elif key == "修复":
                current_finding.fix = value
            elif key == "验证":
                current_finding.validation = value

    return report


def _lane_from_tags(tags: str) -> str:
    """Map skill-review labels to a compact non-priority lane."""
    upper = tags.upper()
    if "SPEC" in upper:
        return "Spec"
    if "PROJECT_POLICY" in upper:
        return "Policy"
    return "Practice"


def _readiness(report: ReviewReport) -> tuple[str, str]:
    """Compute a simple readiness score from filled checklist counts."""
    passed = report.checkbox_counts["pass"]
    failed = report.checkbox_counts["fail"]
    applicable = passed + failed
    if applicable == 0:
        return "N/A", "warn"
    score = round((passed / applicable) * 10, 1)
    klass = "ok" if score >= 8 else "warn" if score >= 6 else "fail"
    return f"{score:.1f}", klass


def _render_summary_cards(report: ReviewReport) -> str:
    critical, warning, suggestion = report.mechanical_counts
    cards = [
        ("Primary action", _primary_action(report)),
        ("Mechanical checks", f"{critical} critical · {warning} warning · {suggestion} suggestion."),
        ("Output contract", "Markdown remains source of truth; this HTML page is the shareable triage artifact."),
    ]
    return "".join(
        f"<div class=\"summary-card\"><b>{_escape(title)}</b><p>{_escape(body)}</p></div>"
        for title, body in cards
    )


def _primary_action(report: ReviewReport) -> str:
    if not report.findings:
        return "No failed checklist items were found. Confirm evidence quality, then deploy."
    return f"Review {len(report.findings)} finding(s), then rerun validation."


def _render_findings(report: ReviewReport) -> str:
    if not report.findings:
        return '<div class="empty">No failed checklist items detected in the filled report.</div>'

    rendered: list[str] = []
    for finding in report.findings:
        lane_class = finding.lane.lower()
        details = [
            ("Evidence", finding.evidence or "Not provided"),
            ("Impact", finding.impact or "Not provided"),
            ("Fix", finding.fix or "Not provided"),
            ("Validation", finding.validation or "Not provided"),
        ]
        detail_html = "".join(
            f"<div class=\"detail\"><b>{_escape(label)}</b><p>{_escape(value)}</p></div>"
            for label, value in details
        )
        tags = finding.tags or "Unlabeled"
        rendered.append(
            "<article class=\"finding\">"
            "<div class=\"finding-head\">"
            f"<div class=\"severity {lane_class}\">{_escape(finding.lane)}</div>"
            "<div>"
            f"<h3>{_escape(finding.title)}</h3>"
            "<div class=\"finding-meta\">"
            f"<span class=\"pill\">{_escape(finding.dimension)} · {_escape(finding.dimension_title)}</span>"
            f"<span class=\"pill\">{_escape(tags)}</span>"
            "</div>"
            "</div>"
            "</div>"
            f"<div class=\"detail-grid\">{detail_html}</div>"
            "</article>"
        )
    return "".join(rendered)


def _render_dimensions(report: ReviewReport) -> str:
    if not report.dimension_states:
        return '<div class="empty">No dimension headings were found.</div>'
    rendered: list[str] = []
    for code, title, state in report.dimension_states:
        state_class = "finding" if state.upper() == "FINDING" else "pass" if state.upper() == "PASS" else ""
        rendered.append(
            "<div class=\"dimension\">"
            f"<span>{_escape(code)} · {_escape(title)}</span>"
            f"<span class=\"state {state_class}\">{_escape(state)}</span>"
            "</div>"
        )
    return "".join(rendered)


def render_html(report: ReviewReport) -> str:
    """Render a parsed report as a self-contained HTML document."""
    readiness, readiness_class = _readiness(report)
    mechanical_total = sum(report.mechanical_counts)
    heading = f"skill-review: {report.skill_name}"
    return HTML_TEMPLATE.format(
        title=_escape(heading),
        heading=_escape(heading),
        readiness=readiness,
        readiness_class=readiness_class,
        fail_count=report.checkbox_counts["fail"],
        pass_count=report.checkbox_counts["pass"],
        mechanical_total=mechanical_total,
        summary_cards=_render_summary_cards(report),
        findings=_render_findings(report),
        dimensions=_render_dimensions(report),
    )


def _slugify(value: str) -> str:
    """Return a filesystem-safe slug."""
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._")
    return slug.lower() or "skill-review"


def _is_relative_to(path: Path, parent: Path) -> bool:
    """Compatibility wrapper for Path.is_relative_to."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _publish_urls(
    output_path: Path,
    data_dir: Path,
    localhost_base_url: str | None,
    tailscale_base_url: str | None,
    legacy_base_url: str | None,
) -> dict[str, str]:
    """Build localhost and Tailscale html-serve URLs for a published file."""
    rel = output_path.resolve().relative_to(data_dir.resolve()).as_posix()
    config = resolve_config(
        omp_home=OMP_HOME,
        data_dir=str(data_dir),
        localhost_base_url=localhost_base_url,
        tailscale_base_url=tailscale_base_url or legacy_base_url,
    )
    localhost_url = build_url(config.localhost_base_url, rel)
    tailscale_url = build_url(config.tailscale_base_url, rel) if config.tailscale_base_url else ""
    return {
        "localhost_url": localhost_url,
        "tailscale_url": tailscale_url,
        "url": tailscale_url or localhost_url,
    }


def resolve_output_path(
    report_path: Path,
    output: str | None,
    publish: bool,
    project: str,
    data_dir: str | None,
) -> tuple[Path, Path | None]:
    """Resolve output path and optional html-serve data dir."""
    if not publish:
        return Path(output).resolve() if output else report_path.with_suffix(".html").resolve(), None

    if not data_dir:
        print(
            "Error: --publish requires HTML_SERVE_DATA_DIR or --data-dir.",
            file=sys.stderr,
        )
        sys.exit(2)

    root = Path(data_dir).expanduser().resolve()
    if output:
        output_path = Path(output).expanduser().resolve()
        if not _is_relative_to(output_path, root):
            print(
                "Error: --output must be under HTML_SERVE_DATA_DIR when --publish is used.",
                file=sys.stderr,
            )
            sys.exit(2)
        return output_path, root

    timestamp = datetime.now().strftime("%Y-%m-%dT%H%M")
    filename = f"{timestamp}-{_slugify(report_path.stem)}.html"
    return root / _slugify(project) / "skill-review" / filename, root


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Render a filled skill-review Markdown report as static HTML.",
    )
    parser.add_argument("report", help="Path to a filled skill-review Markdown report.")
    parser.add_argument("--output", help="Path to write the HTML file.")
    parser.add_argument("--publish", action="store_true", help="Write under html-serve and print URL metadata.")
    parser.add_argument(
        "--project",
        default=Path.cwd().name,
        help="Project namespace used when --publish chooses the output path.",
    )
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("HTML_SERVE_DATA_DIR"),
        help="html-serve data root. Defaults to HTML_SERVE_DATA_DIR.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("HTML_SERVE_BASE_URL"),
        help="Legacy public html-serve base URL. Prefer --tailscale-base-url.",
    )
    parser.add_argument(
        "--localhost-base-url",
        default=None,
        help="Localhost html-serve base URL. Defaults to http://localhost:HTML_SERVE_PORT.",
    )
    parser.add_argument(
        "--tailscale-base-url",
        default=os.environ.get("HTML_SERVE_TAILSCALE_BASE_URL"),
        help="Tailscale html-serve base URL. Defaults to env or automatic Tailscale detection.",
    )
    args = parser.parse_args()

    report_path = Path(args.report).expanduser().resolve()
    if not report_path.is_file():
        print(f"Error: report not found: {report_path}", file=sys.stderr)
        sys.exit(2)

    report_text = report_path.read_text(encoding="utf-8")
    validation_issues = collect_issues(report_text)
    if validation_issues:
        print(f"Error: report failed validation: {report_path}", file=sys.stderr)
        for issue in validation_issues:
            print(f"  {issue}", file=sys.stderr)
        sys.exit(1)

    report = parse_report(report_text)
    output_path, data_root = resolve_output_path(
        report_path=report_path,
        output=args.output,
        publish=args.publish,
        project=args.project,
        data_dir=args.data_dir,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(report), encoding="utf-8")

    result: dict[str, str] = {"html_path": str(output_path)}
    if args.publish and data_root is not None:
        result.update(
            _publish_urls(
                output_path,
                data_root,
                args.localhost_base_url,
                args.tailscale_base_url,
                args.base_url,
            )
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
