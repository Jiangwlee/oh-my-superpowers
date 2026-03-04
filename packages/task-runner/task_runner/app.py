"""task-runner FastAPI 应用入口。

通用任务执行 HTTP 服务，为 n8n 等编排系统提供后端能力。
按服务分组注册路由：/health, /ashare/*。
"""

from __future__ import annotations

from fastapi import FastAPI

from task_runner.routers import ashare, deep_research, health

app = FastAPI(
    title="task-runner",
    description="通用任务执行 HTTP 服务",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(ashare.router)
app.include_router(deep_research.router)
