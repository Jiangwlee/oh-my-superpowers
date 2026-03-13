"""Tests for building market review daily facts."""

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


class TestBuildMarketReview(unittest.TestCase):
    """Market review build tests."""

    def test_build_market_review_persists_report(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            import app.core.config as config_module
            import app.db.session as session_module
            from app.models.market_review_daily import MarketReviewDaily
            from app.models.theme_pool_daily import ThemePoolDaily
            from app.models.trend_pool_daily import TrendPoolDaily
            from app.pipelines.build_market_review import build_market_review

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()

            with session_module.open_session() as session:
                session.add(
                    ThemePoolDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="r1",
                        theme_name="深海科技",
                        theme_rank=1,
                    )
                )
                session.add(
                    TrendPoolDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="r1",
                        code="000001",
                        name="平安银行",
                        score_total=88.0,
                        star_rating=4,
                    )
                )
                session.commit()

            result = build_market_review(trade_date="2026-03-13")
            self.assertTrue(result["stored"])

            with session_module.open_session() as session:
                rows = session.query(MarketReviewDaily).all()
                self.assertEqual(len(rows), 1)
                self.assertIn("深海科技", rows[0].report_markdown)

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()


if __name__ == "__main__":
    unittest.main()
