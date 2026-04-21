"""Initialize the global Karpathy-style wiki layout."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import dump_json, now_iso, raw_dir, resolve_wiki_home, wiki_dir, write_text_atomic


AGENTS_MD = """# LLM Wiki Schema

Karpathy-style markdown knowledge base managed by the `llm-wiki` skill.

## Layout

- `raw/` — ingested source material, one file per source (created by `omp wiki ingest`).
- `wiki/sources/` — one page per raw source with a caller-written summary.
- `wiki/concepts/` — cross-source concept pages.
- `wiki/maps/` — high-level index / map pages.
- `wiki/outputs/` — caller-produced outputs derived from the wiki.
- `wiki/index.md` — top-level navigation entrypoint.
- `wiki/log.md` — append-only log of significant events.

## Division of labor

- **CLI (`omp wiki …`)**: ingest, navigation status (`nav`), lint.
- **Skill SOP**: decides *when* and *how* to synthesize pages.
- **Caller agent**: writes the actual markdown in `wiki/` using its own Read/Write tools.
"""


INDEX_MD = """# Knowledge Base Index
"""


LOG_MD = """# Wiki Log
"""


def ensure_wiki_home(wiki_home: Path) -> None:
    """Create the global wiki directory contract."""

    raw_dir(wiki_home).mkdir(parents=True, exist_ok=True)
    wiki_root = wiki_dir(wiki_home)
    for path in (
        wiki_root,
        wiki_root / "sources",
        wiki_root / "concepts",
        wiki_root / "maps",
        wiki_root / "outputs",
    ):
        path.mkdir(parents=True, exist_ok=True)

    agents_md = wiki_root / "AGENTS.md"
    if not agents_md.exists():
        write_text_atomic(agents_md, AGENTS_MD)

    index_md = wiki_root / "index.md"
    if not index_md.exists():
        write_text_atomic(index_md, INDEX_MD)

    log_md = wiki_root / "log.md"
    if not log_md.exists():
        write_text_atomic(log_md, LOG_MD)

    state_file = wiki_home / "state.json"
    if not state_file.exists():
        dump_json(
            state_file,
            {
                "version": 1,
                "created_at": now_iso(),
            },
        )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Initialize the global wiki home.")
    parser.add_argument("--path", help="Wiki home directory (default: <git-root>/wiki or global).")
    args = parser.parse_args(argv)

    wiki_home = resolve_wiki_home(args.path)
    ensure_wiki_home(wiki_home)
    print(f"Initialized wiki home at {wiki_home}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
