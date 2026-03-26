"""Save one fetched source into a deep-research workspace.

Usage:
    omp-deep-research save-source --workspace "<workspace>" --url "<url>" --title "<title>" --platform "<platform>" --content-file "<file>"
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from common import dump_json, ensure_workspace_dirs, load_json, next_source_id, resolve_workspace


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Save one source into a deep-research workspace.")
    parser.add_argument("--workspace", required=True, help="Workspace directory.")
    parser.add_argument("--url", required=True, help="Source URL.")
    parser.add_argument("--title", required=True, help="Source title.")
    parser.add_argument("--platform", required=True, help="Source platform label.")
    parser.add_argument("--content-file", help="Path to a file containing raw content.")
    parser.add_argument("--content", help="Inline raw content.")
    return parser.parse_args()


def load_content(args: argparse.Namespace) -> str:
    """Return the raw source content from file or inline text."""

    if args.content_file:
        return Path(args.content_file).read_text(encoding="utf-8")
    if args.content is not None:
        return args.content
    raise ValueError("either --content-file or --content is required")


def main() -> None:
    """Save raw content and update source index."""

    args = parse_args()
    workspace = resolve_workspace(args.workspace)
    paths = ensure_workspace_dirs(workspace)
    state = load_json(paths.state_file, default={})

    existing_urls = {s["url"] for s in state.get("source_index", [])}
    if args.url in existing_urls:
        print(json.dumps({"status": "duplicate", "url": args.url}, ensure_ascii=False))
        return

    source_id = next_source_id(state)
    content = load_content(args)

    raw_file = paths.raw_dir / f"{source_id}.txt"
    meta_file = paths.raw_dir / f"{source_id}.meta.json"
    note_file = paths.notes_dir / f"{source_id}.md"

    raw_file.write_text(content, encoding="utf-8")
    meta = {
        "source_id": source_id,
        "title": args.title,
        "url": args.url,
        "platform": args.platform,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    dump_json(meta_file, meta)
    if not note_file.exists():
        note_file.write_text("", encoding="utf-8")

    index_entry = {
        "source_id": source_id,
        "title": args.title,
        "url": args.url,
        "platform": args.platform,
        "raw_file": str(raw_file),
        "meta_file": str(meta_file),
        "note_file": str(note_file),
    }
    state.setdefault("source_index", []).append(index_entry)
    dump_json(paths.state_file, state)

    print(
        json.dumps(
            {
                "status": "ok",
                "source_id": source_id,
                "raw_file": str(raw_file),
                "meta_file": str(meta_file),
                "note_file": str(note_file),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
