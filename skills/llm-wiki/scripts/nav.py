"""Show status for the wiki, including raw sources pending synthesis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import list_markdown_files, raw_dir, resolve_wiki_home, wiki_dir


def find_pending_synthesis(wiki_home: Path) -> list[str]:
    """Return raw filenames (with .md) that no wiki/sources page covers yet.

    A raw file is considered covered when either:
    - wiki/sources/<same-name>.md exists, or
    - any wiki/sources/*.md body references it via a raw/ relative link.
    """

    raw_files = [p.name for p in list_markdown_files(raw_dir(wiki_home))]
    if not raw_files:
        return []

    sources_dir = wiki_dir(wiki_home) / "sources"
    if not sources_dir.exists():
        return sorted(raw_files)

    covered: set[str] = set()
    source_pages = list_markdown_files(sources_dir)
    source_bodies: list[str] = []
    for source_page in source_pages:
        if (raw_dir(wiki_home) / source_page.name).exists():
            covered.add(source_page.name)
        source_bodies.append(source_page.read_text(encoding="utf-8"))

    joined = "\n".join(source_bodies)
    for raw_name in raw_files:
        if raw_name in covered:
            continue
        needles = (
            f"raw/{raw_name}",
            f"../raw/{raw_name}",
            f"../../raw/{raw_name}",
        )
        if any(needle in joined for needle in needles):
            covered.add(raw_name)

    return sorted(set(raw_files) - covered)


def build_nav_payload(wiki_home: Path) -> dict[str, object]:
    """Build a compact nav payload."""

    compiled_root = wiki_dir(wiki_home)
    return {
        "wiki_home": str(wiki_home),
        "wiki_dir": str(compiled_root),
        "entrypoints": ["index.md", "log.md", "AGENTS.md"],
        "counts": {
            "raw": len(list_markdown_files(raw_dir(wiki_home))),
            "sources": len(list_markdown_files(compiled_root / "sources")),
            "concepts": len(list_markdown_files(compiled_root / "concepts")),
            "maps": len(list_markdown_files(compiled_root / "maps")),
        },
        "pending_synthesis": find_pending_synthesis(wiki_home),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Show wiki status.")
    parser.add_argument("--path", help="Wiki home directory (default: <git-root>/wiki or global).")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args(argv)

    payload = build_nav_payload(resolve_wiki_home(args.path))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"Wiki home: {payload['wiki_home']}")
    print(f"Wiki dir: {payload['wiki_dir']}")
    print("Entrypoints: index.md, log.md, AGENTS.md")
    counts = payload["counts"]
    print(
        "Counts: "
        f"raw={counts['raw']} "
        f"sources={counts['sources']} "
        f"concepts={counts['concepts']} "
        f"maps={counts['maps']}"
    )
    pending = payload["pending_synthesis"]
    if pending:
        print(f"Pending synthesis ({len(pending)}):")
        for name in pending:
            print(f"  - raw/{name}")
    else:
        print("Pending synthesis: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
