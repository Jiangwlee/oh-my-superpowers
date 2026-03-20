"""Tests for retained task run logging."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class TestTaskRunLogging(unittest.TestCase):
    """Task run logging tests."""

    def test_build_trend_pool_task_persists_success_run(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from app.models.run import Run
            from app.tasks.build_trend_pool import run

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

            with patch(
                "app.tasks.build_trend_pool.build_trend_pool",
                return_value={
                    "run_id": "20260313-build-trend-pool-test",
                    "trade_date": "2026-03-13",
                    "rows_written": 3,
                },
            ):
                result = run(
                    trade_date="2026-03-13",
                    max_rank=10,
                )
            self.assertIn("run_id", result)

            with session_module.open_session() as session:
                rows = session.query(Run).all()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].pipeline_name, "build-trend-pool")
                self.assertEqual(rows[0].status, "success")
                self.assertFalse(rows[0].degraded)

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

    def test_collect_task_marks_degraded_when_sources_fail(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from app.models.run import Run
            from app.tasks.collect_ephemeral import run

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

            def fake_collector(*args, **kwargs):
                return {
                    "sources": {
                        "ok_source": {"status": "ok", "error": None},
                        "bad_source": {"status": "error", "error": "boom"},
                    }
                }

            result = run(
                trade_date="2026-03-13",
                news_count=1,
                taoguba_count=1,
                scan_trends=False,
                popularity_max=10,
                collector=fake_collector,  # type: ignore[arg-type]
            )
            self.assertIn("collector_result", result)

            with session_module.open_session() as session:
                rows = session.query(Run).all()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].pipeline_name, "collect-ephemeral")
                self.assertEqual(rows[0].status, "success")
                self.assertTrue(rows[0].degraded)
                self.assertEqual(rows[0].degraded_reasons, ["bad_source:boom"])

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

    def test_red_for_n_days_task_persists_success_run(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from app.models.run import Run
            from app.tasks.red_for_n_days import run

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

            with patch(
                "app.tasks.red_for_n_days.build_red_for_n_days",
                return_value={
                    "run_id": "20260313-red-for-n-days-test",
                    "trade_date": "2026-03-13",
                    "matched_count": 5,
                },
            ):
                result = run(
                    trade_date="2026-03-13",
                    days=7,
                    top_n=2000,
                )
            self.assertIn("run_id", result)

            with session_module.open_session() as session:
                rows = session.query(Run).all()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].pipeline_name, "red-for-n-days")
                self.assertEqual(rows[0].status, "success")
                self.assertFalse(rows[0].degraded)

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()


if __name__ == "__main__":
    unittest.main()
