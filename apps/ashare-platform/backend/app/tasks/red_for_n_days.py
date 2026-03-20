"""Task entrypoint for red-for-n-days screening."""

from __future__ import annotations

from typing import Any, Callable

from ashare_data.fetchers.trade_date import fetch_trade_date

from app.pipelines.red_for_n_days import build_red_for_n_days
from app.tasks._run_logging import run_logged


def _resolve_trade_date(
    trade_date: str | None,
    fetch_latest_trade_date: Callable[[], str],
) -> str:
    if trade_date:
        return trade_date
    latest = str(fetch_latest_trade_date()).strip()
    if len(latest) != 8 or not latest.isdigit():
        raise ValueError(f"Invalid latest trade date: {latest}")
    return f"{latest[:4]}-{latest[4:6]}-{latest[6:]}"


def run(
    *,
    trade_date: str | None = None,
    days: int = 7,
    top_n: int = 1000,
    fetch_candidates: Any | None = None,
    fetch_daily_kline: Any | None = None,
    fetch_latest_trade_date: Any | None = None,
) -> dict[str, Any]:
    """Run the red-for-n-days stock screen."""
    kwargs: dict[str, Any] = {
        "days": days,
        "top_n": top_n,
    }
    if fetch_candidates is not None:
        kwargs["fetch_candidates"] = fetch_candidates
    if fetch_daily_kline is not None:
        kwargs["fetch_daily_kline"] = fetch_daily_kline
    if fetch_latest_trade_date is not None:
        kwargs["fetch_latest_trade_date"] = fetch_latest_trade_date
    return run_logged(
        pipeline_name="red-for-n-days",
        trade_date=_resolve_trade_date(trade_date, fetch_latest_trade_date or fetch_trade_date),
        task_fn=build_red_for_n_days,
        **kwargs,
    )
