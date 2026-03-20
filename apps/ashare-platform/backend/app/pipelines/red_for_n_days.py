"""Screen Eastmoney popularity names for consecutive red daily candles.

Purpose: Filter Eastmoney popularity-ranked stocks whose last N trading days
         all close at or above their open.

Public API:
    build_red_for_n_days(...) -> dict
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Any, Callable

from ashare_data.fetchers.trade_date import fetch_trade_date
from ashare_data.fetchers.trend_scanner import (
    fetch_eastmoney_popularity_rank,
    fetch_jrj_daily_kline,
)

from app.core.runtime import build_run_id, today_cn


def _normalize_trade_date(trade_date: str | None, fetch_latest_trade_date: Callable[[], str]) -> str:
    if trade_date:
        return trade_date
    latest = fetch_latest_trade_date()
    latest_text = str(latest).strip()
    if len(latest_text) != 8 or not latest_text.isdigit():
        raise ValueError(f"Invalid latest trade date: {latest_text}")
    return f"{latest_text[:4]}-{latest_text[4:6]}-{latest_text[6:]}"


def _resolve_range_num(trade_date: str, days: int) -> int:
    target = date.fromisoformat(trade_date)
    current = date.fromisoformat(today_cn())
    delta_days = max(0, (current - target).days)
    return min(1000, max(days + 15, delta_days + days + 15))


def _serialize_bar(bar: dict[str, Any]) -> dict[str, Any]:
    raw_time = str(int(bar["time"]))
    return {
        "date": f"{raw_time[:4]}-{raw_time[4:6]}-{raw_time[6:]}",
        "open": float(bar["open"]),
        "close": float(bar["close"]),
    }


def _calc_gain_n_days_pct(bars: list[dict[str, Any]]) -> float:
    first_open = float(bars[0]["open"])
    last_close = float(bars[-1]["close"])
    if first_open <= 0:
        return 0.0
    return round((last_close / first_open - 1.0) * 100.0, 2)


def _select_recent_bars(kline: list[dict[str, Any]], trade_date: str, days: int) -> list[dict[str, Any]]:
    cutoff = int(trade_date.replace("-", ""))
    valid = [
        bar
        for bar in kline
        if int(bar.get("time", 0) or 0) <= cutoff
        and bar.get("open") is not None
        and bar.get("close") is not None
    ]
    return valid[-days:] if len(valid) >= days else []


def build_red_for_n_days(
    *,
    trade_date: str | None = None,
    days: int = 7,
    top_n: int = 1000,
    fetch_candidates: Callable[..., list[dict[str, Any]]] = fetch_eastmoney_popularity_rank,
    fetch_daily_kline: Callable[..., list[dict[str, Any]]] = fetch_jrj_daily_kline,
    fetch_latest_trade_date: Callable[[], str] = fetch_trade_date,
) -> dict[str, Any]:
    """Filter popularity-ranked stocks by consecutive red daily candles."""
    if days <= 0:
        raise ValueError("days must be positive")
    if top_n <= 0:
        raise ValueError("top_n must be positive")

    resolved_trade_date = _normalize_trade_date(trade_date, fetch_latest_trade_date)
    resolved_top_n = min(4000, top_n)
    range_num = _resolve_range_num(resolved_trade_date, days)
    run_id = build_run_id(resolved_trade_date, "red-for-n-days")
    candidates = fetch_candidates(top_n=resolved_top_n)

    matches: list[dict[str, Any]] = []
    insufficient_count = 0

    def _screen_candidate(candidate: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
        bars = _select_recent_bars(
            fetch_daily_kline(str(candidate.get("code", "")), range_num=range_num),
            resolved_trade_date,
            days,
        )
        if len(bars) < days:
            return None, True
        if not all(float(bar["close"]) >= float(bar["open"]) for bar in bars):
            return None, False
        return (
            {
                "code": str(candidate.get("code", "")),
                "sc": str(candidate.get("sc", "")),
                "name": str(candidate.get("name", "")),
                "rank": int(candidate.get("rank", 0) or 0),
                "all_red": True,
                "gain_n_days_pct": _calc_gain_n_days_pct(bars),
                "bars": [_serialize_bar(bar) for bar in bars],
            },
            False,
        )

    with ThreadPoolExecutor(max_workers=min(16, len(candidates) or 1)) as pool:
        futures = [pool.submit(_screen_candidate, candidate) for candidate in candidates]
        for future in as_completed(futures):
            match, insufficient = future.result()
            if match is None:
                if insufficient:
                    insufficient_count += 1
                continue
            matches.append(match)

    matches.sort(key=lambda item: (int(item["rank"]), str(item["code"])))
    return {
        "run_id": run_id,
        "trade_date": resolved_trade_date,
        "days": days,
        "top_n": resolved_top_n,
        "candidate_count": len(candidates),
        "matched_count": len(matches),
        "insufficient_kline_count": insufficient_count,
        "matches": matches,
    }
