"""Merge structured state updates into a deep-research workspace.

Usage:
    omp-deep-research update-state --workspace "<workspace>" --payload-file "<json_file>"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import append_jsonl, dump_json, ensure_workspace_dirs, load_json, resolve_workspace


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Update deep-research state from a JSON payload.")
    parser.add_argument("--workspace", required=True, help="Workspace directory.")
    parser.add_argument("--payload-file", required=True, help="JSON payload file.")
    return parser.parse_args()


def upsert_source_note(state: dict[str, Any], note: dict[str, Any]) -> None:
    """Insert or replace a source note by source_id."""

    source_id = note["source_id"]
    notes = state.setdefault("source_notes", [])
    for idx, existing in enumerate(notes):
        if existing.get("source_id") == source_id:
            notes[idx] = note
            break
    else:
        notes.append(note)


def main() -> None:
    """Update state.json and rounds.jsonl from a payload."""

    args = parse_args()
    workspace = resolve_workspace(args.workspace)
    paths = ensure_workspace_dirs(workspace)
    state = load_json(paths.state_file, default={})
    payload = json.loads(Path(args.payload_file).read_text(encoding="utf-8"))

    round_log = payload.get("round_log")
    if round_log:
        append_jsonl(paths.rounds_file, round_log)

    source_note = payload.get("source_note")
    if source_note:
        upsert_source_note(state, source_note)
        note_file = paths.notes_dir / f"{source_note['source_id']}.md"
        note_file.write_text(source_note.get("markdown", ""), encoding="utf-8")

    if "subquestions" in payload:
        state["subquestions"] = payload["subquestions"]

    hypothesis = payload.get("hypothesis")
    if hypothesis:
        state.setdefault("hypotheses", []).append(hypothesis)

    next_step = payload.get("next_step")
    if next_step:
        state.setdefault("next_steps", []).append(next_step)

    status = payload.get("status")
    if status:
        state["status"] = status

    dump_json(paths.state_file, state)
    print(json.dumps({"status": "ok", "state_file": str(paths.state_file)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
