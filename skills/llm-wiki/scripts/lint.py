"""Report-only linting for compiled wiki pages."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import list_markdown_files, resolve_wiki_home, wiki_dir


WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def known_pages(compiled_root: Path) -> set[str]:
    """Return the normalized wiki page keys that exist."""

    pages = {"index", "log", "AGENTS"}
    for section in ("sources", "concepts", "maps", "outputs"):
        for path in list_markdown_files(compiled_root / section):
            pages.add(f"{section}/{path.stem}")
    return pages


def collect_issues(compiled_root: Path) -> list[dict[str, str]]:
    """Collect structural issues from compiled wiki pages."""

    issues: list[dict[str, str]] = []
    index_text = (compiled_root / "index.md").read_text(encoding="utf-8")
    if "# Knowledge Base Index" not in index_text:
        issues.append(
            {
                "kind": "missing_heading",
                "path": "index.md",
                "message": "index.md is missing the Knowledge Base Index heading",
            }
        )

    available = known_pages(compiled_root)
    pages_to_check = [
        compiled_root / "index.md",
        compiled_root / "log.md",
        *list_markdown_files(compiled_root / "sources"),
        *list_markdown_files(compiled_root / "concepts"),
        *list_markdown_files(compiled_root / "maps"),
    ]

    for page in pages_to_check:
        if not page.exists():
            continue
        content = page.read_text(encoding="utf-8")
        for target in WIKILINK_RE.findall(content):
            raw_target = target.strip()
            if raw_target.startswith("../raw/"):
                continue
            normalized = raw_target.lstrip("./").removesuffix(".md")
            if normalized not in available:
                issues.append(
                    {
                        "kind": "broken_wikilink",
                        "path": str(page.relative_to(compiled_root)),
                        "message": f"missing target: {target}",
                    }
                )
    return issues


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Lint compiled wiki pages.")
    parser.add_argument("--wiki-home", help="Override global wiki home.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args(argv)

    compiled_root = wiki_dir(resolve_wiki_home(args.wiki_home))
    issues = collect_issues(compiled_root)
    payload = {"issues": issues}

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if not issues:
        print("No issues found.")
        return 0

    for issue in issues:
        print(f"[{issue['kind']}] {issue['path']}: {issue['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
