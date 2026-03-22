"""Tests for building market/theme emotion daily facts."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


class TestBuildEmotionFacts(unittest.TestCase):
    """Emotion fact build tests."""

    def _clear_env(self) -> None:
        for key in ("ASHARE_PLATFORM_HOME",):
            os.environ.pop(key, None)

    def test_build_emotion_facts_persists_market_and_theme_rows(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            self._clear_env()
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from app.models.market_emotion_daily import MarketEmotionDaily
            from app.models.theme_emotion_daily import ThemeEmotionDaily
            from app.pipelines.build_emotion_facts import build_emotion_facts

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()

            history = [
                {
                    "date": "20260311",
                    "continuous_limit_up": [
                        {"code": "000001", "name": "A", "continue_num": 4},
                        {"code": "000002", "name": "B", "continue_num": 3},
                        {"code": "000003", "name": "C", "continue_num": 2},
                    ],
                    "block_top": [
                        {
                            "name": "风电",
                            "limit_up_num": 10,
                            "change": 2.3,
                            "stock_list": [
                                {"code": "000001", "name": "A", "continue_num": 4, "change_tag": "LIMIT_BACK"},
                                {"code": "000004", "name": "D", "continue_num": 1, "change_tag": "FIRST_LIMIT"},
                            ],
                        }
                    ],
                },
                {
                    "date": "20260312",
                    "continuous_limit_up": [
                        {"code": "000001", "name": "A", "continue_num": 5},
                        {"code": "000008", "name": "H", "continue_num": 3},
                        {"code": "000009", "name": "I", "continue_num": 2},
                        {"code": "000005", "name": "E", "continue_num": 3},
                    ],
                    "block_top": [
                        {
                            "name": "风电",
                            "limit_up_num": 12,
                            "change": 1.8,
                            "stock_list": [
                                {"code": "000001", "name": "A", "continue_num": 5, "change_tag": "LIMIT_BACK"},
                                {"code": "000006", "name": "F", "continue_num": 1, "change_tag": "FIRST_LIMIT"},
                            ],
                        },
                        {
                            "name": "储能",
                            "limit_up_num": 8,
                            "change": 1.2,
                            "stock_list": [
                                {"code": "000007", "name": "G", "continue_num": 2, "change_tag": "LIMIT_BACK"},
                            ],
                        },
                    ],
                },
                {
                    "date": "20260313",
                    "continuous_limit_up": [
                        {"code": "000001", "name": "A", "continue_num": 6},
                        {"code": "000008", "name": "H", "continue_num": 4},
                        {"code": "000009", "name": "I", "continue_num": 3},
                    ],
                    "block_top": [
                        {
                            "name": "风电",
                            "limit_up_num": 14,
                            "change": 0.9,
                            "stock_list": [
                                {"code": "000001", "name": "A", "continue_num": 6, "change_tag": "LIMIT_BACK"},
                                {"code": "000010", "name": "J", "continue_num": 1, "change_tag": "FIRST_LIMIT"},
                                {"code": "000011", "name": "K", "continue_num": 1, "change_tag": "HIGH_LIMIT"},
                            ],
                        },
                        {
                            "name": "海工装备",
                            "limit_up_num": 9,
                            "change": 0.6,
                            "stock_list": [
                                {"code": "000012", "name": "L", "continue_num": 2, "change_tag": "LIMIT_BACK"},
                                {"code": "000013", "name": "M", "continue_num": 1, "change_tag": "FIRST_LIMIT"},
                            ],
                        },
                    ],
                },
            ]

            result = build_emotion_facts(
                trade_date="2026-03-13",
                history_fetcher=lambda **_: history,
                sentiment_fetcher=lambda day: {
                    "20260311": {
                        "limit_up": 52,
                        "limit_down": 4,
                        "blowup_rate": 0.10,
                        "seal_rate": 0.80,
                        "limit_up_history_num": 60,
                        "limit_up_open_num": 8,
                        "limit_down_history_num": 5,
                        "limit_down_open_num": 1,
                    },
                    "20260312": {
                        "limit_up": 48,
                        "limit_down": 6,
                        "blowup_rate": 0.12,
                        "seal_rate": 0.75,
                        "limit_up_history_num": 55,
                        "limit_up_open_num": 7,
                        "limit_down_history_num": 7,
                        "limit_down_open_num": 1,
                    },
                    "20260313": {
                        "limit_up": 45,
                        "limit_down": 11,
                        "blowup_rate": 0.28,
                        "seal_rate": 0.66,
                        "limit_up_history_num": 62,
                        "limit_up_open_num": 17,
                        "limit_down_history_num": 15,
                        "limit_down_open_num": 4,
                    },
                }[day],
                breadth_fetcher=lambda day: type(
                    "Breadth",
                    (),
                    {
                        "trade_date": day,
                        "advance_count": 1200,
                        "decline_count": 3100,
                        "flat_count": 180,
                        "zdfb_bins": [100, 200, 500],
                        "universe_total": 4480,
                    },
                )(),
                turnover_fetcher=lambda day: type(
                    "Turnover",
                    (),
                    {
                        "trade_date": day,
                        "market_volume": 23027.77,
                        "source_name": "同花顺全A(沪深京)",
                        "source_code": "883957",
                    },
                )(),
            )
            self.assertEqual(result["market_rows_written"], 1)
            self.assertEqual(result["theme_rows_written"], 2)

            with session_module.open_session() as session:
                market_row = session.query(MarketEmotionDaily).one()
                self.assertEqual(market_row.trade_date.isoformat(), "2026-03-13")
                self.assertEqual(market_row.highest_board, 6)
                self.assertEqual(market_row.limit_up_ladder_count, 3)
                self.assertEqual(market_row.board_ge_3_count, 3)
                self.assertEqual(market_row.top_theme_name, "风电")
                self.assertEqual(market_row.top_theme_limit_up_num, 14)
                self.assertEqual(market_row.limit_up_count, 45)
                self.assertEqual(market_row.limit_down_count, 11)
                self.assertAlmostEqual(market_row.blowup_rate or 0.0, 0.28, places=6)
                self.assertAlmostEqual(market_row.seal_rate or 0.0, 0.66, places=6)
                self.assertEqual(market_row.advance_count, 1200)
                self.assertEqual(market_row.decline_count, 3100)
                self.assertEqual(market_row.flat_count, 180)
                self.assertEqual(market_row.promotion_2to3_total, 2)
                self.assertEqual(market_row.promotion_2to3_success, 1)
                self.assertEqual(market_row.promotion_3to4_total, 2)
                self.assertEqual(market_row.promotion_3to4_success, 1)
                self.assertAlmostEqual(market_row.market_volume or 0.0, 23027.77, places=2)
                self.assertEqual(market_row.limit_down_count_3d_delta, 7)
                self.assertEqual(market_row.highest_board_3d_delta, 2)
                self.assertEqual(market_row.evidence_json["market_breadth"]["zdfb_bins"], [100, 200, 500])
                self.assertEqual(
                    market_row.evidence_json["promotion"]["candidates_2to3"],
                    ["000007", "000009"],
                )
                self.assertEqual(
                    market_row.evidence_json["promotion"]["candidates_3to4"],
                    ["000005", "000008"],
                )

                theme_rows = (
                    session.query(ThemeEmotionDaily)
                    .order_by(ThemeEmotionDaily.theme_rank.asc())
                    .all()
                )
                self.assertEqual([row.theme_name for row in theme_rows], ["风电", "海工装备"])
                self.assertEqual(theme_rows[0].leader_board_max, 6)
                self.assertEqual(theme_rows[0].limit_up_num_3d_delta, 4)
                self.assertEqual(theme_rows[0].first_limit_count, 1)
                self.assertEqual(theme_rows[0].limit_back_count, 1)
                self.assertEqual(theme_rows[0].high_limit_count, 1)

            self._clear_env()
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()


if __name__ == "__main__":
    unittest.main()
