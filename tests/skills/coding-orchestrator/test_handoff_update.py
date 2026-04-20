"""Task-level handoff context updates."""
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
FIXTURE_STORY = Path(__file__).parent / "fixtures" / "feature-dispatch" / "stories" / "2026-04-19-fake"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HANDOFF_MOD = _load_module("orchestrator_handoff", "handoff.py")


class TestHandoffUpdate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        shutil.copytree(
            FIXTURE_STORY, Path(self.tmpdir) / "stories" / "2026-04-19-fake"
        )
        self.story_root = Path(self.tmpdir) / "stories"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _args(self, **overrides) -> argparse.Namespace:
        data = {
            "story_dir": str(self.story_root),
            "story": "fake",
            "task_id": "01",
            "phase": "executing",
            "next_action": "Dispatch worker on task-01.",
            "worker_agent_id": "worker-123",
            "reviewer_agent_id": None,
            "commit": None,
            "deviation": None,
        }
        data.update(overrides)
        return argparse.Namespace(**data)

    def test_update_writes_story_local_context(self) -> None:
        rc = HANDOFF_MOD.cmd_update(self._args())
        self.assertEqual(rc, 0)

        context_path = self.story_root / "2026-04-19-fake" / ".handoff-context"
        data = yaml.safe_load(context_path.read_text(encoding="utf-8"))
        self.assertEqual(data["story"], "2026-04-19-fake")
        self.assertEqual(data["current_wave"], 1)
        self.assertEqual(data["current_phase"], "executing")
        self.assertEqual(data["next_action"], "Dispatch worker on task-01.")
        self.assertEqual(data["wave_state"]["1"]["tasks"][0]["worker_agent_id"], "worker-123")

    def test_accepting_phase_records_deviation_and_commit(self) -> None:
        rc = HANDOFF_MOD.cmd_update(
            self._args(
                phase="accepting",
                reviewer_agent_id="reviewer-7",
                commit="abc1234",
                deviation="Allowed a narrow helper extraction.",
            )
        )
        self.assertEqual(rc, 0)

        context_path = self.story_root / "2026-04-19-fake" / ".handoff-context"
        data = yaml.safe_load(context_path.read_text(encoding="utf-8"))
        task = data["wave_state"]["1"]["tasks"][0]
        self.assertEqual(task["status"], "reviewed")
        self.assertEqual(task["reviewer_agent_id"], "reviewer-7")
        self.assertEqual(task["commit"], "abc1234")
        self.assertEqual(data["deviations_accepted"][0]["task_id"], "01")


if __name__ == "__main__":
    unittest.main(verbosity=2)
