"""T1 tests for `omp wiki ingest`."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
OMP_BIN = REPO_ROOT / "bin" / "omp"


def run_ingest(wiki_home: Path, title: str, body: str) -> subprocess.CompletedProcess[str]:
    """Ingest a text snippet via the CLI."""

    env = {**os.environ, "OMP_HOME": str(REPO_ROOT), "WIKI_HOME": str(wiki_home)}
    return subprocess.run(
        [str(OMP_BIN), "wiki", "ingest", "--text", "--title", title],
        input=f"# {title}\n\n{body}\n",
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


class TestWikiIngest(unittest.TestCase):
    """Validate ingest writes normalized raw/*.md files."""

    def test_ingest_text_creates_raw_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_home = Path(tmpdir) / "wiki-home"
            init_result = subprocess.run(
                [str(OMP_BIN), "wiki", "init"],
                env={**os.environ, "OMP_HOME": str(REPO_ROOT), "WIKI_HOME": str(wiki_home)},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(init_result.returncode, 0, init_result.stderr)

            result = run_ingest(
                wiki_home,
                "CLI Runtime Notes",
                "CLI tools should stay filesystem-first.",
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            raw_file = wiki_home / "raw" / "cli-runtime-notes.md"
            self.assertTrue(raw_file.is_file())

            content = raw_file.read_text(encoding="utf-8")
            self.assertIn("# CLI Runtime Notes", content)
            self.assertIn("> Source: text-input", content)
            self.assertIn("> Collected:", content)
            self.assertIn("CLI tools should stay filesystem-first.", content)

    def test_ingest_does_not_touch_wiki_dir(self) -> None:
        """Ingest must only write to raw/, never to wiki/."""

        with tempfile.TemporaryDirectory() as tmpdir:
            wiki_home = Path(tmpdir) / "wiki-home"
            subprocess.run(
                [str(OMP_BIN), "wiki", "init"],
                env={**os.environ, "OMP_HOME": str(REPO_ROOT), "WIKI_HOME": str(wiki_home)},
                text=True,
                capture_output=True,
                check=False,
            )
            run_ingest(wiki_home, "Alpha", "alpha body")

            for section in ("sources", "concepts", "maps"):
                section_dir = wiki_home / "wiki" / section
                self.assertTrue(section_dir.is_dir())
                self.assertEqual(list(section_dir.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
