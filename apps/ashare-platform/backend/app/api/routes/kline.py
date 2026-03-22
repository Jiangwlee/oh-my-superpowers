"""Read-only daily K-line routes.

Purpose: Expose lightweight real-time daily OHLCV bars from the upstream
         JRJ data source without persisting them locally.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ashare_data.fetchers.trend_scanner import fetch_jrj_daily_kline

from app.schemas.api import KlineDailyResponse

router = APIRouter(prefix="/kline", tags=["kline"])


def _to_daily_kline_response(bar: dict[str, Any]) -> KlineDailyResponse:
    raw_time = str(int(bar["time"]))
    amount = float(bar.get("amount") or 0.0)
    change_pct = bar.get("change_pct")
    return KlineDailyResponse(
        date=f"{raw_time[:4]}-{raw_time[4:6]}-{raw_time[6:]}",
        open=float(bar["open"]),
        high=float(bar["high"]),
        low=float(bar["low"]),
        close=float(bar["close"]),
        volume=int(round(float(bar.get("volume") or 0.0))),
        amount=round(amount / 100000000.0, 2),
        change_pct=float(change_pct) if change_pct is not None else None,
    )


@router.get("/daily/{code}", response_model=list[KlineDailyResponse])
def get_daily_kline(
    code: str,
    days: int = Query(default=20, ge=1, le=120),
) -> list[KlineDailyResponse]:
    """Get recent daily OHLCV bars for one stock."""
    bars = fetch_jrj_daily_kline(code, range_num=days)
    valid_bars = [
        bar
        for bar in bars
        if bar.get("time") is not None
        and bar.get("open") is not None
        and bar.get("high") is not None
        and bar.get("low") is not None
        and bar.get("close") is not None
    ]
    return [_to_daily_kline_response(bar) for bar in valid_bars[-days:]]
