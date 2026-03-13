"""Tests for ephemeral data cleanup."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.services.retention_service import cleanup_ephemeral


class TestCleanupEphemeralData(unittest.TestCase):
    """Cleanup tests."""

    def test_cleanup_ephemeral_removes_expired_files(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            stale = root / "stale.json"
            stale.write_text("{}", encoding="utf-8")
            removed = cleanup_ephemeral(root, max_age_days=0)
            self.assertEqual(removed, 1)
            self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
