"""Tests for backend app import."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class TestAppImport(unittest.TestCase):
    """App import tests."""

    def test_backend_app_importable(self) -> None:
        from app.main import app

        self.assertIsNotNone(app)


if __name__ == "__main__":
    unittest.main()
