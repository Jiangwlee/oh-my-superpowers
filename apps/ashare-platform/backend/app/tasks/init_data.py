"""Task entrypoint for historical data initialization."""

from __future__ import annotations

from typing import Any

from app.core.runtime import today_cn
from app.core.trade_calendar import resolve_trade_dates
from app.tasks.build_emotion_facts import run as run_build_emotion_facts


def run(
    *,
    trade_date: str | None = None,
    days: int = 30,
) -> dict[str, Any]:
    """Backfill retained data without running analysis pipelines."""
    resolved_end_date = trade_date or today_cn()
    trade_dates = resolve_trade_dates(end_date=resolved_end_date, days=days)
    runs: list[dict[str, Any]] = []

    for item in trade_dates:
        runs.append(
            {
                "trade_date": item,
                "build_emotion_facts": run_build_emotion_facts(trade_date=item),
            }
        )

    return {
        "end_date": resolved_end_date,
        "days": days,
        "trade_dates": trade_dates,
        "runs": runs,
    }
