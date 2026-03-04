"""A 股数据服务路由。

提供 ashare-data 的 HTTP 接口封装：
  POST /ashare/collect   — 数据采集
  POST /ashare/diagnose  — 决策诊断
  POST /ashare/watchlist — 自选股扫描
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from task_runner.models import TaskResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ashare", tags=["ashare"])


# ── Request models ────────────────────────────────────────────────────────


class CollectRequest(BaseModel):
    """数据采集请求参数。"""

    date: str | None = Field(default=None, description="目标日期 YYYY-MM-DD，默认今日")
    skip_collect: bool = Field(default=False, description="跳过数据采集")
    skip_filter: bool = Field(default=False, description="跳过 filter 转换")


class DiagnoseRequest(BaseModel):
    """决策诊断请求参数。"""

    today: str | None = Field(default=None, description="覆盖当前日期 YYYY-MM-DD")
    dry_run: bool = Field(default=False, description="只演算，不写回")


class WatchlistRequest(BaseModel):
    """自选股扫描请求参数。"""

    force: bool = Field(default=False, description="忽略交易时间限制")


# ── Helpers ───────────────────────────────────────────────────────────────


def _make_result(
    *, task_id: str, started_at: datetime, ok: bool,
    result: dict[str, Any] | None = None, error: str | None = None,
) -> TaskResult:
    """构造统一 TaskResult 响应。"""
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
    """调用 ashare_data.collect.run()，隔离层便于测试 mock。"""
    from ashare_data.collect import run

    return run(
        date_str=req.date,
        skip_collect=req.skip_collect,
        skip_filter=req.skip_filter,
    )


def _run_diagnose(req: DiagnoseRequest) -> dict[str, Any]:
    """调用 ashare_data.diagnose.process_diagnose()。"""
    from ashare_data.core.config import DECISION_LOG
    from ashare_data.diagnose import FEEDBACK_FILE, process_diagnose

    return process_diagnose(
        log_file=DECISION_LOG,
        feedback_file=FEEDBACK_FILE,
        dry_run=req.dry_run,
        today=req.today,
    )


def _run_watchlist(req: WatchlistRequest) -> dict[str, Any]:
    """调用 ashare_data.watchlist_monitor.scan_once()。"""
    from ashare_data.watchlist_monitor import scan_once

    return scan_once(force=req.force)


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.post("/collect")
async def collect(req: CollectRequest | None = None) -> TaskResult:
    """执行 A 股数据采集。"""
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
        logger.exception("ashare/collect 异常")
        return _make_result(
            task_id=task_id, started_at=started_at, ok=False, error=str(exc),
        )


@router.post("/diagnose")
async def diagnose(req: DiagnoseRequest | None = None) -> TaskResult:
    """执行决策诊断（T+1/T+5 回填）。"""
    req = req or DiagnoseRequest()
    task_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    try:
        result = await asyncio.to_thread(_run_diagnose, req)
        ok = bool(result.get("ok", False))
        error = result.get("error") if not ok else None
        return _make_result(
            task_id=task_id, started_at=started_at, ok=ok,
            result=result, error=str(error) if error else None,
        )
    except Exception as exc:
        logger.exception("ashare/diagnose 异常")
        return _make_result(
            task_id=task_id, started_at=started_at, ok=False, error=str(exc),
        )


@router.post("/watchlist")
async def watchlist(req: WatchlistRequest | None = None) -> TaskResult:
    """执行自选股单次扫描。"""
    req = req or WatchlistRequest()
    task_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    try:
        result = await asyncio.to_thread(_run_watchlist, req)
        ok = result.get("status") != "error"
        error = result.get("message") if not ok else None
        return _make_result(
            task_id=task_id, started_at=started_at, ok=ok,
            result=result, error=str(error) if error else None,
        )
    except Exception as exc:
        logger.exception("ashare/watchlist 异常")
        return _make_result(
            task_id=task_id, started_at=started_at, ok=False, error=str(exc),
        )
