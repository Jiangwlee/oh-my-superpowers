"""Ephemeral collection pipeline.

Purpose: Collect short-lived source data into the backend ephemeral file layer.

Public API:
    collect_ephemeral(...) -> dict
"""

from __future__ import annotations

from typing import Any, Callable

from app.core.config import get_settings
from app.core.runtime import build_run_id, today_cn


def collect_ephemeral(
    *,
    trade_date: str | None = None,
    news_count: int = 20,
    taoguba_count: int = 20,
    scan_trends: bool = True,
    popularity_max: int = 1000,
    collector: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Collect ephemeral source data and return normalized run metadata."""
    resolved_date = trade_date or today_cn()
    settings = get_settings()
    data_dir = settings.ephemeral_dir / resolved_date
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    if collector is None:
        from ashare_data.collect_sentiment import collect as collect_sentiment

        collector = collect_sentiment

    result = collector(
        str(raw_dir),
        news_count=news_count,
        taoguba_count=taoguba_count,
        scan_trends=scan_trends,
        popularity_max=popularity_max,
    )
    run_id = build_run_id(resolved_date, "collect-ephemeral")
    return {
        "run_id": run_id,
        "trade_date": resolved_date,
        "data_dir": str(data_dir),
        "raw_dir": str(raw_dir),
        "collector_result": result,
    }
