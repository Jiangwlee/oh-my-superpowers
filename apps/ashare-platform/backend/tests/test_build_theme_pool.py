"""Tests for building theme pool daily facts."""

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


class TestBuildThemePool(unittest.TestCase):
    """Theme pool build tests."""

    def _clear_env(self) -> None:
        for key in (
            "ASHARE_PLATFORM_HOME",
            "ASHARE_THEME_POOL_PROFILE",
            "ASHARE_THEME_POOL_MIN_TREND_STOCK_COUNT",
            "ASHARE_THEME_POOL_MIN_CORE_TREND_STOCK_COUNT",
            "ASHARE_THEME_POOL_WEIGHT_THEME_STRENGTH",
            "ASHARE_THEME_POOL_WEIGHT_TREND_STOCK_COUNT",
            "ASHARE_THEME_POOL_WEIGHT_CORE_TREND_STOCK_COUNT",
            "ASHARE_THEME_POOL_WEIGHT_STRONGEST_TREND_SCORE",
            "ASHARE_THEME_SEMANTIC_ENRICH_ENABLED",
        ):
            os.environ.pop(key, None)

    def test_build_theme_pool_keeps_only_supported_themes_and_stocks(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            self._clear_env()
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from app.models.trend_pool_daily import TrendPoolDaily
            from app.models.theme_pool_daily import ThemePoolDaily
            from app.models.theme_stock_daily import ThemeStockDaily
            from app.pipelines.build_theme_pool import build_theme_pool

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()
            with session_module.open_session() as session:
                session.add_all(
                    [
                        TrendPoolDaily(
                            trade_date=date.fromisoformat("2026-03-13"),
                            run_id="trend-run",
                            code="000001",
                            name="平安银行",
                            rank=1,
                            score_total=88.0,
                            star_rating=4,
                            emotion_level=3,
                            trade_signal="观察",
                            is_uptrend=True,
                        ),
                        TrendPoolDaily(
                            trade_date=date.fromisoformat("2026-03-13"),
                            run_id="trend-run",
                            code="000004",
                            name="国华网安",
                            rank=4,
                            score_total=91.0,
                            star_rating=5,
                            emotion_level=4,
                            trade_signal="观察",
                            is_uptrend=True,
                        ),
                    ]
                )
                session.commit()

            result = build_theme_pool(
                trade_date="2026-03-13",
                snapshot_fetcher=lambda **_: {
                    "date": "20260313",
                    "block_top": [
                        {
                            "name": "深海科技",
                            "limit_up_num": 4,
                            "change": 3.2,
                            "stock_list": [
                                {"code": "000001", "name": "平安银行", "continue_num": 2},
                                {"code": "000002", "name": "万科A", "continue_num": 1},
                                {"code": "000004", "name": "国华网安", "continue_num": 1},
                                {"code": "000005", "name": "世纪星源", "continue_num": 1},
                            ],
                        },
                        {
                            "name": "纯题材噪音",
                            "limit_up_num": 2,
                            "change": 1.1,
                            "stock_list": [
                                {"code": "000006", "name": "深振业A", "continue_num": 1},
                                {"code": "000007", "name": "全新好", "continue_num": 1},
                            ],
                        },
                        {
                            "name": "趋势更强",
                            "limit_up_num": 3,
                            "change": 2.0,
                            "stock_list": [
                                {"code": "000004", "name": "国华网安", "continue_num": 2},
                                {"code": "000008", "name": "神州高铁", "continue_num": 1},
                            ],
                        },
                    ],
                },
            )
            self.assertEqual(result["themes_written"], 2)
            self.assertEqual(result["stocks_written"], 5)

            with session_module.open_session() as session:
                theme_rows = session.query(ThemePoolDaily).order_by(ThemePoolDaily.theme_rank.asc()).all()
                self.assertEqual(len(theme_rows), 2)
                self.assertEqual(theme_rows[0].theme_name, "深海科技")
                self.assertGreater(theme_rows[0].theme_score or 0.0, theme_rows[1].theme_score or 0.0)
                self.assertEqual(theme_rows[0].trend_stock_count, 2)
                self.assertEqual(theme_rows[0].core_trend_stock_count, 2)
                self.assertEqual(theme_rows[1].trend_stock_count, 1)

                self.assertEqual(session.query(ThemeStockDaily).count(), 5)
                deep_sea_codes = [
                    row.code
                    for row in session.query(ThemeStockDaily)
                    .filter(ThemeStockDaily.theme_name == "深海科技")
                    .order_by(ThemeStockDaily.rank_in_theme.asc())
                    .all()
                ]
                stronger_codes = [
                    row.code
                    for row in session.query(ThemeStockDaily)
                    .filter(ThemeStockDaily.theme_name == "趋势更强")
                    .order_by(ThemeStockDaily.rank_in_theme.asc())
                    .all()
                ]
                self.assertEqual(deep_sea_codes, ["000001", "000002", "000004"])
                self.assertEqual(stronger_codes, ["000004", "000008"])

            self._clear_env()
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

    def test_build_theme_pool_filters_theme_when_core_trend_threshold_is_not_met(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            self._clear_env()
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            os.environ["ASHARE_THEME_POOL_MIN_CORE_TREND_STOCK_COUNT"] = "2"
            import app.core.config as config_module
            import app.db.session as session_module
            from app.models.trend_pool_daily import TrendPoolDaily
            from app.models.theme_pool_daily import ThemePoolDaily
            from app.pipelines.build_theme_pool import build_theme_pool

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()
            with session_module.open_session() as session:
                session.add(
                    TrendPoolDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="trend-run",
                        code="000004",
                        name="国华网安",
                        rank=4,
                        score_total=91.0,
                        star_rating=5,
                        emotion_level=4,
                        trade_signal="观察",
                        is_uptrend=True,
                    )
                )
                session.commit()

            result = build_theme_pool(
                trade_date="2026-03-13",
                snapshot_fetcher=lambda **_: {
                    "date": "20260313",
                    "block_top": [
                        {
                            "name": "核心不强",
                            "limit_up_num": 4,
                            "change": 3.2,
                            "stock_list": [
                                {"code": "000001", "name": "平安银行", "continue_num": 2},
                                {"code": "000002", "name": "万科A", "continue_num": 1},
                                {"code": "000004", "name": "国华网安", "continue_num": 1},
                            ],
                        }
                    ],
                },
            )
            self.assertEqual(result["themes_written"], 0)

            with session_module.open_session() as session:
                self.assertEqual(session.query(ThemePoolDaily).count(), 0)

            self._clear_env()
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()

    def test_build_theme_pool_uses_semantic_enricher_when_enabled(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            self._clear_env()
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            os.environ["ASHARE_THEME_SEMANTIC_ENRICH_ENABLED"] = "1"
            import app.core.config as config_module
            import app.db.session as session_module
            from app.models.market_emotion_daily import MarketEmotionDaily
            from app.models.theme_emotion_daily import ThemeEmotionDaily
            from app.models.trend_pool_daily import TrendPoolDaily
            from app.models.theme_pool_daily import ThemePoolDaily
            from app.pipelines.build_theme_pool import build_theme_pool

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()
            with session_module.open_session() as session:
                session.add(
                    TrendPoolDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="trend-run",
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
                session.add(
                    MarketEmotionDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="emotion-run",
                        limit_down_count=13,
                        highest_board=5,
                        limit_up_ladder_count=8,
                        board_ge_2_count=8,
                        board_ge_3_count=3,
                        board_ge_4_count=2,
                        theme_count=20,
                        top_theme_name="风电",
                        top_theme_limit_up_num=13,
                        risk_score=5.0,
                        emotion_score=12.0,
                        cycle_stage_hint="weakening",
                    )
                )
                session.add(
                    ThemeEmotionDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="emotion-run",
                        theme_name="深海科技",
                        theme_rank=1,
                        limit_up_num=4,
                        sample_stock_count=1,
                        leader_names_json=["平安银行"],
                        leader_board_max=2,
                        leader_board_count_ge_2=1,
                        first_limit_count=0,
                        limit_back_count=1,
                        high_limit_count=0,
                        heat_score=8.0,
                        risk_score=2.0,
                        theme_cycle_hint="ferment",
                    )
                )
                session.commit()

            def fake_semantic_enricher(theme_row: dict, stock_rows: list[dict]) -> tuple[dict, list[dict]]:
                self.assertEqual(theme_row["market_emotion_json"]["limit_down_count"], 13)
                self.assertEqual(theme_row["theme_emotion_json"]["theme_cycle_hint"], "ferment")
                theme_row["market_attitude"] = "认可度高"
                theme_row["summary"] = "语义总结"
                stock_rows[0]["comment"] = "核心观察"
                return theme_row, stock_rows

            result = build_theme_pool(
                trade_date="2026-03-13",
                snapshot_fetcher=lambda **_: {
                    "date": "20260313",
                    "block_top": [
                        {
                            "name": "深海科技",
                            "limit_up_num": 4,
                            "change": 3.2,
                            "stock_list": [
                                {"code": "000001", "name": "平安银行", "continue_num": 2},
                            ],
                        }
                    ],
                },
                semantic_enricher=fake_semantic_enricher,
            )
            self.assertEqual(result["themes_written"], 1)

            with session_module.open_session() as session:
                row = session.query(ThemePoolDaily).one()
                self.assertEqual(row.market_attitude, "认可度高")
                self.assertEqual(row.summary, "语义总结")

            self._clear_env()
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()


if __name__ == "__main__":
    unittest.main()
