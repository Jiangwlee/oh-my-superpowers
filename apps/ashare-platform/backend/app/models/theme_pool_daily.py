"""Theme pool daily fact model.

Purpose: Persist one daily theme fact row per theme and trade date.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ThemePoolDaily(Base):
    """Daily theme pool fact."""

    __tablename__ = "theme_pool_daily"
    __table_args__ = (UniqueConstraint("trade_date", "theme_name", name="uq_theme_pool_daily_date_theme"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    theme_name: Mapped[str] = mapped_column(String(128), index=True)
    theme_rank: Mapped[int] = mapped_column(Integer, default=0)
    theme_strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    theme_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    theme_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    market_attitude: Mapped[str | None] = mapped_column(Text, nullable=True)
    core_stock_count: Mapped[int] = mapped_column(Integer, default=0)
    trend_stock_count: Mapped[int] = mapped_column(Integer, default=0)
    core_trend_stock_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    tags_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
