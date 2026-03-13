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

    def test_build_theme_pool_keeps_only_supported_themes_and_stocks(self) -> None:
        with TemporaryDirectory() as tmp_dir:
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
                        }
                    ],
                },
            )
            self.assertEqual(result["themes_written"], 1)
            self.assertEqual(result["stocks_written"], 3)

            with session_module.open_session() as session:
                self.assertEqual(session.query(ThemePoolDaily).count(), 1)
                self.assertEqual(session.query(ThemeStockDaily).count(), 3)
                stock_codes = [row.code for row in session.query(ThemeStockDaily).order_by(ThemeStockDaily.rank_in_theme.asc()).all()]
                self.assertEqual(stock_codes, ["000001", "000002", "000004"])

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()


if __name__ == "__main__":
    unittest.main()
