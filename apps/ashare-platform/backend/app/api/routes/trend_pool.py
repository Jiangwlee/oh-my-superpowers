"""Read-only trend pool routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.db.session import init_db, open_session
from app.models.trend_pool_daily import TrendPoolDaily
from app.schemas.api import TrendPoolDailyResponse

router = APIRouter(prefix="/trend-pool", tags=["trend-pool"])


@router.get("/daily", response_model=list[TrendPoolDailyResponse])
def get_trend_pool_daily(
    trade_date: str = Query(...),
    min_star: int = Query(default=0, ge=0, le=5),
    is_uptrend: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    sort: str = Query(default="rank"),
) -> list[TrendPoolDailyResponse]:
    """Get daily trend pool facts."""
    init_db()
    with open_session() as session:
        query = session.query(TrendPoolDaily).filter(TrendPoolDaily.trade_date == trade_date)
        if min_star > 0:
            query = query.filter(TrendPoolDaily.star_rating >= min_star)
        if is_uptrend is not None:
            query = query.filter(TrendPoolDaily.is_uptrend == is_uptrend)
        if sort == "-score_total":
            query = query.order_by(TrendPoolDaily.score_total.desc())
        else:
            query = query.order_by(TrendPoolDaily.rank.asc())
        rows = query.limit(limit).all()
        return [
            TrendPoolDailyResponse(
                trade_date=row.trade_date.isoformat(),
                code=row.code,
                name=row.name,
                rank=row.rank,
                score_total=row.score_total,
                star_rating=row.star_rating,
                emotion_level=row.emotion_level,
                trade_signal=row.trade_signal,
                is_uptrend=row.is_uptrend,
            )
            for row in rows
        ]


@router.get("/stocks/{code}/history", response_model=list[TrendPoolDailyResponse])
def get_trend_stock_history(
    code: str,
    days: int = Query(default=20, ge=1, le=365),
) -> list[TrendPoolDailyResponse]:
    """Get recent daily trend facts for one stock."""
    init_db()
    with open_session() as session:
        rows = (
            session.query(TrendPoolDaily)
            .filter(TrendPoolDaily.code == code)
            .order_by(TrendPoolDaily.trade_date.desc())
            .limit(days)
            .all()
        )
        return [
            TrendPoolDailyResponse(
                trade_date=row.trade_date.isoformat(),
                code=row.code,
                name=row.name,
                rank=row.rank,
                score_total=row.score_total,
                star_rating=row.star_rating,
                emotion_level=row.emotion_level,
                trade_signal=row.trade_signal,
                is_uptrend=row.is_uptrend,
            )
            for row in rows
        ]
