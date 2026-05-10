#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""omp kickoff status — report the current state of a story.

Outputs:
  - Story path
  - Task list with current state (planned / in_progress / done / needs_fix /
    reviewed / dropped)
  - Evidence completeness for the active in_progress task
  - Open ISSUE list
  - Uncommitted git changes (best-effort)
  - Phase 3 ready judgment

Exit codes:
  0   success
  2   --story-dir or --story not resolvable
  3   story.md or journal.md missing
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Task entry: "## T2 implement [in_progress] 14:22"
# Batched reviewed entry: "## T2,T3 [reviewed] 16:10"
TASK_HEADER_RE = re.compile(
    r"^##\s+(?P<ids>T\d+(?:\s*,\s*T\d+)*)\s*(?P<title>[^\[]*?)\s*\[(?P<state>[a-z_]+)\]"
)
# ISSUE entry: "## ISSUE-001 open 14:50"
#           or "## ISSUE-001 update fixed 16:30"
ISSUE_HEADER_RE = re.compile(
    r"^##\s+ISSUE-(?P<num>\d+)\s+(?P<kind>open|update)(?:\s+(?P<state>[a-z_]+))?"
)
# Story.md task plan bullet: "- **T1 explore**: ..."  or "- **T1 explore** — ..."
PLAN_BULLET_RE = re.compile(r"^\s*-\s*\*\*\s*(T\d+)\s+([^*]+?)\*\*")

EVIDENCE_FIELDS = ("assumption", "verify", "fact", "edit target")
TERMINAL_STATES = {"reviewed", "dropped"}
VALID_TASK_STATES = {
    "planned", "in_progress", "done", "needs_fix", "reviewed", "dropped",
}
# Mirrors references/state-machine.md §Legal Transitions (the 7 allowed pairs).
# Any (from, to) outside this set is an illegal transition and blocks Phase 3.
LEGAL_TRANSITIONS: set[tuple[str, str]] = {
    ("planned", "in_progress"),
    ("planned", "dropped"),
    ("in_progress", "done"),
    ("in_progress", "dropped"),
    ("done", "reviewed"),
    ("done", "needs_fix"),
    ("needs_fix", "done"),
}


@dataclass
class TaskRecord:
    task_id: str
    state: str = "planned"
    title: str = ""
    evidence: dict[str, bool] = field(default_factory=dict)
    illegal_transitions: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class IssueRecord:
    issue_id: str
    state: str = "open"


def find_active_story(story_root: Path) -> Path | None:
    """Pick the most recent non-archive subdir, by name (YYYY-MM-DD-... sorts naturally)."""
    if not story_root.exists():
        return None
    candidates = [
        p for p in story_root.iterdir() if p.is_dir() and p.name != "archives"
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.name, reverse=True)
    return candidates[0]


def resolve_story_dir(story_root: Path, story_arg: str | None) -> Path | None:
    if story_arg is None:
        return find_active_story(story_root)
    target = story_root / story_arg
    if target.is_dir():
        return target
    matches = [
        p for p in story_root.iterdir()
        if p.is_dir() and p.name.endswith(f"-{story_arg}")
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def parse_story_tasks(story_md: Path) -> list[tuple[str, str]]:
    """Extract (task_id, title) pairs from the '## Task 计划' section.

    Skips lines inside HTML comments and the closing horizontal rule.
    """
    text = story_md.read_text(encoding="utf-8")
    tasks: list[tuple[str, str]] = []
    in_section = False
    in_comment = False
    for line in text.splitlines():
        stripped_line = line.strip()
        if "<!--" in line and "-->" not in line:
            in_comment = True
            continue
        if "-->" in line and "<!--" not in line:
            in_comment = False
            continue
        if "<!--" in line and "-->" in line:
            continue
        if in_comment:
            continue
        if line.startswith("## "):
            in_section = stripped_line == "## Task 计划"
            continue
        if not in_section:
            continue
        if stripped_line.startswith("---"):
            break
        m = PLAN_BULLET_RE.match(line)
        if m:
            tasks.append((m.group(1), m.group(2).strip()))
    return tasks


def _strip_comments(lines: list[str]) -> list[str]:
    out: list[str] = []
    in_comment = False
    for line in lines:
        if "<!--" in line and "-->" not in line:
            in_comment = True
            continue
        if "-->" in line and "<!--" not in line:
            in_comment = False
            continue
        if "<!--" in line and "-->" in line:
            continue
        if in_comment:
            continue
        out.append(line)
    return out


def _evidence_check(body: list[str]) -> dict[str, bool]:
    found = {f: False for f in EVIDENCE_FIELDS}
    for line in body:
        s = line.strip()
        for f in EVIDENCE_FIELDS:
            if s.startswith(f + ":"):
                value = s.split(":", 1)[1].strip()
                if value:
                    found[f] = True
    return found


def parse_journal(
    journal_md: Path,
) -> tuple[dict[str, TaskRecord], dict[str, IssueRecord], TaskRecord | None]:
    """Parse journal.md; return (tasks, issues, active_in_progress).

    "Current state" = last entry with the same id wins.
    Sections inside HTML comments (the template body) are ignored.
    """
    raw = journal_md.read_text(encoding="utf-8").splitlines()
    lines = _strip_comments(raw)

    pending: list[tuple[str, list[str]]] = []
    current_header: str | None = None
    current_body: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if current_header is not None:
                pending.append((current_header, current_body))
            current_header = line
            current_body = []
        elif current_header is not None:
            current_body.append(line)
    if current_header is not None:
        pending.append((current_header, current_body))

    tasks: dict[str, TaskRecord] = {}
    issues: dict[str, IssueRecord] = {}
    active: TaskRecord | None = None

    for header, body in pending:
        m = TASK_HEADER_RE.match(header)
        if m:
            ids = [s.strip() for s in m.group("ids").split(",")]
            state = m.group("state")
            title = m.group("title").strip()
            if state not in VALID_TASK_STATES:
                continue
            for tid in ids:
                rec = tasks.get(tid) or TaskRecord(task_id=tid)
                prev_state = rec.state
                if (prev_state, state) not in LEGAL_TRANSITIONS:
                    rec.illegal_transitions.append((prev_state, state))
                rec.state = state
                if title and len(ids) == 1:
                    rec.title = title
                if state == "in_progress":
                    rec.evidence = _evidence_check(body)
                    active = rec
                else:
                    rec.evidence = {}
                    if active is not None and active.task_id == tid:
                        active = None
                tasks[tid] = rec
            continue
        m2 = ISSUE_HEADER_RE.match(header)
        if m2:
            iid = f"ISSUE-{m2.group('num').zfill(3)}"
            kind = m2.group("kind")
            rec = issues.get(iid) or IssueRecord(issue_id=iid, state="open")
            if kind == "open":
                rec.state = "open"
            else:
                rec.state = m2.group("state") or rec.state
            issues[iid] = rec

    return tasks, issues, active


def git_uncommitted(repo: Path) -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo), "status", "--porcelain"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line.rstrip() for line in out.splitlines() if line.strip()]


def render_report(
    story_dir: Path,
    planned: list[tuple[str, str]],
    parsed: dict[str, TaskRecord],
    issues: dict[str, IssueRecord],
    active: TaskRecord | None,
    git_changes: list[str],
) -> str:
    out: list[str] = []
    out.append(f"Story: {story_dir}")

    out.append("Tasks:")
    title_by_id = {tid: title for tid, title in planned}
    seen: set[str] = set()
    ordered_ids: list[str] = []
    for tid, _ in planned:
        if tid not in seen:
            ordered_ids.append(tid)
            seen.add(tid)
    for tid in parsed:
        if tid not in seen:
            ordered_ids.append(tid)
            seen.add(tid)

    if not ordered_ids:
        out.append("  (none)")
    else:
        max_id_width = max(len(tid) for tid in ordered_ids)
        for tid in ordered_ids:
            rec = parsed.get(tid)
            state = rec.state if rec else "planned"
            title = title_by_id.get(tid) or (rec.title if rec else "")
            marker = "  ← reviewable" if state == "done" else ""
            title_part = f" {title}" if title else ""
            out.append(f"  {tid.ljust(max_id_width)}{title_part}  [{state}]{marker}")

    if active is not None:
        ev = active.evidence
        marks = " ".join(("✓" if ev.get(f) else "✗") + " " + f for f in EVIDENCE_FIELDS)
        out.append(f"    Evidence: {marks}")

    open_issues = sorted(iid for iid, rec in issues.items() if rec.state == "open")
    if open_issues:
        out.append(f"Open issues: {len(open_issues)} ({', '.join(open_issues)})")
    else:
        out.append("Open issues: 0")

    illegal: list[str] = []
    for tid, rec in parsed.items():
        for prev, curr in rec.illegal_transitions:
            illegal.append(f"{tid}: {prev} → {curr}")
    if illegal:
        out.append(f"Illegal transitions: {len(illegal)}")
        for entry in illegal[:5]:
            out.append(f"  {entry}")
        if len(illegal) > 5:
            out.append(f"  ... ({len(illegal) - 5} more)")

    if git_changes:
        out.append(f"Uncommitted: {len(git_changes)} files")
        for change in git_changes[:5]:
            out.append(f"  {change}")
        if len(git_changes) > 5:
            out.append(f"  ... ({len(git_changes) - 5} more)")
    else:
        out.append("Uncommitted: clean")

    planned_ids = {tid for tid, _ in planned}
    non_terminal = sorted(
        tid for tid, rec in parsed.items() if rec.state not in TERMINAL_STATES
    )
    untouched = sorted(planned_ids - set(parsed.keys()))
    blockers: list[str] = []
    if not planned_ids and not parsed:
        blockers.append("no tasks defined or recorded")
    if non_terminal:
        blockers.append(f"{len(non_terminal)} task ∉ {{reviewed, dropped}}")
    if untouched:
        blockers.append(f"{len(untouched)} planned task(s) untouched")
    if open_issues:
        blockers.append(f"{len(open_issues)} open issue(s)")
    if illegal:
        blockers.append(f"{len(illegal)} illegal transition(s)")
    if blockers:
        out.append(f"Phase 3 ready: NO — {'; '.join(blockers)}")
    else:
        out.append("Phase 3 ready: YES")

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="status",
        description="Report current state of a kickoff story.",
    )
    parser.add_argument("--story-dir", required=True)
    parser.add_argument("--story", default=None)
    args = parser.parse_args()

    story_root = Path(args.story_dir)
    story_dir = resolve_story_dir(story_root, args.story)
    if story_dir is None:
        sys.stderr.write(
            f"[status] no active story under {story_root}"
            + (f" matching '{args.story}'" if args.story else "")
            + "\n"
        )
        return 2

    story_md = story_dir / "story.md"
    journal_md = story_dir / "journal.md"
    if not story_md.exists() or not journal_md.exists():
        sys.stderr.write(
            f"[status] story.md or journal.md missing in {story_dir}\n"
        )
        return 3

    planned = parse_story_tasks(story_md)
    parsed_tasks, issues, active = parse_journal(journal_md)

    repo = story_root.parent
    try:
        out = subprocess.check_output(
            ["git", "-C", str(story_root), "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        repo = Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    git_changes = git_uncommitted(repo)

    print(render_report(story_dir, planned, parsed_tasks, issues, active, git_changes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
