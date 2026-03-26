"""Persist brief and full report files into a deep-research workspace.

Usage:
    omp-deep-research build-report --workspace "<workspace>" \
        --brief-file "<brief_md>" --full-report-file "<full_report_md>" \
        [--sources-file "<sources_json>"]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from common import dump_json, ensure_workspace_dirs, load_json, resolve_workspace


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Persist brief and full report into a workspace.")
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


def load_sources(sources_file: str | None) -> list[dict]:
    """Load sources array from a JSON file, or return empty list."""

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
    return data


def main() -> None:
    """Write report files, persist sources, and update state.json."""

    args = parse_args()
    workspace = resolve_workspace(args.workspace)
    paths = ensure_workspace_dirs(workspace)

    brief_text = resolve_text(args.brief_file, args.brief, "brief")
    full_report_text = resolve_text(args.full_report_file, args.full_report, "full-report")

    brief_file = paths.reports_dir / "brief.md"
    full_report_file = paths.reports_dir / "full-report.md"
    brief_file.write_text(brief_text, encoding="utf-8")
    full_report_file.write_text(full_report_text, encoding="utf-8")

    sources = load_sources(args.sources_file)
    if not sources:
        print("warning: no sources provided, report audit trail will be incomplete", file=sys.stderr)

    state = load_json(paths.state_file, default={})
    state["sources"] = sources
    state["completed_at"] = datetime.now().isoformat(timespec="seconds")
    state["report_files"] = {
        "brief": str(brief_file),
        "full_report": str(full_report_file),
    }
    state["status"] = "reported"
    dump_json(paths.state_file, state)

    print(
        json.dumps(
            {
                "status": "ok",
                "brief_file": str(brief_file),
                "full_report_file": str(full_report_file),
                "sources_count": len(sources),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
