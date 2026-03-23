"""FastAPI entrypoint for the A-share platform backend.

Purpose: Expose the backend application shell for future read-only APIs.

Public API:
    app -- FastAPI application instance
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes.emotion import router as emotion_router
from app.api.routes.health import router as health_router
from app.api.routes.kline import router as kline_router
from app.api.routes.market_reviews import router as market_reviews_router
from app.api.routes.runs import router as runs_router
from app.api.routes.trade_dates import router as trade_dates_router
from app.api.routes.theme_pool import router as theme_pool_router
from app.api.routes.trend_pool import router as trend_pool_router

app = FastAPI(
    title="A-Share Platform Backend",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(runs_router)
app.include_router(trade_dates_router)
app.include_router(trend_pool_router)
app.include_router(theme_pool_router)
app.include_router(kline_router)
app.include_router(market_reviews_router)
app.include_router(emotion_router)
