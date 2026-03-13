"""Task entrypoint for theme pool build."""

from __future__ import annotations

from typing import Any

from app.core.runtime import today_cn
from app.pipelines.build_theme_pool import build_theme_pool
from app.tasks._run_logging import run_logged


def run(*, trade_date: str | None = None) -> dict[str, Any]:
    """Build retained theme pool daily facts."""
    return run_logged(
        pipeline_name="build-theme-pool",
        trade_date=trade_date or today_cn(),
        task_fn=build_theme_pool,
    )
