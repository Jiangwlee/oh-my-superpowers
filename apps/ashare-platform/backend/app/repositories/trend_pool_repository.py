"""Repository for trend pool daily facts.

Purpose: Persist and query retained trend-pool daily rows.

Public API:
    replace_for_date(...) -> int
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.trend_pool_daily import TrendPoolDaily


def replace_for_date(session: Session, trade_date: date, rows: list[dict]) -> int:
    """Replace all trend pool rows for a trade date."""
    session.execute(delete(TrendPoolDaily).where(TrendPoolDaily.trade_date == trade_date))
    objects = [TrendPoolDaily(**row) for row in rows]
    session.add_all(objects)
    session.commit()
    return len(objects)
