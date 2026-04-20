"""JIT gate on task.py::cmd_update.

Contract: a task cannot transition to ``executing`` unless its ``spec`` field
points to a real spec file. ``null``, missing key, and empty-string all count
as "not yet written" and must be rejected with exit code 2.

Rationale: wave-by-wave JIT task decomposition writes wave≥2 specs only after
prior waves' feedback. Dispatching a task whose spec hasn't been written means
the worker runs without instructions — the gate prevents that entire class of
bug at the state-transition boundary.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import unittest
from pathlib import Path

import yaml

SKILL_DIR = Path(__file__).resolve().parents[3] / "skills" / "coding-orchestrator"
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load_task_module():
    spec = importlib.util.spec_from_file_location(
        "orchestrator_task", SCRIPTS_DIR / "task.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orchestrator_task"] = mod
    spec.loader.exec_module(mod)
    return mod


TASK_MOD = _load_task_module()


def _write_story(tmp_path: Path, spec_field) -> Path:
    """Write a minimal story with one task whose spec = ``spec_field``.

    ``spec_field`` may be the literal string "__MISSING__" to signal the key
    should be absent from the dict entirely.
    """
    story_dir = tmp_path / "stories" / "2026-04-19-fake"
    story_dir.mkdir(parents=True)

    task_entry: dict = {
        "id": "01",
        "title": "fake task",
        "status": "pending",
        "wave": 1,
        "depends_on": [],
    }
    if spec_field != "__MISSING__":
        task_entry["spec"] = spec_field

    tasks_file = story_dir / "tasks.yaml"
    tasks_file.write_text(
        yaml.safe_dump(
            {"story": "fake", "created": "2026-04-19", "tasks": [task_entry]},
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return tmp_path / "stories"


def _make_args(story_root: Path, status: str) -> argparse.Namespace:
    return argparse.Namespace(
        story_dir=str(story_root),
        story="fake",
        id="01",
        status=status,
        worker=None,
        reviewer=None,
        commit=None,
        note=None,
    )


class TestJitGateRejects(unittest.TestCase):
    """status=executing must fail when spec is effectively empty."""

    def _run_reject_case(self, spec_field) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            story_root = _write_story(Path(td), spec_field)
            args = _make_args(story_root, "executing")
            rc = TASK_MOD.cmd_update(args)
            self.assertEqual(
                rc, 2, f"expected exit 2 for spec={spec_field!r}, got {rc}"
            )

            tasks_file = story_root / "2026-04-19-fake" / "tasks.yaml"
            data = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))
            self.assertEqual(
                data["tasks"][0]["status"],
                "pending",
                f"status should stay pending when rejected (spec={spec_field!r})",
            )

    def test_reject_null_spec(self) -> None:
        self._run_reject_case(None)

    def test_reject_missing_spec_key(self) -> None:
        self._run_reject_case("__MISSING__")

    def test_reject_empty_string_spec(self) -> None:
        self._run_reject_case("")


class TestJitGateAllows(unittest.TestCase):
    """status=executing must succeed when spec points to a file path."""

    def test_allow_non_empty_spec(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            story_root = _write_story(Path(td), "tasks/task-01.md")
            args = _make_args(story_root, "executing")
            rc = TASK_MOD.cmd_update(args)
            self.assertEqual(rc, 0, f"expected exit 0, got {rc}")

            tasks_file = story_root / "2026-04-19-fake" / "tasks.yaml"
            data = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))
            self.assertEqual(data["tasks"][0]["status"], "executing")


class TestJitGateDoesNotBlockOtherTransitions(unittest.TestCase):
    """The gate only triggers on pending→executing. Other transitions untouched."""

    def test_allow_pending_to_blocked_with_null_spec(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            story_root = _write_story(Path(td), None)
            args = _make_args(story_root, "blocked")
            rc = TASK_MOD.cmd_update(args)
            self.assertEqual(rc, 0, "status=blocked should not be gated by spec")


if __name__ == "__main__":
    unittest.main(verbosity=2)
