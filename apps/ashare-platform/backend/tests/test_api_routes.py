"""Tests for backend API routes."""

from __future__ import annotations

import os
import sys
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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

    def test_market_emotion_routes_return_rows(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from app.api.routes.emotion import get_market_emotion_daily, get_market_emotion_history
            from app.models.market_emotion_daily import MarketEmotionDaily

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()
            with session_module.open_session() as session:
                session.add(
                    MarketEmotionDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="r1",
                        source="ths",
                        highest_board=5,
                        limit_up_ladder_count=3,
                        board_ge_2_count=2,
                        board_ge_3_count=1,
                        board_ge_4_count=1,
                        theme_count=4,
                        advance_count=1200,
                        decline_count=3000,
                        flat_count=150,
                        seal_rate=0.71,
                        market_volume=23027.77,
                    )
                )
                session.commit()

            row = get_market_emotion_daily("2026-03-13")
            self.assertEqual(row.trade_date, "2026-03-13")
            self.assertEqual(row.advance_count, 1200)
            rows = get_market_emotion_history(days=20, end_date=None)
            self.assertEqual(len(rows), 1)
            self.assertAlmostEqual(rows[0].market_volume or 0.0, 23027.77, places=2)

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

    def test_market_emotion_daily_returns_404_when_missing(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from fastapi import HTTPException
            from app.api.routes.emotion import get_market_emotion_daily

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()

            with self.assertRaises(HTTPException) as ctx:
                get_market_emotion_daily("2026-03-13")
            self.assertEqual(ctx.exception.status_code, 404)

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

    def test_theme_emotion_routes_support_filters_and_history(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from app.api.routes.emotion import get_theme_emotion_daily, get_theme_emotion_history
            from app.models.theme_emotion_daily import ThemeEmotionDaily

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()
            with session_module.open_session() as session:
                session.add_all(
                    [
                        ThemeEmotionDaily(
                            trade_date=date.fromisoformat("2026-03-12"),
                            run_id="r1",
                            theme_name="风电",
                            theme_rank=2,
                            source="ths_block_top",
                            limit_up_num=8,
                            sample_stock_count=10,
                            leader_board_max=3,
                            leader_board_count_ge_2=1,
                            first_limit_count=2,
                            limit_back_count=1,
                            high_limit_count=0,
                            heat_score=8.0,
                            theme_cycle_hint="ferment",
                        ),
                        ThemeEmotionDaily(
                            trade_date=date.fromisoformat("2026-03-13"),
                            run_id="r2",
                            theme_name="风电",
                            theme_rank=1,
                            source="ths_block_top",
                            limit_up_num=10,
                            sample_stock_count=12,
                            leader_board_max=4,
                            leader_board_count_ge_2=2,
                            first_limit_count=3,
                            limit_back_count=1,
                            high_limit_count=0,
                            heat_score=18.0,
                            theme_cycle_hint="main_rise",
                        ),
                        ThemeEmotionDaily(
                            trade_date=date.fromisoformat("2026-03-13"),
                            run_id="r2",
                            theme_name="储能",
                            theme_rank=2,
                            source="ths_block_top",
                            limit_up_num=7,
                            sample_stock_count=9,
                            leader_board_max=3,
                            leader_board_count_ge_2=1,
                            first_limit_count=2,
                            limit_back_count=0,
                            high_limit_count=1,
                            heat_score=9.0,
                            theme_cycle_hint="ferment",
                        ),
                    ]
                )
                session.commit()

            daily_rows = get_theme_emotion_daily(
                trade_date="2026-03-13",
                cycle_hint="main_rise",
                limit=50,
                sort="-heat_score",
            )
            self.assertEqual([row.theme_name for row in daily_rows], ["风电"])
            history_rows = get_theme_emotion_history(theme_name="风电", days=20)
            self.assertEqual([row.trade_date for row in history_rows], ["2026-03-12", "2026-03-13"])

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

    def test_theme_daily_stocks_exposes_evidence_fields(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from app.api.routes.theme_pool import get_theme_daily_stocks
            from app.models.theme_stock_daily import ThemeStockDaily

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()
            with session_module.open_session() as session:
                session.add(
                    ThemeStockDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="r1",
                        theme_name="新能源汽车",
                        code="002913",
                        name="奥士康",
                        role="leader",
                        is_core=True,
                        rank_in_theme=1,
                        trend_score=85.2,
                        star_rating=4,
                        emotion_level=3,
                        comment=None,
                        evidence_json={
                            "continue_num": 3,
                            "change_rate": 10.01,
                            "reason_type": "新能源汽车+锂电池",
                            "change_tag": "HIGH_LIMIT",
                        },
                    )
                )
                session.commit()

            rows = get_theme_daily_stocks("新能源汽车", trade_date="2026-03-13")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].continue_num, 3)
            self.assertAlmostEqual(rows[0].change_rate or 0.0, 10.01, places=2)
            self.assertEqual(rows[0].reason_type, "新能源汽车+锂电池")
            self.assertEqual(rows[0].change_tag, "HIGH_LIMIT")

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

    def test_kline_daily_route_formats_fetcher_payload(self) -> None:
        from app.api.routes.kline import get_daily_kline

        with patch(
            "app.api.routes.kline.fetch_jrj_daily_kline",
            return_value=[
                {
                    "time": 20260317,
                    "open": 12.5,
                    "high": 13.0,
                    "low": 12.3,
                    "close": 12.8,
                    "volume": 15234.0,
                    "amount": 198563200.0,
                    "change_pct": None,
                },
                {
                    "time": 20260318,
                    "open": 12.8,
                    "high": 13.2,
                    "low": 12.7,
                    "close": 13.1,
                    "volume": 1523400.0,
                    "amount": 198563200.0,
                    "change_pct": 2.34,
                },
            ],
        ) as mocked_fetch:
            rows = get_daily_kline("002913", days=2)

        mocked_fetch.assert_called_once_with("002913", range_num=2)
        self.assertEqual([row.date for row in rows], ["2026-03-17", "2026-03-18"])
        self.assertEqual(rows[1].volume, 1523400)
        self.assertAlmostEqual(rows[1].amount, 1.99, places=2)
        self.assertAlmostEqual(rows[1].change_pct or 0.0, 2.34, places=2)

    def test_trade_dates_latest_route_returns_single_date(self) -> None:
        from app.api.routes.trade_dates import get_latest_trade_date

        with patch(
            "app.api.routes.trade_dates.resolve_trade_dates",
            return_value=["2026-03-20"],
        ) as mocked_resolve:
            row = get_latest_trade_date()

        mocked_resolve.assert_called_once()
        self.assertEqual(row.trade_date, "2026-03-20")

    def test_trade_dates_recent_route_returns_window(self) -> None:
        from app.api.routes.trade_dates import get_recent_trade_dates

        with patch(
            "app.api.routes.trade_dates.resolve_trade_dates",
            return_value=["2026-03-17", "2026-03-18", "2026-03-19", "2026-03-20"],
        ) as mocked_resolve:
            row = get_recent_trade_dates(days=4)

        mocked_resolve.assert_called_once()
        self.assertEqual(row.days, 4)
        self.assertEqual(
            row.trade_dates,
            ["2026-03-17", "2026-03-18", "2026-03-19", "2026-03-20"],
        )


if __name__ == "__main__":
    unittest.main()
