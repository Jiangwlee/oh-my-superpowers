"""Read-only trade-date routes.

Purpose: Expose recent A-share trading dates for frontend defaults and
         date-window queries.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.runtime import today_cn
from app.core.trade_calendar import resolve_trade_dates
from app.schemas.api import LatestTradeDateResponse, RecentTradeDatesResponse

router = APIRouter(prefix="/trade-dates", tags=["trade-dates"])


@router.get("/latest", response_model=LatestTradeDateResponse)
def get_latest_trade_date() -> LatestTradeDateResponse:
    """Get the latest trading date on or before today."""
    trade_dates = resolve_trade_dates(end_date=today_cn(), days=1)
    if not trade_dates:
        raise HTTPException(status_code=503, detail="trade dates unavailable")
    return LatestTradeDateResponse(trade_date=trade_dates[-1])


@router.get("/recent", response_model=RecentTradeDatesResponse)
def get_recent_trade_dates(
    days: int = Query(default=30, ge=1, le=500),
) -> RecentTradeDatesResponse:
    """Get the most recent trading-date window ending on or before today."""
    trade_dates = resolve_trade_dates(end_date=today_cn(), days=days)
    if not trade_dates:
        raise HTTPException(status_code=503, detail="trade dates unavailable")
    return RecentTradeDatesResponse(days=days, trade_dates=trade_dates)
