"""Market breadth fetcher from THS quote center and Sohu history.

Purpose: Fetch A-share up/down/flat counts from q.10jqka.com.cn and
historical counts from q.stock.sohu.com.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from ashare_data.core.http_client import http_json
from ashare_data.fetchers.sohu_zdt import fetch_sohu_zdt_history
from ashare_data.fetchers.ths_cdp import fetch_indexflash_via_cdp

logger = logging.getLogger(__name__)

_THS_BREADTH_URL = "https://q.10jqka.com.cn/api.php?t=indexflash"
_THS_HEADERS = {
    "Referer": "https://q.10jqka.com.cn/",
}


@dataclass
class MarketBreadth:
    """Market breadth snapshot."""

    trade_date: str | None = None
    advance_count: int | None = None
    decline_count: int | None = None
    flat_count: int | None = None
    zdfb_bins: list[int] | None = None
    universe_total: int | None = None


def fetch_market_breadth() -> MarketBreadth:
    """Fetch current market breadth from THS quote center."""
    try:
        resp = http_json(url=_THS_BREADTH_URL, headers=_THS_HEADERS, timeout=10, retries=1)
    except Exception as exc:
        logger.warning("fetch_market_breadth 请求失败: %s", exc)
        return _parse_market_breadth_payload(_fetch_market_breadth_via_cdp())

    result = _parse_market_breadth_payload(resp)
    if result.advance_count is None or result.decline_count is None:
        return _parse_market_breadth_payload(_fetch_market_breadth_via_cdp())
    return result


def fetch_market_breadth_for_date(trade_date: str) -> MarketBreadth:
    """Fetch market breadth for a specific trade date.

    Historical dates prefer Sohu's SSR history table. If the date is not found,
    the function falls back to the current THS snapshot path.
    """
    normalized_date = _normalize_trade_date(trade_date)
    sohu_result = _fetch_market_breadth_from_sohu(normalized_date)
    if sohu_result is not None:
        return sohu_result
    result = fetch_market_breadth()
    result.trade_date = normalized_date
    return result


def _fetch_market_breadth_via_cdp() -> dict:
    """Use a real browser session as a fallback for protected THS endpoints."""
    try:
        return fetch_indexflash_via_cdp()
    except Exception as exc:
        logger.warning("fetch_market_breadth CDP fallback 失败: %s", exc)
        return {}


def _fetch_market_breadth_from_sohu(trade_date: str) -> MarketBreadth | None:
    """Load exact-date market breadth from Sohu history rows."""
    try:
        rows = fetch_sohu_zdt_history(anchor_date=date.fromisoformat(trade_date))
    except Exception as exc:
        logger.warning("fetch_market_breadth_from_sohu 失败: %s", exc)
        return None

    for row in rows:
        if row.get("trade_date") != trade_date:
            continue
        advance = sum(
            item.get("advance_count") or 0
            for item in (row.get("shanghai") or {}, row.get("shenzhen") or {}, row.get("beijing") or {})
        )
        flat = sum(
            item.get("flat_count") or 0
            for item in (row.get("shanghai") or {}, row.get("shenzhen") or {}, row.get("beijing") or {})
        )
        decline = sum(
            item.get("decline_count") or 0
            for item in (row.get("shanghai") or {}, row.get("shenzhen") or {}, row.get("beijing") or {})
        )
        universe_total = advance + flat + decline
        return MarketBreadth(
            trade_date=trade_date,
            advance_count=advance,
            decline_count=decline,
            flat_count=flat,
            zdfb_bins=None,
            universe_total=universe_total,
        )
    return None


def _parse_market_breadth_payload(resp: dict) -> MarketBreadth:
    """Parse THS indexflash payload into MarketBreadth."""
    data = resp.get("zdfb_data") or {}
    bins = data.get("zdfb") or []
    if not isinstance(bins, list):
        bins = []
    try:
        zdfb_bins = [int(item) for item in bins]
    except (TypeError, ValueError):
        zdfb_bins = []

    advance_count = data.get("znum")
    decline_count = data.get("dnum")
    try:
        advance = int(advance_count) if advance_count is not None else None
    except (TypeError, ValueError):
        advance = None
    try:
        decline = int(decline_count) if decline_count is not None else None
    except (TypeError, ValueError):
        decline = None

    universe_total = sum(zdfb_bins) if zdfb_bins else None
    flat_count = None
    if universe_total is not None and advance is not None and decline is not None:
        flat_count = max(universe_total - advance - decline, 0)

    return MarketBreadth(
        advance_count=advance,
        decline_count=decline,
        flat_count=flat_count,
        zdfb_bins=zdfb_bins,
        universe_total=universe_total,
    )


def _normalize_trade_date(trade_date: str) -> str:
    """Normalize trade date to YYYY-MM-DD."""
    text = (trade_date or "").strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return date.fromisoformat(text).isoformat()
