"""Repository for theme-related daily facts.

Purpose: Persist and query retained daily theme and theme-stock rows.

Public API:
    replace_for_date(...) -> tuple[int, int]
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.theme_pool_daily import ThemePoolDaily
from app.models.theme_stock_daily import ThemeStockDaily


def replace_for_date(
    session: Session,
    trade_date: date,
    theme_rows: list[dict],
    stock_rows: list[dict],
) -> tuple[int, int]:
    """Replace all theme facts for a trade date."""
    session.execute(delete(ThemeStockDaily).where(ThemeStockDaily.trade_date == trade_date))
    session.execute(delete(ThemePoolDaily).where(ThemePoolDaily.trade_date == trade_date))

    theme_objects = [ThemePoolDaily(**row) for row in theme_rows]
    stock_objects = [ThemeStockDaily(**row) for row in stock_rows]
    session.add_all(theme_objects)
    session.add_all(stock_objects)
    session.commit()
    return len(theme_objects), len(stock_objects)
