"""Persist brief and full report files into a deep-research workspace.

Usage:
    omp-deep-research build-report --workspace "<workspace>" --brief-file "<brief_md>" --full-report-file "<full_report_md>"
"""

from __future__ import annotations

import argparse
import json
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
    return parser.parse_args()


def resolve_text(file_arg: str | None, text_arg: str | None, label: str) -> str:
    """Return text from a file or inline argument."""

    if file_arg:
        return Path(file_arg).read_text(encoding="utf-8")
    if text_arg is not None:
        return text_arg
    raise ValueError(f"either --{label}-file or --{label} is required")


def main() -> None:
    """Write report files and update state.json."""

    args = parse_args()
    workspace = resolve_workspace(args.workspace)
    paths = ensure_workspace_dirs(workspace)

    brief_text = resolve_text(args.brief_file, args.brief, "brief")
    full_report_text = resolve_text(args.full_report_file, args.full_report, "full-report")

    brief_file = paths.reports_dir / "brief.md"
    full_report_file = paths.reports_dir / "full-report.md"
    brief_file.write_text(brief_text, encoding="utf-8")
    full_report_file.write_text(full_report_text, encoding="utf-8")

    state = load_json(paths.state_file, default={})
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
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
