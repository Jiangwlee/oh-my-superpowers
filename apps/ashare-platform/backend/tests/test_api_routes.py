"""Tests for backend API routes."""

from __future__ import annotations

import os
import sys
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class TestApiRoutes(unittest.TestCase):
    """API route tests."""

    def test_trend_pool_daily_route_exists(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from app.api.routes.trend_pool import get_trend_pool_daily
            from app.models.trend_pool_daily import TrendPoolDaily

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()
            with session_module.open_session() as session:
                session.add(
                    TrendPoolDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="r1",
                        code="000001",
                        name="平安银行",
                        rank=1,
                        score_total=88.0,
                        star_rating=4,
                        emotion_level=3,
                        trade_signal="观察",
                        is_uptrend=True,
                    )
                )
                session.commit()

            rows = get_trend_pool_daily(
                trade_date="2026-03-13",
                min_star=0,
                is_uptrend=None,
                limit=100,
                sort="rank",
            )
            self.assertEqual(rows[0].code, "000001")

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

    def test_runs_route_exists(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from app.api.routes.runs import list_runs
            from app.models.run import Run

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()
            with session_module.open_session() as session:
                session.add(
                    Run(
                        run_id="run-1",
                        trade_date=date.fromisoformat("2026-03-13"),
                        pipeline_name="build-trend-pool",
                        status="success",
                        degraded=False,
                    )
                )
                session.commit()

            rows = list_runs(
                trade_date="2026-03-13",
                pipeline_name="build-trend-pool",
                status="success",
                limit=20,
            )
            self.assertEqual(rows[0].run_id, "run-1")

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

    def test_market_review_route_returns_row(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from app.api.routes.market_reviews import get_market_review_daily
            from app.models.market_review_daily import MarketReviewDaily

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()
            with session_module.open_session() as session:
                session.add(
                    MarketReviewDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="r1",
                        regime="strong",
                        position_guidance="60-80%",
                        main_themes_json=["风电"],
                        emerging_themes_json=[],
                        fading_themes_json=[],
                        summary="主线聚焦风电。",
                        report_markdown="# 市场复盘",
                    )
                )
                session.commit()

            row = get_market_review_daily("2026-03-13")
            self.assertEqual(row.trade_date, "2026-03-13")
            self.assertEqual(row.summary, "主线聚焦风电。")

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

    def test_market_review_route_returns_404_when_missing(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from fastapi import HTTPException
            from app.api.routes.market_reviews import get_market_review_daily

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()

            with self.assertRaises(HTTPException) as ctx:
                get_market_review_daily("2026-03-13")
            self.assertEqual(ctx.exception.status_code, 404)

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()


if __name__ == "__main__":
    unittest.main()
