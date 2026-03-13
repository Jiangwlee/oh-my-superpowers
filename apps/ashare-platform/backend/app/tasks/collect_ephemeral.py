"""Task entrypoint for ephemeral data collection.

Purpose: Trigger the short-lived source collection pipeline.

Public API:
    run(...) -> dict
"""

from __future__ import annotations

from typing import Any

from app.pipelines.collect_ephemeral import collect_ephemeral
from app.tasks._run_logging import run_logged


def run(
    *,
    trade_date: str | None = None,
    news_count: int = 20,
    taoguba_count: int = 20,
    scan_trends: bool = True,
    popularity_max: int = 1000,
    collector: Any | None = None,
) -> dict[str, Any]:
    """Run ephemeral collection."""
    return run_logged(
        pipeline_name="collect-ephemeral",
        trade_date=trade_date,
        task_fn=collect_ephemeral,
        news_count=news_count,
        taoguba_count=taoguba_count,
        scan_trends=scan_trends,
        popularity_max=popularity_max,
        collector=collector,
    )
