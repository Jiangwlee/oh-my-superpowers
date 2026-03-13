"""Tests for ephemeral collection task."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class TestCollectEphemeralTask(unittest.TestCase):
    """Task tests for ephemeral collection."""

    def test_collect_ephemeral_returns_run_summary(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            from app.pipelines import collect_ephemeral as pipeline_module

            config_module.get_settings.cache_clear()

            def fake_collector(output_dir: str, **_: object) -> dict[str, object]:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                return {"ok_count": 1, "error_count": 0}

            result = pipeline_module.collect_ephemeral(
                trade_date="2026-03-13",
                collector=fake_collector,
            )

            self.assertIn("run_id", result)
            self.assertEqual(result["trade_date"], "2026-03-13")
            self.assertTrue(Path(result["raw_dir"]).exists())

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
