"""Intake contract: a story skeleton produced by brainstorming S3 must be
directly consumable by coding-orchestrator.

Validates:
- Required four-artifact chain exists (story.md / tasks.yaml / task-01.md / story-memory.md)
- story.md has the mandatory ``> Design:`` backlink on its first non-title line
- tasks.yaml schema: every task has id / title / status / wave / depends_on
- wave-1 tasks have non-null spec + the spec file exists
- wave≥2 tasks have spec=null (JIT slot)
- story-memory.md contains the three required section headers
- task.py JIT gate: wave-1 task dispatches cleanly; wave-2 task is rejected
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SKILL_DIR = Path(__file__).resolve().parents[3] / "skills" / "coding-orchestrator"
SCRIPTS_DIR = SKILL_DIR / "scripts"
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "feature-dispatch"
FIXTURE_STORY = FIXTURE_ROOT / "stories" / "2026-04-19-fake"


def _load_task_module():
    spec = importlib.util.spec_from_file_location(
        "orchestrator_task_intake", SCRIPTS_DIR / "task.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orchestrator_task_intake"] = mod
    spec.loader.exec_module(mod)
    return mod


TASK_MOD = _load_task_module()


class TestFixtureShape(unittest.TestCase):
    """The skeleton brainstorming writes must match the contract."""

    def test_four_artifacts_present(self) -> None:
        for name in ("story.md", "tasks.yaml", "story-memory.md"):
            self.assertTrue(
                (FIXTURE_STORY / name).is_file(), f"missing required artifact: {name}"
            )
        self.assertTrue(
            (FIXTURE_STORY / "tasks" / "task-01.md").is_file(),
            "missing wave-1 task spec tasks/task-01.md",
        )

    def test_story_md_has_design_backlink(self) -> None:
        text = (FIXTURE_STORY / "story.md").read_text(encoding="utf-8")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        self.assertTrue(lines[0].startswith("# "), "story.md must start with a title")
        backlink = lines[1]
        self.assertTrue(
            backlink.startswith("> Design:"),
            f"first non-title line must be '> Design: ...', got: {backlink!r}",
        )
        self.assertIn(
            "/docs/brainstorming/specs/",
            backlink,
            "Design backlink must point to docs/brainstorming/specs/",
        )

    def test_story_memory_has_required_sections(self) -> None:
        text = (FIXTURE_STORY / "story-memory.md").read_text(encoding="utf-8")
        for header in ("## Patterns", "## Gotchas", "## Known False Positives"):
            self.assertIn(header, text, f"story-memory.md missing section: {header}")


class TestTasksYamlSchema(unittest.TestCase):
    """tasks.yaml must be a consumable skeleton, not a finished plan."""

    def setUp(self) -> None:
        self.data = yaml.safe_load(
            (FIXTURE_STORY / "tasks.yaml").read_text(encoding="utf-8")
        )

    def test_required_top_level_fields(self) -> None:
        for key in ("story", "created", "tasks"):
            self.assertIn(key, self.data, f"tasks.yaml missing top-level key: {key}")
        self.assertIsInstance(self.data["tasks"], list)
        self.assertGreater(len(self.data["tasks"]), 0)

    def test_each_task_has_required_fields(self) -> None:
        required = {"id", "title", "status", "wave", "depends_on"}
        for task in self.data["tasks"]:
            missing = required - task.keys()
            self.assertFalse(missing, f"task {task.get('id')} missing {missing}")

    def test_wave1_tasks_have_spec_and_file_exists(self) -> None:
        for task in self.data["tasks"]:
            if task["wave"] != 1:
                continue
            self.assertTrue(
                task.get("spec"),
                f"wave-1 task {task['id']} must have non-null spec",
            )
            spec_path = FIXTURE_STORY / task["spec"]
            self.assertTrue(
                spec_path.is_file(), f"wave-1 spec file missing: {spec_path}"
            )

    def test_wave_ge2_tasks_have_null_spec(self) -> None:
        for task in self.data["tasks"]:
            if task["wave"] < 2:
                continue
            self.assertIsNone(
                task.get("spec"),
                f"wave-{task['wave']} task {task['id']} must have spec=null "
                f"(JIT slot for orchestrator), got: {task.get('spec')!r}",
            )


class TestWave1DispatchableAsIs(unittest.TestCase):
    """Orchestrator must be able to transition wave-1 tasks without manual fix."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        shutil.copytree(
            FIXTURE_STORY, Path(self.tmpdir) / "stories" / "2026-04-19-fake"
        )
        self.story_root = Path(self.tmpdir) / "stories"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_args(self, task_id: str, status: str) -> argparse.Namespace:
        return argparse.Namespace(
            story_dir=str(self.story_root),
            story="fake",
            id=task_id,
            status=status,
            worker=None,
            reviewer=None,
            commit=None,
            note=None,
        )

    def test_wave1_dispatch_succeeds(self) -> None:
        rc = TASK_MOD.cmd_update(self._make_args("01", "executing"))
        self.assertEqual(rc, 0, "wave-1 task with complete spec must dispatch cleanly")

    def test_wave2_dispatch_rejected_until_jit_write(self) -> None:
        rc = TASK_MOD.cmd_update(self._make_args("02", "executing"))
        self.assertEqual(
            rc, 2,
            "wave-2 task with spec=null must be rejected by JIT gate",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
