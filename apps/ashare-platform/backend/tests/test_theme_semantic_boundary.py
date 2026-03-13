"""Tests for deterministic vs semantic boundary in theme enrichment."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.pipelines.enrich_theme_semantics import enrich_theme_semantics


class TestThemeSemanticBoundary(unittest.TestCase):
    """Semantic boundary tests."""

    def test_theme_semantics_do_not_replace_deterministic_fields(self) -> None:
        theme = {
            "trade_date": "2026-03-13",
            "run_id": "r1",
            "theme_name": "深海科技",
            "theme_rank": 1,
            "theme_strength": 9.2,
            "core_stock_count": 3,
            "theme_stage": "early",
            "summary": None,
        }
        stocks = [
            {
                "trade_date": "2026-03-13",
                "run_id": "r1",
                "theme_name": "深海科技",
                "code": "000001",
                "name": "平安银行",
                "role": "leader",
                "is_core": True,
                "rank_in_theme": 1,
                "trend_score": 88.0,
                "star_rating": 4,
                "emotion_level": 3,
                "comment": None,
            }
        ]

        def fake_enricher(theme_row: dict, stock_rows: list[dict]) -> tuple[dict, list[dict]]:
            theme_row["theme_strength"] = 1.0
            theme_row["theme_stage"] = "middle"
            theme_row["summary"] = "语义总结"
            stock_rows[0]["trend_score"] = 1.0
            stock_rows[0]["comment"] = "语义评论"
            return theme_row, stock_rows

        enriched_theme, enriched_stocks = enrich_theme_semantics(theme, stocks, enrich_fn=fake_enricher)
        self.assertEqual(enriched_theme["theme_stage"], "middle")
        self.assertEqual(enriched_theme["summary"], "语义总结")
        self.assertEqual(enriched_theme["theme_strength"], 9.2)
        self.assertEqual(enriched_stocks[0]["trend_score"], 88.0)
        self.assertEqual(enriched_stocks[0]["comment"], "语义评论")


if __name__ == "__main__":
    unittest.main()
