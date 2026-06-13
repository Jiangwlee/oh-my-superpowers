#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


STYLE_KEYWORDS = {
    "dashboard",
    "enterprise",
    "productivity",
    "saas",
    "editorial",
    "minimal",
    "clean",
    "modern",
    "bold",
    "brutalism",
    "luxury",
    "futuristic",
    "friendly",
    "corporate",
    "creative",
    "dark",
    "light",
    "glass",
    "data",
    "mobile",
    "commerce",
    "developer",
    "ai",
}

SCENE_KEYWORDS = {
    "dashboard",
    "report",
    "brief",
    "review",
    "catalog",
    "landing",
    "marketing",
    "documentation",
    "settings",
    "workflow",
    "analytics",
    "editor",
    "console",
    "product",
    "portfolio",
    "commerce",
    "finance",
}


def _front_lines(text: str, limit: int = 60) -> str:
    return "\n".join(text.splitlines()[:limit])


def _extract_title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else fallback


def _extract_category(text: str) -> str:
    match = re.search(r"^>\s*Category:\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def _extract_description(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(">") or line.startswith("-"):
            continue
        return line[:240]
    return ""


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9-]{1,}", value.lower())


def _display_path(path: Path) -> str:
    home = Path.home().resolve()
    resolved = path.expanduser().resolve()
    try:
        return "~/" + resolved.relative_to(home).as_posix()
    except ValueError:
        return str(resolved)


def _tags(path: Path, text: str) -> list[str]:
    haystack = " ".join([path.parent.name, _front_lines(text)]).lower()
    found = {token for token in STYLE_KEYWORDS | SCENE_KEYWORDS if token in haystack}
    found.update(_tokens(path.parent.name))
    category = _extract_category(text)
    found.update(_tokens(category))
    return sorted(found)


def compile_index(source: Path, output: Path) -> int:
    source = source.expanduser().resolve()
    if not source.is_dir():
        print(f"html-design compile: source directory not found: {source}", file=sys.stderr)
        return 2

    entries = []
    for design_md in sorted(source.rglob("DESIGN.md")):
        text = design_md.read_text(encoding="utf-8", errors="replace")
        slug = design_md.parent.name
        tags = _tags(design_md, text)
        entries.append(
            {
                "path": _display_path(design_md),
                "slug": slug,
                "title": _extract_title(text, slug),
                "category": _extract_category(text),
                "description": _extract_description(text),
                "tags": tags,
                "keywords": sorted(set(tags + _tokens(_front_lines(text, 120))))[:80],
            }
        )

    payload = {
        "schema": "html-design.design-index.v1",
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "source": _display_path(source),
        "count": len(entries),
        "entries": entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "count": len(entries)}, ensure_ascii=False))
    return 0


def search_index(index: Path, query: list[str], limit: int) -> int:
    if not index.is_file():
        print(
            f"html-design search: index not found: {index}\n"
            "Run: omp html-design compile",
            file=sys.stderr,
        )
        return 2
    payload = json.loads(index.read_text(encoding="utf-8"))
    terms = _tokens(" ".join(query))
    scored = []
    for entry in payload.get("entries", []):
        bag = Counter(entry.get("keywords", []))
        bag.update(entry.get("tags", []))
        bag.update(_tokens(" ".join([entry.get("slug", ""), entry.get("title", ""), entry.get("category", "")])))
        score = sum(bag.get(term, 0) * 3 for term in terms)
        score += sum(1 for term in terms if term in entry.get("description", "").lower())
        if score:
            scored.append((score, entry))

    scored.sort(key=lambda item: (-item[0], item[1].get("slug", "")))
    results = [
        {
            "score": score,
            "path": entry["path"],
            "slug": entry["slug"],
            "title": entry["title"],
            "category": entry.get("category", ""),
            "tags": entry.get("tags", [])[:16],
        }
        for score, entry in scored[:limit]
    ]
    print(json.dumps({"query": " ".join(query), "count": len(results), "results": results}, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="design_index.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_compile = sub.add_parser("compile")
    p_compile.add_argument("--source", required=True, type=Path)
    p_compile.add_argument("--output", required=True, type=Path)

    p_search = sub.add_parser("search")
    p_search.add_argument("--index", required=True, type=Path)
    p_search.add_argument("--limit", required=True, type=int)
    p_search.add_argument("query", nargs="+")

    args = parser.parse_args()
    if args.command == "compile":
        return compile_index(args.source, args.output)
    if args.command == "search":
        return search_index(args.index, args.query, args.limit)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
