"""Tests for backend runtime config."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class TestConfig(unittest.TestCase):
    """Config tests."""

    def test_runtime_paths_are_resolved(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            try:
                import app.core.config as config_module

                config_module.get_settings.cache_clear()
                settings = config_module.get_settings()
                self.assertTrue(settings.ephemeral_dir.exists())
                self.assertEqual(settings.database_path.name, "ashare_platform.db")
            finally:
                os.environ.pop("ASHARE_PLATFORM_HOME", None)
                config_module.get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
