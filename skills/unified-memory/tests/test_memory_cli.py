import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "skills" / "unified-memory" / "scripts" / "memory_cli.py"


class MemoryCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.tmpdir.name)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        cmd = [
            sys.executable,
            str(CLI),
            "--project-dir",
            str(self.project_dir),
            *args,
        ]
        return subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=check,
        )

    def test_add_and_search_json_output(self) -> None:
        add = self._run(
            "add",
            "--topic",
            "coding_preferences",
            "--content",
            "修改前先阅读 AGENTS.md 与相关 Skill 指南。",
            "--tags",
            "workflow,repo-rules",
            "--source",
            "explicit_user_memory",
            "--json",
        )
        added = json.loads(add.stdout)
        self.assertEqual(added["topic"], "coding_preferences")
        self.assertEqual(added["weight"], 8)

        search = self._run("search", "AGENTS", "--json")
        results = json.loads(search.stdout)
        self.assertEqual(len(results["items"]), 1)
        self.assertEqual(results["items"][0]["topic"], "coding_preferences")

    def test_autoload_topics_returns_only_topics_and_touches_weights(self) -> None:
        self._run(
            "add",
            "--topic",
            "deploy_rules",
            "--content",
            "部署前先做 dry-run。",
        )
        self._run(
            "add",
            "--topic",
            "coding_preferences",
            "--content",
            "先读 AGENTS.md。",
            "--weight",
            "20",
        )

        out = self._run("autoload-topics", "--limit", "1", "--json")
        payload = json.loads(out.stdout)
        self.assertEqual(payload["topics"], ["coding_preferences"])

        show = self._run("show", "coding_preferences", "--json")
        item = json.loads(show.stdout)["items"][0]
        self.assertGreaterEqual(item["retrieval_hits"], 1)
        self.assertGreaterEqual(item["weight"], 21)

    def test_prune_respects_max_items_and_keeps_high_weight(self) -> None:
        self._run("add", "--topic", "low_a", "--content", "a", "--weight", "1")
        self._run("add", "--topic", "high", "--content", "b", "--weight", "50")
        self._run("add", "--topic", "low_b", "--content", "c", "--weight", "2")

        self._run("prune", "--max-items", "2")

        topics = json.loads(self._run("topics", "--json").stdout)["topics"]
        self.assertIn("high", topics)
        self.assertEqual(len(topics), 2)

    def test_sensitive_content_is_rejected(self) -> None:
        result = self._run(
            "add",
            "--topic",
            "api_key",
            "--content",
            "sk-1234567890abcdef1234567890abcdef",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sensitive", result.stderr.lower())

    def test_rebuild_index_creates_index_file(self) -> None:
        self._run("add", "--topic", "t1", "--content", "alpha")
        self._run("rebuild-index")
        index_path = self.project_dir / ".memory" / "INDEX.md"
        self.assertTrue(index_path.exists())
        text = index_path.read_text(encoding="utf-8")
        self.assertIn("t1", text)

    def test_show_accepts_topic_flag_alias(self) -> None:
        self._run("add", "--topic", "user_name", "--content", "用户名字是 bruce")
        out = self._run("show", "--topic", "user_name", "--json")
        payload = json.loads(out.stdout)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["items"][0]["topic"], "user_name")


if __name__ == "__main__":
    unittest.main()
