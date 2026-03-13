"""Run model for backend task executions.

Purpose: Persist batch-level run metadata, status, and degradation context.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Run(Base):
    """Daily task run metadata."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    trade_date: Mapped[datetime.date] = mapped_column(Date, index=True)
    pipeline_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)
    degraded_reasons: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    source_summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
