#!/usr/bin/env python3
"""Fetch GitHub Trending daily data via OpenClaw browser.

This script coordinates with LLM to extract trending repositories.
The LLM must use OpenClaw browser tool as instructed by this script.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any


def validate_trending_data(data: list[dict[str, Any]]) -> tuple[bool, str]:
    """Validate extracted trending data meets requirements.

    Returns:
        (is_valid, error_message)
    """
    if not data:
        return False, "No repositories extracted"

    if len(data) < 10:
        return (
            False,
            f"Only {len(data)} repositories found (minimum 10 required). "
            f"Likely incomplete extraction - ensure ALL repositories are captured.",
        )

    # Check for duplicates
    repos = [item.get("repo", "") for item in data]
    if len(repos) != len(set(repos)):
        duplicates = [r for r in repos if repos.count(r) > 1]
        return False, f"Duplicate repositories found: {set(duplicates)}"

    # Check each item has required fields
    for i, item in enumerate(data):
        if not item.get("repo"):
            return False, f"Item {i + 1} missing 'repo' field"
        if not item.get("what_it_does"):
            return (
                False,
                f"Item {i + 1} ({item.get('repo')}) missing 'what_it_does' field",
            )

    return True, ""


def generate_daily_brief(data: list[dict[str, Any]], date_str: str) -> str:
    """Generate markdown daily brief from trending data."""
    lines = [
        "---",
        "type: github_trending_brief",
        'format_version: "1.1.0"',
        f"date: {date_str}",
        "source: https://github.com/trending",
        "since: daily",
        f"item_count: {len(data)}",
        "---",
        "",
        f"# GitHub Trending Brief ({date_str})",
        "",
        f"## Complete Repository List",
        "",
        f"**ALL {len(data)} repositories from GitHub Trending Daily:**",
        "",
    ]

    for i, item in enumerate(data, 1):
        repo = item.get("repo", "unknown/unknown")
        what_it_does = item.get("what_it_does", "No description available")
        tech_stack = item.get("tech_stack", "")
        key_insight = item.get("key_insight", "")
        stars = item.get("stars", "")
        stars_today = item.get("stars_today", "")

        lines.extend(
            [
                f"### {i}. {repo}",
                f"**What it does**: {what_it_does}",
            ]
        )
        if tech_stack:
            lines.append(f"**Tech stack**: {tech_stack}")
        if key_insight:
            lines.append(f"**Key insight**: {key_insight}")
        if stars:
            stars_line = f"**Stars**: {stars}"
            if stars_today:
                stars_line += f" | **Today**: +{stars_today}"
            lines.append(stars_line)
        lines.append("")

    # Summary by language/category (simplified)
    lines.extend(
        [
            "## Summary",
            "",
            f"- **Total repositories**: {len(data)}",
            "- **Source**: https://github.com/trending (Daily)",
            f"- **Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
            "",
            "## Candidate Actions",
            "",
        ]
    )

    # Suggest actions based on what_it_does
    actions = []
    for item in data[:5]:  # Top 5 for actions
        repo = item.get("repo", "")
        what = item.get("what_it_does", "")[:60]
        if repo and what:
            actions.append(f"- **Add to watchlist**: {repo} — {what}...")

    lines.extend(actions)
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch GitHub Trending daily data. LLM must use browser as instructed.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
WORKFLOW FOR LLM:
1. Open browser to https://github.com/trending
2. Verify URL shows '/trending' (NOT '/trending/weekly' or '/trending/monthly')
3. Extract ALL repositories (typically 25-30 items)
4. For each repo, collect: repo name, what it does, tech stack, key insight, stars
5. Run this script with --data-json to generate the brief

Example:
  python3 fetch_trending.py --data-json '[{"repo":"owner/repo","what_it_does":"..."},...]'
        """,
    )
    parser.add_argument(
        "--memory-root", default=".memory", help="Root directory for memory files"
    )
    parser.add_argument(
        "--data-json", type=str, help="JSON array of extracted trending data"
    )
    parser.add_argument(
        "--date", type=str, help="Date string (YYYY-MM-DD), defaults to today"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (defaults to briefs/daily/YYYY-MM-DD.md)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate data, don't generate brief",
    )

    args = parser.parse_args()

    # If no data provided, print instructions for LLM
    if not args.data_json:
        print("""
╔════════════════════════════════════════════════════════════════╗
║  INSTRUCTIONS FOR LLM AGENT                                    ║
╠════════════════════════════════════════════════════════════════╣
║  STEP 1: Open OpenClaw browser                                 ║
║  STEP 2: Navigate to https://github.com/trending               ║
║  STEP 3: Verify URL is '/trending' (NOT weekly/monthly)        ║
║  STEP 4: Extract ALL repositories from the page                ║
║                                                                ║
║  For each repository, collect:                                 ║
║  - repo: "owner/repo-name"                                     ║
║  - what_it_does: "What problem this project solves"            ║
║  - tech_stack: "Primary language/frameworks"                   ║
║  - key_insight: "Why trending — functional significance"       ║
║  - stars: "Total star count"                                   ║
║  - stars_today: "Stars gained today"                           ║
║                                                                ║
║  STEP 5: Run this script with --data-json:                     ║
║  python3 fetch_trending.py --data-json '[{...}, {...}]'        ║
╚════════════════════════════════════════════════════════════════╝
""")
        sys.exit(0)

    # Parse and validate data
    try:
        data = json.loads(args.data_json)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON data: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print("ERROR: Data must be a JSON array", file=sys.stderr)
        sys.exit(1)

    # Validate
    is_valid, error_msg = validate_trending_data(data)
    if not is_valid:
        print(f"ERROR: Validation failed - {error_msg}", file=sys.stderr)
        print(f"\nExtracted {len(data)} repositories:", file=sys.stderr)
        for item in data:
            print(f"  - {item.get('repo', 'unknown')}", file=sys.stderr)
        sys.exit(1)

    if args.validate_only:
        print(json.dumps({"status": "ok", "count": len(data)}, ensure_ascii=False))
        sys.exit(0)

    # Generate brief
    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    brief_content = generate_daily_brief(data, date_str)

    # Determine output path
    if args.output:
        output_path = pathlib.Path(args.output)
    else:
        output_path = (
            pathlib.Path(args.memory_root)
            / "github-tracker"
            / "briefs"
            / "daily"
            / f"{date_str}.md"
        )

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    output_path.write_text(brief_content, encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "count": len(data),
                "output_path": str(output_path),
                "date": date_str,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
