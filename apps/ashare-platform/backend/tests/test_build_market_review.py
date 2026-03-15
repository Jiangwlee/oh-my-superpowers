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
            from app.models.market_emotion_daily import MarketEmotionDaily
            from app.models.market_review_daily import MarketReviewDaily
            from app.models.theme_pool_daily import ThemePoolDaily
            from app.models.trend_pool_daily import TrendPoolDaily
            from app.pipelines.build_market_review import build_market_review

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()

            with session_module.open_session() as session:
                session.add(
                    MarketEmotionDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="e1",
                        limit_up_count=59,
                        limit_down_count=13,
                        highest_board=5,
                        limit_up_ladder_count=8,
                        board_ge_2_count=8,
                        board_ge_3_count=3,
                        board_ge_4_count=2,
                        theme_count=20,
                        top_theme_name="深海科技",
                        top_theme_limit_up_num=13,
                        blowup_rate=0.23,
                        risk_score=5.4,
                        emotion_score=12.8,
                        cycle_stage_hint="weakening",
                    )
                )
                session.add(
                    ThemePoolDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="r1",
                        theme_name="深海科技",
                        theme_rank=1,
                        theme_stage="middle",
                        market_attitude="情绪退潮但题材未崩",
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

    def test_build_market_review_uses_semantic_enricher_when_enabled(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            os.environ["ASHARE_PLATFORM_HOME"] = tmp_dir
            os.environ["ASHARE_MARKET_REVIEW_SEMANTIC_ENRICH_ENABLED"] = "1"
            import app.core.config as config_module
            import app.db.session as session_module
            from app.models.market_emotion_daily import MarketEmotionDaily
            from app.models.market_review_daily import MarketReviewDaily
            from app.models.theme_pool_daily import ThemePoolDaily
            from app.models.trend_pool_daily import TrendPoolDaily
            from app.pipelines.build_market_review import build_market_review

            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()
            session_module.init_db()

            with session_module.open_session() as session:
                session.add(
                    MarketEmotionDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="e1",
                        limit_up_count=59,
                        limit_down_count=13,
                        highest_board=5,
                        limit_up_ladder_count=8,
                        board_ge_2_count=8,
                        board_ge_3_count=3,
                        board_ge_4_count=2,
                        theme_count=20,
                        top_theme_name="深海科技",
                        top_theme_limit_up_num=13,
                        blowup_rate=0.23,
                        risk_score=5.4,
                        emotion_score=12.8,
                        cycle_stage_hint="weakening",
                    )
                )
                session.add(
                    ThemePoolDaily(
                        trade_date=date.fromisoformat("2026-03-13"),
                        run_id="r1",
                        theme_name="深海科技",
                        theme_rank=1,
                        theme_stage="middle",
                        market_attitude="情绪退潮但题材未崩",
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

            result = build_market_review(
                trade_date="2026-03-13",
                semantic_enricher=lambda row: {
                    **(
                        self.assertEqual(row["market_emotion_json"]["limit_down_count"], 13) or
                        self.assertEqual(row["themes_json"][0]["theme_stage"], "middle") or
                        {}
                    ),
                    **row,
                    "summary": "市场主线延续，情绪回暖。",
                    "report_markdown": "# 市场复盘\n\n## 市场情绪定位\n\n情绪分歧加剧。\n\n## 交易结论\n\n只做核心主线。",
                },
            )
            self.assertTrue(result["stored"])

            with session_module.open_session() as session:
                row = session.query(MarketReviewDaily).one()
                self.assertEqual(row.summary, "市场主线延续，情绪回暖。")
                self.assertIn("## 市场情绪定位", row.report_markdown)

            os.environ.pop("ASHARE_PLATFORM_HOME", None)
            os.environ.pop("ASHARE_MARKET_REVIEW_SEMANTIC_ENRICH_ENABLED", None)
            config_module.get_settings.cache_clear()
            session_module.reset_db_runtime()


if __name__ == "__main__":
    unittest.main()
