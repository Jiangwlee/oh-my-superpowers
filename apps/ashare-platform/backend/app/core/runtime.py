"""Runtime helpers for backend tasks.

Purpose: Provide consistent identifiers and trade-date helpers for task runs.

Public API:
    build_run_id(trade_date, pipeline_name) -> str
    today_cn() -> str
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

_CN_TZ = timezone(timedelta(hours=8))


def today_cn() -> str:
    """Return current China trade date in YYYY-MM-DD format."""
    return datetime.now(_CN_TZ).strftime("%Y-%m-%d")


def build_run_id(trade_date: str, pipeline_name: str) -> str:
    """Build a simple run identifier with date, pipeline, and current time."""
    stamp = datetime.now(_CN_TZ).strftime("%H%M%S")
    normalized = pipeline_name.strip().replace("_", "-")
    return f"{trade_date.replace('-', '')}-{normalized}-{stamp}"
