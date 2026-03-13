"""Read-only run routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.db.session import init_db, open_session
from app.models.run import Run
from app.schemas.api import RunResponse

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=list[RunResponse])
def list_runs(
    trade_date: str | None = Query(default=None),
    pipeline_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
) -> list[RunResponse]:
    """List retained runs."""
    init_db()
    with open_session() as session:
        query = session.query(Run)
        if trade_date:
            query = query.filter(Run.trade_date == trade_date)
        if pipeline_name:
            query = query.filter(Run.pipeline_name == pipeline_name)
        if status:
            query = query.filter(Run.status == status)
        rows = query.order_by(Run.id.desc()).limit(limit).all()
        return [
            RunResponse(
                run_id=row.run_id,
                trade_date=row.trade_date.isoformat(),
                pipeline_name=row.pipeline_name,
                status=row.status,
                degraded=row.degraded,
            )
            for row in rows
        ]
