"""T1 tests for `omp wiki nav` and `lint` behavior."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
OMP_BIN = REPO_ROOT / "bin" / "omp"


def run_omp(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run the local `omp` binary against the current repo as OMP_HOME."""

    merged = os.environ.copy()
    merged["OMP_HOME"] = str(REPO_ROOT)
    if env:
        merged.update(env)
    return subprocess.run(
        [str(OMP_BIN), *args],
        text=True,
        capture_output=True,
        env=merged,
        check=False,
    )


def ingest_text(wiki_home: Path, title: str, body: str) -> None:
    """Ingest a text source via the CLI."""

    result = subprocess.run(
        [str(OMP_BIN), "wiki", "ingest", "--text", "--title", title],
        input=f"# {title}\n\n{body}\n",
        text=True,
        capture_output=True,
        env={**os.environ, "OMP_HOME": str(REPO_ROOT), "WIKI_HOME": str(wiki_home)},
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"ingest failed: {result.stderr}")


class TestWikiNavAndLint(unittest.TestCase):
    """Validate read-only wiki status commands."""

    def test_nav_reports_status_as_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_home = Path(tmpdir) / "wiki-home"
            init_result = run_omp("wiki", "init", env={"WIKI_HOME": str(wiki_home)})
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            result = run_omp("wiki", "nav", "--json", env={"WIKI_HOME": str(wiki_home)})
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)

            self.assertEqual(payload["entrypoints"], ["index.md", "log.md", "AGENTS.md"])
            self.assertEqual(payload["counts"]["raw"], 0)
            self.assertEqual(payload["counts"]["sources"], 0)
            self.assertEqual(payload["counts"]["concepts"], 0)
            self.assertEqual(payload["counts"]["maps"], 0)
            self.assertEqual(payload["pending_synthesis"], [])

    def test_lint_reports_empty_issues_for_fresh_wiki(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_home = Path(tmpdir) / "wiki-home"
            init_result = run_omp("wiki", "init", env={"WIKI_HOME": str(wiki_home)})
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            result = run_omp("wiki", "lint", "--json", env={"WIKI_HOME": str(wiki_home)})
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["issues"], [])

    def test_nav_pending_synthesis_lists_uncovered_raw(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_home = Path(tmpdir) / "wiki-home"
            init_result = run_omp("wiki", "init", env={"WIKI_HOME": str(wiki_home)})
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            ingest_text(wiki_home, "Alpha Note", "Alpha covers CLI runtime.")
            ingest_text(wiki_home, "Beta Note", "Beta covers workflow.")

            result = run_omp("wiki", "nav", "--json", env={"WIKI_HOME": str(wiki_home)})
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)

            self.assertEqual(payload["counts"]["raw"], 2)
            self.assertEqual(payload["counts"]["sources"], 0)
            self.assertEqual(
                payload["pending_synthesis"],
                ["alpha-note.md", "beta-note.md"],
            )

    def test_nav_pending_synthesis_respects_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_home = Path(tmpdir) / "wiki-home"
            init_result = run_omp("wiki", "init", env={"WIKI_HOME": str(wiki_home)})
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            ingest_text(wiki_home, "Alpha Note", "Alpha covers CLI runtime.")
            ingest_text(wiki_home, "Beta Note", "Beta covers workflow.")

            sources_dir = wiki_home / "wiki" / "sources"
            sources_dir.mkdir(parents=True, exist_ok=True)
            (sources_dir / "alpha-note.md").write_text(
                "# Alpha Note\n\nSummary of alpha.\n",
                encoding="utf-8",
            )
            (sources_dir / "mentions-beta.md").write_text(
                "# Mentions Beta\n\nSee [[../raw/beta-note.md]] for detail.\n",
                encoding="utf-8",
            )

            result = run_omp("wiki", "nav", "--json", env={"WIKI_HOME": str(wiki_home)})
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["pending_synthesis"], [])
            self.assertEqual(payload["counts"]["sources"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
