"""Task-level retained run logging.

Purpose: Persist batch run metadata for task entrypoints without coupling it
         to individual pipelines.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Callable

from app.core.runtime import build_run_id, today_cn
from app.db.session import init_db, open_session
from app.models.run import Run
from app.repositories.run_repository import save_run

TaskFn = Callable[..., dict[str, Any]]


def _extract_degradation(result: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any] | None]:
    collector_result = result.get("collector_result")
    if isinstance(collector_result, dict):
        sources = collector_result.get("sources")
        if isinstance(sources, dict):
            degraded_reasons = [
                f"{name}:{details.get('error') or details.get('status')}"
                for name, details in sources.items()
                if isinstance(details, dict) and details.get("status") != "ok"
            ]
            return bool(degraded_reasons), degraded_reasons, collector_result

    degraded = bool(result.get("degraded", False))
    degraded_reasons = result.get("degraded_reasons")
    if not isinstance(degraded_reasons, list):
        degraded_reasons = []
    source_summary = result.get("source_summary_json")
    return degraded, [str(reason) for reason in degraded_reasons], source_summary if isinstance(source_summary, dict) else None


def run_logged(
    *,
    pipeline_name: str,
    trade_date: str | None,
    task_fn: TaskFn,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run one task and persist its retained run record."""
    resolved_trade_date = trade_date or today_cn()
    started_at = datetime.now(timezone.utc)
    fallback_run_id = build_run_id(resolved_trade_date, pipeline_name)
    result: dict[str, Any] | None = None
    run = Run(
        run_id=fallback_run_id,
        trade_date=date.fromisoformat(resolved_trade_date),
        pipeline_name=pipeline_name,
        status="running",
        started_at=started_at,
    )

    init_db()
    try:
        result = task_fn(trade_date=resolved_trade_date, **kwargs)
        degraded, degraded_reasons, source_summary_json = _extract_degradation(result)
        run.run_id = str(result.get("run_id", fallback_run_id))
        run.status = "success"
        run.finished_at = datetime.now(timezone.utc)
        run.degraded = degraded
        run.degraded_reasons = degraded_reasons or None
        run.source_summary_json = source_summary_json
        with open_session() as session:
            save_run(session, run)
        return result
    except Exception as exc:
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        run.error_message = f"{type(exc).__name__}: {exc}"
        with open_session() as session:
            save_run(session, run)
        raise
