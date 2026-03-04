"""个股深研服务路由。

提供深研档案的 HTTP 接口：
  POST /ashare/deep-research/collect      — 采集深研数据
  GET  /ashare/deep-research/data         — 读取单只股票深研数据
  POST /ashare/deep-research/save-report  — 保存 LLM 报告
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from task_runner.models import TaskResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ashare/deep-research", tags=["deep-research"])


# ── Request models ────────────────────────────────────────────────────────


class CollectRequest(BaseModel):
    """深研采集请求。"""

    force: bool = Field(default=False, description="忽略 7 天时效限制")


class SaveReportRequest(BaseModel):
    """保存深研报告请求。"""

    code: str = Field(description="股票代码")
    report: str = Field(description="Markdown 报告内容")


# ── Helpers ───────────────────────────────────────────────────────────────


def _make_result(
    *, task_id: str, started_at: datetime, ok: bool,
    result: dict[str, Any] | None = None, error: str | None = None,
) -> TaskResult:
    finished_at = datetime.now(timezone.utc)
    return TaskResult(
        task_id=task_id,
        status="success" if ok else "failed",
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=round((finished_at - started_at).total_seconds(), 2),
        result=result,
        error=error,
    )


def _run_collect(req: CollectRequest) -> dict[str, Any]:
    from ashare_data.deep_research_collect import collect_deep_research

    return collect_deep_research(force=req.force)


def _run_load_data(code: str) -> dict[str, Any] | None:
    from ashare_data.core.config import ASHARE_HOME
    from ashare_data.deep_research import DeepResearchArchive

    archive = DeepResearchArchive(ASHARE_HOME / "deep_research")
    return archive.load_raw_data(code)


def _run_save_report(req: SaveReportRequest) -> dict[str, Any]:
    from ashare_data.core.config import ASHARE_HOME
    from ashare_data.deep_research import DeepResearchArchive

    archive = DeepResearchArchive(ASHARE_HOME / "deep_research")
    archive.save_report(req.code, req.report)
    return {
        "code": req.code,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.post("/collect")
async def collect(req: CollectRequest | None = None) -> TaskResult:
    """采集深研数据（趋势股 + watchlist，按时效过滤）。"""
    req = req or CollectRequest()
    task_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    try:
        result = await asyncio.to_thread(_run_collect, req)
        ok = bool(result.get("ok", False))
        error = result.get("error") if not ok else None
        return _make_result(
            task_id=task_id, started_at=started_at, ok=ok,
            result=result, error=str(error) if error else None,
        )
    except Exception as exc:
        logger.exception("deep-research/collect 异常")
        return _make_result(
            task_id=task_id, started_at=started_at, ok=False, error=str(exc),
        )


@router.get("/data")
async def get_data(code: str = Query(description="股票代码")) -> TaskResult:
    """读取单只股票的深研原始数据。"""
    task_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    try:
        result = await asyncio.to_thread(_run_load_data, code)
        if result is None:
            return _make_result(
                task_id=task_id, started_at=started_at, ok=False,
                error=f"not_found: {code}",
            )
        return _make_result(
            task_id=task_id, started_at=started_at, ok=True, result=result,
        )
    except Exception as exc:
        logger.exception("deep-research/data 异常")
        return _make_result(
            task_id=task_id, started_at=started_at, ok=False, error=str(exc),
        )


@router.post("/save-report")
async def save_report(req: SaveReportRequest) -> TaskResult:
    """保存 LLM 生成的深研报告。"""
    task_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    try:
        result = await asyncio.to_thread(_run_save_report, req)
        return _make_result(
            task_id=task_id, started_at=started_at, ok=True, result=result,
        )
    except Exception as exc:
        logger.exception("deep-research/save-report 异常")
        return _make_result(
            task_id=task_id, started_at=started_at, ok=False, error=str(exc),
        )
