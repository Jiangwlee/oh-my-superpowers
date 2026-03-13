"""Task entrypoint for trend pool build."""

from __future__ import annotations

from typing import Any

from app.core.runtime import today_cn
from app.pipelines.build_trend_pool import build_trend_pool
from app.tasks._run_logging import run_logged


def run(*, trade_date: str | None = None, max_rank: int = 1000) -> dict[str, Any]:
    """Build retained trend pool daily facts."""
    return run_logged(
        pipeline_name="build-trend-pool",
        trade_date=trade_date or today_cn(),
        task_fn=build_trend_pool,
        max_rank=max_rank,
    )
