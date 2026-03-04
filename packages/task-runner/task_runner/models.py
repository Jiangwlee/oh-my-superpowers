"""通用响应模型。

所有 task-runner 端点共用的请求/响应模型定义。
TaskResult 是统一响应格式，预留 task_id 字段支持未来异步扩展。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskResult(BaseModel):
    """统一任务响应模型。"""

    task_id: str = Field(description="任务 ID（UUID）")
    status: str = Field(description="success | failed")
    started_at: datetime = Field(description="任务开始时间")
    finished_at: datetime = Field(description="任务结束时间")
    duration_seconds: float = Field(description="耗时（秒）")
    result: dict[str, Any] | str | None = Field(default=None, description="任务返回数据")
    error: str | None = Field(default=None, description="错误信息")
