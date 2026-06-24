from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "code-graph" / "scripts" / "code_graph.py"


def run_cli(home: Path, *args: str, extra_env: dict[str, str] | None = None) -> dict:
    env = os.environ.copy()
    env["OMP_CODE_GRAPH_HOME"] = str(home)
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    return json.loads(proc.stdout)


class CodeGraphTests(unittest.TestCase):
    def test_index_search_trace_snippet_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            repo = tmp_path / "repo"
            repo.mkdir()
            (repo / "app.py").write_text(
                "\n".join(
                    [
                        "def helper():",
                        "    return 1",
                        "",
                        "def main():",
                        "    return helper()",
                        "",
                        "class Service:",
                        "    def run(self):",
                        "        return helper()",
                    ]
                ),
                encoding="utf-8",
            )
            (repo / "web.ts").write_text(
                "\n".join(
                    [
                        "export function sendMail(user: string) {",
                        "  formatUser(user)",
                        "}",
                        "function formatUser(user: string) {",
                        "  return user",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )
            (repo / "task.sh").write_text(
                "\n".join(["build() {", "  clean", "}", "clean() {", "  echo ok", "}"]),
                encoding="utf-8",
            )

            stats = run_cli(tmp_path / "cache", "index", str(repo), "--project", "sample")
            self.assertEqual(stats["status"], "indexed")
            self.assertEqual(stats["files"], 3)
            self.assertGreaterEqual(stats["nodes"], 9)
            self.assertGreaterEqual(stats["edges"], 3)

            search = run_cli(tmp_path / "cache", "search", "helper", "--project", "sample", "--json")
            self.assertTrue(any(row["name"] == "helper" for row in search["results"]))

            callers = run_cli(tmp_path / "cache", "callers", "helper", "--project", "sample", "--json")
            caller_names = {row["name"] for row in callers["results"]}
            self.assertLessEqual({"main", "run"}, caller_names)

            callees = run_cli(tmp_path / "cache", "callees", "sendMail", "--project", "sample", "--json")
            self.assertTrue(any(row["name"] == "formatUser" for row in callees["results"]))

            qname = next(row["qname"] for row in search["results"] if row["name"] == "helper")
            snippet = run_cli(tmp_path / "cache", "snippet", qname, "--project", "sample", "--json")
            self.assertIn("def helper", snippet["code"])

            status = run_cli(tmp_path / "cache", "status", "--project", "sample", "--json")
            self.assertFalse(status["stale"])
            (repo / "app.py").write_text(
                (repo / "app.py").read_text(encoding="utf-8") + "\n# changed\n",
                encoding="utf-8",
            )
            status = run_cli(tmp_path / "cache", "status", "--project", "sample", "--json")
            self.assertTrue(status["stale"])

    def test_multi_project_indexes_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            os.environ["OMP_CODE_GRAPH_HOME"] = str(tmp_path / "cache")
            spec = importlib.util.spec_from_file_location("code_graph_under_test", SCRIPT)
            self.assertIsNotNone(spec)
            assert spec and spec.loader
            cg = importlib.util.module_from_spec(spec)
            sys.modules["code_graph_under_test"] = cg
            spec.loader.exec_module(cg)

            repo_a = tmp_path / "a"
            repo_b = tmp_path / "b"
            repo_a.mkdir()
            repo_b.mkdir()
            (repo_a / "a.py").write_text("def shared():\n    pass\n", encoding="utf-8")
            (repo_b / "b.py").write_text("def shared():\n    pass\n", encoding="utf-8")

            with cg.db() as conn:
                cg.rebuild_project(conn, "a", repo_a)
                cg.rebuild_project(conn, "b", repo_b)
                projects = [r["name"] for r in conn.execute("SELECT name FROM projects ORDER BY name")]
                self.assertEqual(projects, ["a", "b"])
                a_count = conn.execute("SELECT COUNT(*) FROM nodes WHERE project = 'a'").fetchone()[0]
                b_count = conn.execute("SELECT COUNT(*) FROM nodes WHERE project = 'b'").fetchone()[0]
            self.assertEqual(a_count, 2)
            self.assertEqual(b_count, 2)

    def test_default_and_extra_skip_dirs_avoid_duplicate_local_worktrees(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            repo = tmp_path / "repo"
            repo.mkdir()
            (repo / "src").mkdir()
            (repo / "src" / "main.ts").write_text(
                "export function liveFeature() { return 1 }\n",
                encoding="utf-8",
            )
            for directory in [
                repo / ".agents" / "skills",
                repo / ".claude" / "worktrees" / "copy" / "src",
                repo / ".codex" / "sessions",
                repo / "github" / "reference" / "src",
                repo / ".memory" / "snapshots",
                repo / ".next" / "server",
                repo / ".pi" / "runs",
                repo / "scratch",
            ]:
                directory.mkdir(parents=True)
                (directory / "main.ts").write_text(
                    "export function duplicateFeature() { return 1 }\n",
                    encoding="utf-8",
                )

            stats = run_cli(
                tmp_path / "cache",
                "index",
                str(repo),
                "--project",
                "skip-sample",
                extra_env={"OMP_CODE_GRAPH_EXTRA_SKIP_DIRS": "scratch"},
            )
            self.assertEqual(stats["files"], 1)

            live = run_cli(
                tmp_path / "cache",
                "search",
                "liveFeature",
                "--project",
                "skip-sample",
                "--json",
            )
            self.assertEqual(live["count"], 1)
            self.assertEqual(live["results"][0]["file"], "src/main.ts")

            duplicate = run_cli(
                tmp_path / "cache",
                "search",
                "duplicateFeature",
                "--project",
                "skip-sample",
                "--json",
            )
            self.assertEqual(duplicate["count"], 0)


if __name__ == "__main__":
    unittest.main()
