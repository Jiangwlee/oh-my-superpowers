"""Repository for market review daily facts.

Purpose: Persist and query retained daily market review rows.

Public API:
    replace_for_date(...) -> bool
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.market_review_daily import MarketReviewDaily


def replace_for_date(session: Session, trade_date: date, row: dict) -> bool:
    """Replace one market review for a trade date."""
    session.execute(delete(MarketReviewDaily).where(MarketReviewDaily.trade_date == trade_date))
    session.add(MarketReviewDaily(**row))
    session.commit()
    return True
