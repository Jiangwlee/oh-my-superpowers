"""Tests for retained daily fact models."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import UniqueConstraint

from app.models.market_review_daily import MarketReviewDaily
from app.models.market_emotion_daily import MarketEmotionDaily
from app.models.theme_pool_daily import ThemePoolDaily
from app.models.theme_emotion_daily import ThemeEmotionDaily
from app.models.theme_stock_daily import ThemeStockDaily
from app.models.trend_pool_daily import TrendPoolDaily


class TestModels(unittest.TestCase):
    """Model metadata tests."""

    def test_trend_pool_daily_has_date_code_uniqueness(self) -> None:
        constraints = [c for c in TrendPoolDaily.__table__.constraints if isinstance(c, UniqueConstraint)]
        self.assertTrue(any(tuple(c.columns.keys()) == ("trade_date", "code") for c in constraints))

    def test_theme_pool_daily_has_date_theme_uniqueness(self) -> None:
        constraints = [c for c in ThemePoolDaily.__table__.constraints if isinstance(c, UniqueConstraint)]
        self.assertTrue(any(tuple(c.columns.keys()) == ("trade_date", "theme_name") for c in constraints))

    def test_theme_stock_daily_has_date_theme_code_uniqueness(self) -> None:
        constraints = [c for c in ThemeStockDaily.__table__.constraints if isinstance(c, UniqueConstraint)]
        self.assertTrue(
            any(tuple(c.columns.keys()) == ("trade_date", "theme_name", "code") for c in constraints)
        )

    def test_market_review_daily_has_trade_date_uniqueness(self) -> None:
        constraints = [c for c in MarketReviewDaily.__table__.constraints if isinstance(c, UniqueConstraint)]
        self.assertTrue(any(tuple(c.columns.keys()) == ("trade_date",) for c in constraints))

    def test_market_emotion_daily_has_trade_date_uniqueness(self) -> None:
        constraints = [c for c in MarketEmotionDaily.__table__.constraints if isinstance(c, UniqueConstraint)]
        self.assertTrue(any(tuple(c.columns.keys()) == ("trade_date",) for c in constraints))

    def test_theme_emotion_daily_has_date_theme_uniqueness(self) -> None:
        constraints = [c for c in ThemeEmotionDaily.__table__.constraints if isinstance(c, UniqueConstraint)]
        self.assertTrue(any(tuple(c.columns.keys()) == ("trade_date", "theme_name") for c in constraints))


if __name__ == "__main__":
    unittest.main()
