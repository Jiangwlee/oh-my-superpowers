"""Theme-stock daily fact model.

Purpose: Persist one daily fact row per theme-stock relation and trade date.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ThemeStockDaily(Base):
    """Daily theme-stock fact."""

    __tablename__ = "theme_stock_daily"
    __table_args__ = (
        UniqueConstraint("trade_date", "theme_name", "code", name="uq_theme_stock_daily_date_theme_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    theme_name: Mapped[str] = mapped_column(String(128), index=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(64))
    role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_core: Mapped[bool] = mapped_column(Boolean, default=False)
    rank_in_theme: Mapped[int] = mapped_column(Integer, default=0)
    trend_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    star_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    emotion_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
