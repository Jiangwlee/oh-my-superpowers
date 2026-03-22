"""Task entrypoint for one-command daily platform collection."""

from __future__ import annotations

from typing import Any

from app.core.runtime import today_cn
from app.tasks.build_emotion_facts import run as run_build_emotion_facts
from app.tasks.build_market_review import run as run_build_market_review
from app.tasks.build_theme_pool import run as run_build_theme_pool
from app.tasks.build_trend_pool import run as run_build_trend_pool
from app.tasks.collect_ephemeral import run as run_collect_ephemeral


def run(
    *,
    trade_date: str | None = None,
    with_ephemeral: bool = False,
    news_count: int = 20,
    taoguba_count: int = 20,
    scan_trends: bool = True,
    popularity_max: int = 1000,
    trend_max_rank: int = 1000,
) -> dict[str, Any]:
    """Run platform collection/build steps for one trading day."""
    resolved_trade_date = trade_date or today_cn()
    day_result: dict[str, Any] = {"trade_date": resolved_trade_date}
    if with_ephemeral:
        day_result["collect_ephemeral"] = run_collect_ephemeral(
            trade_date=resolved_trade_date,
            news_count=news_count,
            taoguba_count=taoguba_count,
            scan_trends=scan_trends,
            popularity_max=popularity_max,
        )
    day_result["build_emotion_facts"] = run_build_emotion_facts(trade_date=resolved_trade_date)
    day_result["build_trend_pool"] = run_build_trend_pool(trade_date=resolved_trade_date, max_rank=trend_max_rank)
    day_result["build_theme_pool"] = run_build_theme_pool(trade_date=resolved_trade_date)
    day_result["build_market_review"] = run_build_market_review(trade_date=resolved_trade_date)

    return {
        "trade_date": resolved_trade_date,
        "run": day_result,
    }
