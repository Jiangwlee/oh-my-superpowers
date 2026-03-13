"""Market review daily fact model.

Purpose: Persist one structured market review and markdown report per trade date.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MarketReviewDaily(Base):
    """Daily market review fact."""

    __tablename__ = "market_review_daily"
    __table_args__ = (UniqueConstraint("trade_date", name="uq_market_review_daily_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    regime: Mapped[str | None] = mapped_column(String(32), nullable=True)
    position_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    main_themes_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    emerging_themes_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    fading_themes_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_markdown: Mapped[str] = mapped_column(Text, default="")
    report_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
