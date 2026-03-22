"""Trade-date helpers backed by THS limit-up calendar API.

Purpose: Resolve recent trading dates for batch task execution.
"""

from __future__ import annotations

import logging
from datetime import date

from ashare_data.core.http_client import http_json

logger = logging.getLogger(__name__)

_TRADE_DAY_URL = "https://data.10jqka.com.cn/dataapi/limit_up/trade_day"
_TRADE_DAY_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html#/",
}


def _normalize_trade_date(trade_date: str) -> tuple[str, str]:
    resolved = date.fromisoformat(trade_date)
    return resolved.isoformat(), resolved.strftime("%Y%m%d")


def resolve_trade_dates(*, end_date: str, days: int) -> list[str]:
    """Resolve a recent trading-date window ending at or before end_date.

    Args:
        end_date: End date in YYYY-MM-DD format.
        days: Number of trading dates to return.

    Returns:
        Trading dates in ascending YYYY-MM-DD order.
    """
    if days < 1:
        raise ValueError("days must be >= 1")

    end_iso, end_compact = _normalize_trade_date(end_date)
    prev = max(days + 5, days * 3)
    payload = http_json(
        url=f"{_TRADE_DAY_URL}?date={end_compact}&stock=stock&next=1&prev={prev}",
        headers=_TRADE_DAY_HEADERS,
        timeout=10,
        retries=1,
    )
    data = payload.get("data") or {}
    prev_dates = [str(item) for item in (data.get("prev_dates") or []) if item]
    trade_day = bool(data.get("trade_day"))

    dates = prev_dates
    if trade_day:
        dates = [*prev_dates, end_compact]
    if not dates:
        logger.warning("resolve_trade_dates: no trading dates returned for %s", end_iso)
        return []
    window = dates[-days:]
    return [f"{item[:4]}-{item[4:6]}-{item[6:]}" for item in window]
