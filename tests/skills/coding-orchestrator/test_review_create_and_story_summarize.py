"""Review prompt rendering and story usage aggregation."""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
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


REVIEW_MOD = _load_module("orchestrator_review", "review.py")
TASK_MOD = _load_module("orchestrator_task_usage", "task.py")
STORY_MOD = _load_module("orchestrator_story", "story.py")


class TestReviewCreate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.story_dir = Path(self.tmpdir) / "stories" / "2026-04-19-fake"
        shutil.copytree(FIXTURE_STORY, self.story_dir)

        tasks_file = self.story_dir / "tasks.yaml"
        data = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))
        data["tasks"][0]["commits"] = ["abc1234", "def5678"]
        tasks_file.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_renders_prompt_with_commits_and_acceptance(self) -> None:
        out = Path(self.tmpdir) / "review.md"
        rc = REVIEW_MOD.cmd_create(
            argparse.Namespace(
                story_dir=str(Path(self.tmpdir) / "stories"),
                story="fake",
                task_id="01",
                template="default",
                additional="Focus on file scope drift.",
                out=str(out),
            )
        )
        self.assertEqual(rc, 0)
        text = out.read_text(encoding="utf-8")
        self.assertIn("abc1234", text)
        self.assertIn("git show def5678 --stat", text)
        self.assertIn("## Acceptance Criteria", text)
        self.assertIn("Focus on file scope drift.", text)


class TestStorySummarize(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        shutil.copytree(
            FIXTURE_STORY, Path(self.tmpdir) / "stories" / "2026-04-19-fake"
        )
        self.story_root = Path(self.tmpdir) / "stories"

        TASK_MOD.cmd_update(
            argparse.Namespace(
                story_dir=str(self.story_root),
                story="fake",
                id="01",
                status=None,
                worker=None,
                reviewer=None,
                commit=None,
                note=None,
                usage_kind="worker",
                model="gpt-5.2-codex",
                tokens=1200,
                tool_uses=4,
                duration_ms=9000,
            )
        )
        TASK_MOD.cmd_update(
            argparse.Namespace(
                story_dir=str(self.story_root),
                story="fake",
                id="01",
                status=None,
                worker=None,
                reviewer=None,
                commit=None,
                note=None,
                usage_kind="reviewer",
                model="gpt-5.4",
                tokens=800,
                tool_uses=1,
                duration_ms=3000,
            )
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_story_summarize_reports_by_kind_and_model(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = STORY_MOD.cmd_summarize(
                argparse.Namespace(story_dir=str(self.story_root), story="fake")
            )
        self.assertEqual(rc, 0)
        output = buf.getvalue()
        self.assertIn("## By Kind", output)
        self.assertIn("worker", output)
        self.assertIn("gpt-5.4", output)
        self.assertIn("1200", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
