"""Repository for market/theme emotion daily facts.

Purpose: Persist one market row and many theme rows for a trade date.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.market_emotion_daily import MarketEmotionDaily
from app.models.theme_emotion_daily import ThemeEmotionDaily


def replace_for_date(
    session: Session,
    trade_date: date,
    market_row: dict,
    theme_rows: list[dict],
) -> tuple[int, int]:
    """Replace market/theme emotion facts for one trade date."""
    session.execute(delete(ThemeEmotionDaily).where(ThemeEmotionDaily.trade_date == trade_date))
    session.execute(delete(MarketEmotionDaily).where(MarketEmotionDaily.trade_date == trade_date))
    session.add(MarketEmotionDaily(**market_row))
    session.add_all([ThemeEmotionDaily(**row) for row in theme_rows])
    session.commit()
    return 1, len(theme_rows)
