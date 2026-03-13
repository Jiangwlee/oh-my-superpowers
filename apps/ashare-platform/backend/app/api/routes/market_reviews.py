"""Read-only market review routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db.session import init_db, open_session
from app.models.market_review_daily import MarketReviewDaily
from app.schemas.api import MarketReviewDailyResponse

router = APIRouter(prefix="/market-reviews", tags=["market-reviews"])


@router.get("/daily/{trade_date}", response_model=MarketReviewDailyResponse)
def get_market_review_daily(trade_date: str) -> MarketReviewDailyResponse:
    """Get one daily market review."""
    init_db()
    with open_session() as session:
        row = (
            session.query(MarketReviewDaily)
            .filter(MarketReviewDaily.trade_date == trade_date)
            .one_or_none()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="market review not found")
        return MarketReviewDailyResponse(
            trade_date=row.trade_date.isoformat(),
            run_id=row.run_id,
            regime=row.regime,
            position_guidance=row.position_guidance,
            main_themes=list(row.main_themes_json or []),
            emerging_themes=list(row.emerging_themes_json or []),
            fading_themes=list(row.fading_themes_json or []),
            summary=row.summary,
            report_markdown=row.report_markdown,
        )
