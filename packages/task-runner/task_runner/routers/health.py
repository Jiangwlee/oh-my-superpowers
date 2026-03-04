"""健康检查端点。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """健康检查。"""
    return {"status": "ok"}
