"""Task entrypoint for market review build."""

from __future__ import annotations

from typing import Any

from app.core.runtime import today_cn
from app.pipelines.build_market_review import build_market_review
from app.tasks._run_logging import run_logged


def run(*, trade_date: str | None = None) -> dict[str, Any]:
    """Build retained market review daily report."""
    return run_logged(
        pipeline_name="build-market-review",
        trade_date=trade_date or today_cn(),
        task_fn=build_market_review,
    )
