"""T1 tests for `omp wiki` CLI skeleton and init contract."""

from __future__ import annotations

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


class TestWikiCli(unittest.TestCase):
    """Validate top-level `omp wiki` command exposure."""

    def test_wiki_help_lists_minimal_commands(self) -> None:
        result = run_omp("wiki", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("init", "ingest", "nav", "lint"):
            self.assertIn(command, result.stdout)


class TestWikiInit(unittest.TestCase):
    """Validate global wiki initialization."""

    def test_init_creates_required_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_home = Path(tmpdir) / "wiki-home"
            result = run_omp("wiki", "init", env={"WIKI_HOME": str(wiki_home)})
            self.assertEqual(result.returncode, 0, result.stderr)

            self.assertTrue((wiki_home / "raw").is_dir())
            self.assertTrue((wiki_home / "wiki").is_dir())
            self.assertTrue((wiki_home / "wiki" / "AGENTS.md").is_file())
            self.assertTrue((wiki_home / "wiki" / "index.md").is_file())
            self.assertTrue((wiki_home / "wiki" / "log.md").is_file())
            self.assertTrue((wiki_home / "state.json").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
