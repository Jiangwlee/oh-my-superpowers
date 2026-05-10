"""T1 static tests for `omp kickoff status` (skills/kickoff/scripts/status.py).

Covers:
  - parse_story_tasks: extracts (id, title) from story.md '## Task 计划' section
    and skips bullets that live inside HTML comments
  - parse_journal:
      * 'last entry wins' state query
      * batched reviewed entry advancing multiple tasks
      * template-comment block is ignored
      * Evidence completeness for in_progress task
      * ISSUE state machine (open ↔ fixed/dismissed via append-only updates)
  - resolve_story_dir: default = newest by name; explicit by name or by slug
  - render_report Phase 3 ready predicate
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "skills" / "kickoff" / "scripts" / "status.py"


def _load_status_module():
    spec = importlib.util.spec_from_file_location("kickoff_status", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    # Register before exec_module so dataclass decorator can resolve __module__
    sys.modules["kickoff_status"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


status = _load_status_module()


SAMPLE_STORY = """# Story: sample

## Goal
Verify status parser.

## Scope
### In
- foo

### Out
- bar

## Task 计划

<!--
格式（替换以下注释内的样板，并把真实 task 写到注释外）：
  - **T1 explore**：... — 验收：...
  - **T2 implement**：... — 验收：...
-->

- **T1 explore**：read code — 验收：journal 写四段
- **T2 implement**：write impl — 验收:本地 PASS
- **T3 wire-up**：integrate — 验收：E2E 通过

---
"""


JOURNAL_LAST_WINS = """# Journal

<!--
模板字段说明：
## T<n> [in_progress] HH:MM
-->

## T1 explore [in_progress] 14:00
assumption:  我以为 X
verify:      rg foo
fact:        实际是 Y
edit target: file.py:func()

## T1 explore [done] 14:30
decision: 决定走 Z
diff:     file.py (+10 -2)

## T1 [reviewed] 15:00
verdict:  PASS
reviewer: codex
batch:    T1
"""


JOURNAL_BATCHED_REVIEWED = """# Journal

## T2 impl [in_progress] 14:00
assumption:  X
verify:      rg
fact:        Y
edit target: a.py

## T2 impl [done] 14:30
decision: x
diff:     a.py (+5)

## T3 wire [in_progress] 14:35
assumption:  X
verify:      rg
fact:        Y
edit target: b.py

## T3 wire [done] 14:50
decision: y
diff:     b.py (+8)

## T2,T3 [reviewed] 15:00
verdict:  PASS
reviewer: sub-agent
batch:    T2 + T3
"""


JOURNAL_EVIDENCE_INCOMPLETE = """# Journal

## T2 impl [in_progress] 14:00
assumption:  X
verify:      rg
fact:
edit target: file.py
"""


JOURNAL_ISSUE_LIFECYCLE = """# Journal

## T1 explore [in_progress] 13:00
assumption:  X
verify:      rg
fact:        Y
edit target: a.py

## T1 explore [done] 14:00
decision: x
diff:     a.py (+1)

## ISSUE-001 open 14:50
source: T1 review
fact:   缺校验
plan:   T2 评估

## ISSUE-001 update fixed 16:00
by:     T2 commit abc1234

## ISSUE-002 open 16:30
source: 自查
fact:   日志噪音
plan:   非本 story scope

## ISSUE-002 update dismissed 16:35
by:     out of scope
"""


JOURNAL_NEEDS_FIX = """# Journal

## T1 explore [in_progress] 13:30
assumption:  X
verify:      rg
fact:        Y
edit target: a.py

## T1 explore [done] 14:00
decision: x
diff:     a.py (+5)

## T1 [needs_fix] 14:30
verdict:  NEEDS_FIX
reviewer: codex
batch:    T1
issues:   CRITICAL: missing timeout

## T1 explore [done] 15:00
decision: 加 timeout
diff:     a.py (+3)
"""


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


class ParseStoryTasksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "story.md"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_extracts_real_bullets_and_skips_comment_placeholder(self) -> None:
        _write(self.path, SAMPLE_STORY)
        result = status.parse_story_tasks(self.path)
        self.assertEqual(
            result,
            [("T1", "explore"), ("T2", "implement"), ("T3", "wire-up")],
        )

    def test_returns_empty_when_section_only_has_comment(self) -> None:
        text = """# Story: x

## Task 计划

<!--
- **T1 explore**：... — 验收：...
- **T2 impl**：... — 验收：...
-->

---
"""
        _write(self.path, text)
        self.assertEqual(status.parse_story_tasks(self.path), [])

    def test_returns_empty_when_section_missing(self) -> None:
        _write(self.path, "# Story: x\n\n## Goal\nfoo\n")
        self.assertEqual(status.parse_story_tasks(self.path), [])


class ParseJournalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "journal.md"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_last_entry_state_wins(self) -> None:
        _write(self.path, JOURNAL_LAST_WINS)
        tasks, issues, active = status.parse_journal(self.path)
        self.assertEqual(tasks["T1"].state, "reviewed")
        self.assertEqual(issues, {})
        self.assertIsNone(active)

    def test_batched_reviewed_entry_advances_all_listed_tasks(self) -> None:
        _write(self.path, JOURNAL_BATCHED_REVIEWED)
        tasks, _issues, _active = status.parse_journal(self.path)
        self.assertEqual(tasks["T2"].state, "reviewed")
        self.assertEqual(tasks["T3"].state, "reviewed")

    def test_evidence_incomplete_marks_missing_field_false(self) -> None:
        _write(self.path, JOURNAL_EVIDENCE_INCOMPLETE)
        tasks, _issues, active = status.parse_journal(self.path)
        self.assertIsNotNone(active)
        assert active is not None
        self.assertEqual(active.task_id, "T2")
        self.assertEqual(active.state, "in_progress")
        self.assertTrue(active.evidence["assumption"])
        self.assertTrue(active.evidence["verify"])
        self.assertFalse(active.evidence["fact"])  # value empty
        self.assertTrue(active.evidence["edit target"])

    def test_template_comment_block_is_ignored(self) -> None:
        text = """# Journal

<!--
## T999 fake [in_progress] 99:99
assumption:  should not be parsed
verify:      should not be parsed
fact:        should not be parsed
edit target: should not be parsed
-->

## T1 real [in_progress] 14:00
assumption:  real
verify:      real
fact:        real
edit target: real
"""
        _write(self.path, text)
        tasks, _issues, _active = status.parse_journal(self.path)
        self.assertNotIn("T999", tasks)
        self.assertEqual(tasks["T1"].state, "in_progress")

    def test_issue_open_then_update_state_machine(self) -> None:
        _write(self.path, JOURNAL_ISSUE_LIFECYCLE)
        _tasks, issues, _active = status.parse_journal(self.path)
        self.assertEqual(issues["ISSUE-001"].state, "fixed")
        self.assertEqual(issues["ISSUE-002"].state, "dismissed")

    def test_needs_fix_then_done_resets_active(self) -> None:
        _write(self.path, JOURNAL_NEEDS_FIX)
        tasks, _issues, active = status.parse_journal(self.path)
        self.assertEqual(tasks["T1"].state, "done")
        self.assertIsNone(active)

    def test_legal_full_chain_has_no_illegal_transitions(self) -> None:
        _write(self.path, JOURNAL_LAST_WINS)
        tasks, _issues, _active = status.parse_journal(self.path)
        self.assertEqual(tasks["T1"].illegal_transitions, [])

    def test_planned_to_done_is_illegal(self) -> None:
        text = """# Journal

## T1 explore [done] 14:00
decision: x
diff:     a.py (+1)
"""
        _write(self.path, text)
        tasks, _issues, _active = status.parse_journal(self.path)
        self.assertEqual(tasks["T1"].illegal_transitions, [("planned", "done")])

    def test_planned_to_reviewed_is_illegal(self) -> None:
        text = """# Journal

## T1 [reviewed] 15:00
verdict:  PASS
reviewer: x
batch:    T1
"""
        _write(self.path, text)
        tasks, _issues, _active = status.parse_journal(self.path)
        self.assertEqual(tasks["T1"].illegal_transitions, [("planned", "reviewed")])

    def test_in_progress_to_reviewed_is_illegal(self) -> None:
        text = """# Journal

## T1 explore [in_progress] 14:00
assumption:  X
verify:      rg
fact:        Y
edit target: a.py

## T1 [reviewed] 15:00
verdict:  PASS
reviewer: x
batch:    T1
"""
        _write(self.path, text)
        tasks, _issues, _active = status.parse_journal(self.path)
        self.assertEqual(
            tasks["T1"].illegal_transitions, [("in_progress", "reviewed")]
        )

    def test_needs_fix_to_reviewed_is_illegal(self) -> None:
        text = """# Journal

## T1 explore [in_progress] 13:00
assumption:  X
verify:      rg
fact:        Y
edit target: a.py

## T1 explore [done] 14:00
decision: x
diff:     a.py (+1)

## T1 [needs_fix] 14:30
verdict:  NEEDS_FIX
reviewer: x
batch:    T1

## T1 [reviewed] 15:00
verdict:  PASS
reviewer: x
batch:    T1
"""
        _write(self.path, text)
        tasks, _issues, _active = status.parse_journal(self.path)
        self.assertEqual(
            tasks["T1"].illegal_transitions, [("needs_fix", "reviewed")]
        )


class ResolveStoryDirTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "stories"
        self.root.mkdir()
        (self.root / "archives").mkdir()
        (self.root / "2026-04-01-old").mkdir()
        (self.root / "2026-05-10-new").mkdir()
        (self.root / "2026-05-09-mid").mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_default_picks_newest_by_name(self) -> None:
        result = status.resolve_story_dir(self.root, None)
        assert result is not None
        self.assertEqual(result.name, "2026-05-10-new")

    def test_explicit_full_name(self) -> None:
        result = status.resolve_story_dir(self.root, "2026-05-09-mid")
        assert result is not None
        self.assertEqual(result.name, "2026-05-09-mid")

    def test_explicit_slug_suffix(self) -> None:
        result = status.resolve_story_dir(self.root, "old")
        assert result is not None
        self.assertEqual(result.name, "2026-04-01-old")

    def test_unknown_returns_none(self) -> None:
        self.assertIsNone(status.resolve_story_dir(self.root, "nonexistent"))


class RenderPhase3ReadyTests(unittest.TestCase):
    def _render(
        self,
        planned: list[tuple[str, str]],
        parsed: dict[str, "status.TaskRecord"],
        issues: dict[str, "status.IssueRecord"],
        active: "status.TaskRecord | None" = None,
    ) -> str:
        return status.render_report(
            Path("/dummy/story"), planned, parsed, issues, active, []
        )

    def test_yes_when_all_tasks_terminal_and_no_issues(self) -> None:
        planned = [("T1", "x"), ("T2", "y")]
        parsed = {
            "T1": status.TaskRecord(task_id="T1", state="reviewed"),
            "T2": status.TaskRecord(task_id="T2", state="dropped"),
        }
        out = self._render(planned, parsed, {})
        self.assertIn("Phase 3 ready: YES", out)

    def test_no_when_task_still_in_progress(self) -> None:
        planned = [("T1", "x")]
        parsed = {"T1": status.TaskRecord(task_id="T1", state="in_progress")}
        out = self._render(planned, parsed, {})
        self.assertIn("Phase 3 ready: NO", out)
        self.assertIn("∉ {reviewed, dropped}", out)

    def test_no_when_planned_task_untouched(self) -> None:
        planned = [("T1", "x"), ("T2", "y")]
        parsed = {"T1": status.TaskRecord(task_id="T1", state="reviewed")}
        out = self._render(planned, parsed, {})
        self.assertIn("Phase 3 ready: NO", out)
        self.assertIn("untouched", out)

    def test_no_when_open_issue_present(self) -> None:
        planned = [("T1", "x")]
        parsed = {"T1": status.TaskRecord(task_id="T1", state="reviewed")}
        issues = {"ISSUE-001": status.IssueRecord(issue_id="ISSUE-001", state="open")}
        out = self._render(planned, parsed, issues)
        self.assertIn("Phase 3 ready: NO", out)
        self.assertIn("open issue", out)

    def test_no_when_empty_story(self) -> None:
        out = self._render([], {}, {})
        self.assertIn("Phase 3 ready: NO", out)
        self.assertIn("no tasks defined or recorded", out)

    def test_no_when_illegal_transition_present(self) -> None:
        planned = [("T1", "x")]
        rec = status.TaskRecord(
            task_id="T1",
            state="reviewed",
            illegal_transitions=[("planned", "reviewed")],
        )
        out = self._render(planned, {"T1": rec}, {})
        self.assertIn("Phase 3 ready: NO", out)
        self.assertIn("illegal transition", out)


if __name__ == "__main__":
    unittest.main()
