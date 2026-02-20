import tempfile
import unittest
from pathlib import Path

import sys

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))
_SCRIPT_DIR = _SKILL_ROOT / "scripts"
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import common
import init_session


class SessionInitTest(unittest.TestCase):
    def test_memory_root_accepts_skill_base_without_double_nesting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_root = Path(tmpdir) / ".memory" / "vibe-coding-discussion"
            memory_root.mkdir(parents=True, exist_ok=True)

            layout = common.ensure_layout(str(memory_root))

            self.assertEqual(layout["base"], memory_root.resolve())
            self.assertEqual(layout["sessions"], memory_root.resolve() / "sessions")

    def test_background_file_is_copied_into_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            background_file = workspace / "background.md"
            background_text = "# Topic background\n\nThis is shared context."
            background_file.write_text(background_text, encoding="utf-8")

            parser = init_session.build_parser()
            args = parser.parse_args(
                [
                    "--memory-root",
                    str(workspace / ".memory"),
                    "--topic",
                    "session with background snapshot",
                    "--participants",
                    "user,claude-code",
                    "--background-file",
                    str(background_file),
                ]
            )
            result = init_session.run(args)

            session_dir = Path(result["session_dir"])
            saved_background = session_dir / "background.md"
            self.assertTrue(saved_background.exists())
            self.assertEqual(saved_background.read_text(encoding="utf-8"), background_text + "\n")

            meta = common.load_meta(session_dir / "meta.json")
            self.assertEqual(meta.get("background_file"), "background.md")


if __name__ == "__main__":
    unittest.main()
