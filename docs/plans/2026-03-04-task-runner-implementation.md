# task-runner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a FastAPI HTTP service (task-runner) in a Docker container that exposes ashare-data functionality as REST endpoints, callable by n8n.

**Architecture:** task-runner is a FastAPI app in `packages/task-runner/`, deployed as a Docker container on `infra_net`. It imports ashare-data (installed via `pip install -e`) and wraps its core functions as HTTP endpoints. n8n calls `http://task-runner:8000/ashare/*`.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, Docker, ashare-data (existing package)

**Design Doc:** `docs/plans/2026-03-04-task-runner-design.md`

---

## Phase 1: ashare-data 改造

Make ashare-data's core functions return structured `dict` results suitable for HTTP responses.

### Task 1: collect.py — 改造 `run()` 返回 dict

**Current state:** `run()` returns `bool`. Need it to return a structured `dict`.

**Files:**
- Modify: `packages/ashare-data/ashare_data/collect.py`
- Test: `packages/ashare-data/tests/test_collect_run.py`

**Step 1: Write the failing test**

Create `packages/ashare-data/tests/test_collect_run.py`:

```python
"""Tests for collect.run() return value structure."""

from __future__ import annotations

import unittest
from unittest.mock import patch


class TestCollectRunReturnType(unittest.TestCase):
    """Verify run() returns a dict with expected keys."""

    @patch("ashare_data.collect.collect")
    @patch("ashare_data.collect.filter_all")
    @patch("ashare_data.collect.run_sentiment_preprocess")
    @patch("ashare_data.collect.ensure_dirs")
    def test_run_returns_dict_on_success(
        self, mock_dirs, mock_sentiment, mock_filter, mock_collect
    ):
        mock_collect.return_value = {
            "ok_count": 5, "error_count": 0, "total_elapsed_sec": 10.0,
            "sources": {},
        }
        mock_filter.return_value = {
            "converted": 5, "skipped": 0, "errors": 0, "total_size_kb": 100.0,
        }
        mock_sentiment.return_value = {"ok": True, "elapsed_sec": 5.0, "news": {}, "social": {}}

        from ashare_data.collect import run

        result = run(date_str="2026-01-01")
        self.assertIsInstance(result, dict)
        self.assertTrue(result["ok"])
        self.assertIn("data_dir", result)
        self.assertIn("collect", result)
        self.assertIn("filter", result)

    @patch("ashare_data.collect.collect")
    @patch("ashare_data.collect.ensure_dirs")
    def test_run_returns_dict_on_failure(self, mock_dirs, mock_collect):
        mock_collect.side_effect = RuntimeError("network error")

        from ashare_data.collect import run

        result = run(date_str="2026-01-01", run_sentiment=False)
        self.assertIsInstance(result, dict)
        self.assertFalse(result["ok"])
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `cd /home/bruce/Projects/oh-my-superpowers && .venv/bin/python -m pytest packages/ashare-data/tests/test_collect_run.py -v`

Expected: FAIL — `run()` returns `bool`, not `dict`.

**Step 3: Modify `collect.py` — change `run()` to return dict**

In `packages/ashare-data/ashare_data/collect.py`, change the `run()` function:

- Change return type annotation from `bool` to `dict[str, Any]`
- Build a result dict accumulating info from each phase
- On `RuntimeError` in collect phase, return `{"ok": False, "error": str(exc), ...}`
- On success, return `{"ok": True, "data_dir": str(data_dir), "collect": {...}, "filter": {...}, "sentiment": {...}}`
- Update docstring accordingly

Change `main()` to use the new return:

```python
def main() -> None:
    # ... (existing argparse unchanged) ...
    result = run(...)
    if result.get("collect") or result.get("filter") or result.get("sentiment"):
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    sys.exit(0 if result["ok"] else 1)
```

Add `import json` if not already present (it is not — add it to the imports).

**Step 4: Run test to verify it passes**

Run: `cd /home/bruce/Projects/oh-my-superpowers && .venv/bin/python -m pytest packages/ashare-data/tests/test_collect_run.py -v`

Expected: PASS

**Step 5: Run existing tests to verify no regressions**

Run: `cd /home/bruce/Projects/oh-my-superpowers && .venv/bin/python -m pytest packages/ashare-data/tests/ -v --timeout=30 2>&1 | tail -30`

Expected: No new failures (existing tests may have network-dependent skips).

**Step 6: Commit**

```bash
git add packages/ashare-data/ashare_data/collect.py packages/ashare-data/tests/test_collect_run.py
git commit -m "refactor(ashare-data): collect.run() returns dict instead of bool"
```

---

### Task 2: watchlist_monitor.py — 公开 `_scan_once()`

**Current state:** `_scan_once()` is private (prefixed `_`). It already returns a `dict`. Just need to make it public.

**Files:**
- Modify: `packages/ashare-data/ashare_data/watchlist_monitor.py`
- Test: `packages/ashare-data/tests/test_watchlist_scan_once.py`

**Step 1: Write the failing test**

Create `packages/ashare-data/tests/test_watchlist_scan_once.py`:

```python
"""Tests for watchlist_monitor.scan_once() public API."""

from __future__ import annotations

import unittest


class TestScanOncePublicAPI(unittest.TestCase):
    """Verify scan_once is importable and returns expected structure."""

    def test_scan_once_is_importable(self):
        from ashare_data.watchlist_monitor import scan_once
        self.assertTrue(callable(scan_once))

    def test_scan_once_outside_trading_hours(self):
        """Outside trading hours, scan_once returns skipped status."""
        from ashare_data.watchlist_monitor import scan_once
        result = scan_once(force=False)
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)
        # Outside trading hours it should be "skipped" (unless force=True)
        # Either way the structure should have these keys
        self.assertIn("market", result)
        self.assertIn("signals", result)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `cd /home/bruce/Projects/oh-my-superpowers && .venv/bin/python -m pytest packages/ashare-data/tests/test_watchlist_scan_once.py::TestScanOncePublicAPI::test_scan_once_is_importable -v`

Expected: FAIL — `ImportError: cannot import name 'scan_once'`

**Step 3: Rename `_scan_once` → `scan_once` in watchlist_monitor.py**

In `packages/ashare-data/ashare_data/watchlist_monitor.py`:

1. Rename function `_scan_once` to `scan_once`
2. Update all internal references (there are 3 calls to `_scan_once` in `main()`):
   - Line in `if args.once:` block: `snapshot = _scan_once(force=args.force)` → `snapshot = scan_once(force=args.force)`
   - Line in `while True:` block: `snapshot = _scan_once(force=args.force)` → `snapshot = scan_once(force=args.force)`
3. Update the module docstring's Public API section: `_scan_once()` → `scan_once()`

**Step 4: Run test to verify it passes**

Run: `cd /home/bruce/Projects/oh-my-superpowers && .venv/bin/python -m pytest packages/ashare-data/tests/test_watchlist_scan_once.py -v`

Expected: PASS

**Step 5: Run existing watchlist tests for regressions**

Run: `cd /home/bruce/Projects/oh-my-superpowers && .venv/bin/python -m pytest packages/ashare-data/tests/test_watchlist_monitor.py -v --timeout=30 2>&1 | tail -20`

Expected: No new failures.

**Step 6: Commit**

```bash
git add packages/ashare-data/ashare_data/watchlist_monitor.py packages/ashare-data/tests/test_watchlist_scan_once.py
git commit -m "refactor(ashare-data): make scan_once() public API"
```

---

### Task 3: diagnose.py — 验证已有 public API

**Current state:** `process_diagnose()` is already public, returns `dict`. Just verify it's clean.

**Files:**
- Test: `packages/ashare-data/tests/test_diagnose.py` (existing)

**Step 1: Run existing diagnose tests**

Run: `cd /home/bruce/Projects/oh-my-superpowers && .venv/bin/python -m pytest packages/ashare-data/tests/test_diagnose.py -v --timeout=30`

Expected: PASS (existing tests confirm API works).

**Step 2: Commit (no-op if tests pass)**

No changes needed. Move on.

---

## Phase 2: task-runner 骨架

### Task 4: 创建 packages/task-runner 项目结构

**Files:**
- Create: `packages/task-runner/pyproject.toml`
- Create: `packages/task-runner/task_runner/__init__.py`
- Create: `packages/task-runner/task_runner/models.py`
- Create: `packages/task-runner/task_runner/app.py`
- Create: `packages/task-runner/task_runner/routers/__init__.py`
- Create: `packages/task-runner/task_runner/routers/health.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "task-runner"
version = "0.1.0"
description = "通用任务执行 HTTP 服务，为 n8n 等编排系统提供后端能力"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "ashare-data",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["task_runner*"]
```

**Step 2: Create models.py**

```python
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
    result: dict[str, Any] | None = Field(default=None, description="任务返回数据")
    error: str | None = Field(default=None, description="错误信息")
```

**Step 3: Create health router**

```python
"""健康检查端点。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """健康检查。"""
    return {"status": "ok"}
```

**Step 4: Create app.py**

```python
"""task-runner FastAPI 应用入口。

通用任务执行 HTTP 服务，为 n8n 等编排系统提供后端能力。
按服务分组注册路由：/health, /ashare/*。
"""

from __future__ import annotations

from fastapi import FastAPI

from task_runner.routers import health

app = FastAPI(
    title="task-runner",
    description="通用任务执行 HTTP 服务",
    version="0.1.0",
)

app.include_router(health.router)
```

**Step 5: Create `__init__.py` files**

`packages/task-runner/task_runner/__init__.py`:
```python
```

`packages/task-runner/task_runner/routers/__init__.py`:
```python
```

**Step 6: Write test for health endpoint**

Create `packages/task-runner/tests/__init__.py` (empty) and `packages/task-runner/tests/test_health.py`:

```python
"""Tests for health endpoint."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from task_runner.app import app


class TestHealth(unittest.TestCase):
    """Health endpoint tests."""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_returns_ok(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
```

**Step 7: Install task-runner in dev mode and run test**

Run:
```bash
cd /home/bruce/Projects/oh-my-superpowers
.venv/bin/pip install -e packages/task-runner
.venv/bin/python -m pytest packages/task-runner/tests/test_health.py -v
```

Expected: PASS

**Step 8: Commit**

```bash
git add packages/task-runner/
git commit -m "feat(task-runner): scaffold FastAPI app with health endpoint"
```

---

### Task 5: ashare router — /ashare/collect

**Files:**
- Create: `packages/task-runner/task_runner/routers/ashare.py`
- Modify: `packages/task-runner/task_runner/app.py` (register router)
- Test: `packages/task-runner/tests/test_ashare_collect.py`

**Step 1: Write the failing test**

Create `packages/task-runner/tests/test_ashare_collect.py`:

```python
"""Tests for /ashare/collect endpoint."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from task_runner.app import app


class TestAshareCollect(unittest.TestCase):
    """POST /ashare/collect tests."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("task_runner.routers.ashare._run_collect")
    def test_collect_success(self, mock_run):
        mock_run.return_value = {
            "ok": True,
            "data_dir": "/tmp/test/2026-01-01",
            "collect": {"ok_count": 5, "error_count": 0},
            "filter": {"converted": 5},
        }
        resp = self.client.post("/ashare/collect", json={"date": "2026-01-01"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "success")
        self.assertIsNotNone(body["task_id"])
        self.assertIsNotNone(body["result"])

    @patch("task_runner.routers.ashare._run_collect")
    def test_collect_failure(self, mock_run):
        mock_run.return_value = {
            "ok": False,
            "error": "network timeout",
        }
        resp = self.client.post("/ashare/collect", json={})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")
        self.assertIsNotNone(body["error"])

    @patch("task_runner.routers.ashare._run_collect")
    def test_collect_exception(self, mock_run):
        mock_run.side_effect = Exception("unexpected crash")
        resp = self.client.post("/ashare/collect", json={})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")
        self.assertIn("unexpected crash", body["error"])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `cd /home/bruce/Projects/oh-my-superpowers && .venv/bin/python -m pytest packages/task-runner/tests/test_ashare_collect.py -v`

Expected: FAIL — route doesn't exist yet.

**Step 3: Create ashare router**

Create `packages/task-runner/task_runner/routers/ashare.py`:

```python
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
```

**Step 4: Register ashare router in app.py**

Modify `packages/task-runner/task_runner/app.py` — add:

```python
from task_runner.routers import health, ashare

# ... after app creation ...
app.include_router(health.router)
app.include_router(ashare.router)
```

**Step 5: Run test to verify it passes**

Run: `cd /home/bruce/Projects/oh-my-superpowers && .venv/bin/python -m pytest packages/task-runner/tests/test_ashare_collect.py -v`

Expected: PASS

**Step 6: Commit**

```bash
git add packages/task-runner/
git commit -m "feat(task-runner): add /ashare/collect, /ashare/diagnose, /ashare/watchlist endpoints"
```

---

### Task 6: ashare router — /ashare/diagnose 和 /ashare/watchlist 测试

**Files:**
- Test: `packages/task-runner/tests/test_ashare_diagnose.py`
- Test: `packages/task-runner/tests/test_ashare_watchlist.py`

**Step 1: Write diagnose test**

Create `packages/task-runner/tests/test_ashare_diagnose.py`:

```python
"""Tests for /ashare/diagnose endpoint."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from task_runner.app import app


class TestAshareDiagnose(unittest.TestCase):
    """POST /ashare/diagnose tests."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("task_runner.routers.ashare._run_diagnose")
    def test_diagnose_success(self, mock_run):
        mock_run.return_value = {"ok": True, "updated_t1": 2, "updated_t5": 1, "dry_run": False}
        resp = self.client.post("/ashare/diagnose", json={"dry_run": True})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "success")

    @patch("task_runner.routers.ashare._run_diagnose")
    def test_diagnose_exception(self, mock_run):
        mock_run.side_effect = Exception("file not found")
        resp = self.client.post("/ashare/diagnose", json={})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")
        self.assertIn("file not found", body["error"])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Write watchlist test**

Create `packages/task-runner/tests/test_ashare_watchlist.py`:

```python
"""Tests for /ashare/watchlist endpoint."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from task_runner.app import app


class TestAshareWatchlist(unittest.TestCase):
    """POST /ashare/watchlist tests."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("task_runner.routers.ashare._run_watchlist")
    def test_watchlist_success(self, mock_run):
        mock_run.return_value = {
            "status": "ok", "message": "", "market": {}, "signals": [],
        }
        resp = self.client.post("/ashare/watchlist", json={"force": True})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "success")

    @patch("task_runner.routers.ashare._run_watchlist")
    def test_watchlist_skipped(self, mock_run):
        mock_run.return_value = {
            "status": "skipped", "message": "非交易时段", "market": {}, "signals": [],
        }
        resp = self.client.post("/ashare/watchlist", json={})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # skipped is not error, so status = success
        self.assertEqual(body["status"], "success")

    @patch("task_runner.routers.ashare._run_watchlist")
    def test_watchlist_exception(self, mock_run):
        mock_run.side_effect = Exception("crash")
        resp = self.client.post("/ashare/watchlist", json={})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")


if __name__ == "__main__":
    unittest.main()
```

**Step 3: Run all task-runner tests**

Run: `cd /home/bruce/Projects/oh-my-superpowers && .venv/bin/python -m pytest packages/task-runner/tests/ -v`

Expected: All PASS

**Step 4: Commit**

```bash
git add packages/task-runner/tests/
git commit -m "test(task-runner): add diagnose and watchlist endpoint tests"
```

---

## Phase 3: Docker 部署

### Task 7: 创建 Dockerfile 和 docker-compose.yml

**Files:**
- Create: `packages/task-runner/Dockerfile`
- Create: `~/Dockers/TaskRunner/docker-compose.yml`

**Step 1: Create Dockerfile**

Create `packages/task-runner/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装基础依赖
RUN pip install --no-cache-dir fastapi 'uvicorn[standard]'

# 挂载点（通过 docker-compose volumes）:
#   /install/ashare-data   → packages/ashare-data 源码
#   /install/task-runner   → packages/task-runner 源码
#   /home/bruce/.ashare-assistant → 数据目录（与宿主机相同路径）

# entrypoint 脚本：安装挂载的包后启动 uvicorn
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
```

**Step 2: Create entrypoint.sh**

Create `packages/task-runner/entrypoint.sh`:

```bash
#!/bin/sh
set -e

echo "=== task-runner entrypoint ==="

# 安装挂载的 packages（-e 模式，代码变更后重启即生效）
if [ -d /install/ashare-data ]; then
    pip install --no-cache-dir -e /install/ashare-data 2>&1 | tail -1
fi
pip install --no-cache-dir -e /install/task-runner 2>&1 | tail -1

echo "=== 启动 uvicorn ==="
exec uvicorn task_runner.app:app --host 0.0.0.0 --port 8000
```

**Step 3: Create docker-compose.yml**

Create `~/Dockers/TaskRunner/docker-compose.yml`:

```yaml
services:
  task-runner:
    build:
      context: /home/bruce/Projects/oh-my-superpowers/packages/task-runner
      dockerfile: Dockerfile
    container_name: task_runner
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - /home/bruce/Projects/oh-my-superpowers/packages/ashare-data:/install/ashare-data:ro
      - /home/bruce/Projects/oh-my-superpowers/packages/task-runner:/install/task-runner:ro
      - /home/bruce/.ashare-assistant:/home/bruce/.ashare-assistant
    networks:
      - infra_net

networks:
  infra_net:
    external: true
```

**Step 4: Build and start container**

```bash
cd ~/Dockers/TaskRunner
docker compose up -d --build
```

**Step 5: Verify container is running**

```bash
docker ps --filter name=task_runner
docker logs task_runner --tail 20
```

Expected: Container running, uvicorn started on port 8000.

**Step 6: Test from n8n container**

```bash
docker exec n8n_app wget -qO- http://task-runner:8000/health
```

Expected: `{"status":"ok"}`

**Step 7: Commit**

```bash
cd /home/bruce/Projects/oh-my-superpowers
git add packages/task-runner/Dockerfile packages/task-runner/entrypoint.sh
git commit -m "feat(task-runner): add Dockerfile and entrypoint"

cd ~/Dockers/TaskRunner
git add docker-compose.yml
git commit -m "feat(task-runner): add docker-compose config"
```

---

### Task 8: 更新 Dockers 端口映射文档

**Files:**
- Modify: `~/Dockers/AGENTS.md`

**Step 1: Add task-runner to port mapping table**

In `~/Dockers/AGENTS.md`, add a row to the Port Mapping Registry table:

```
| task-runner | (none) | 8000 | Task Runner (infra_net only) |
```

**Step 2: Add task-runner to Docker Usage section**

Add:
```markdown
```bash
cd TaskRunner
docker compose up -d
```

**Step 3: Commit**

```bash
cd ~/Dockers
git add AGENTS.md
git commit -m "docs: add task-runner to port mapping and usage"
```

---

## Phase 4: 端到端验证

### Task 9: 手动端到端测试

No code changes. Verification only.

**Step 1: Test /ashare/collect from n8n container (dry run)**

```bash
docker exec n8n_app wget -qO- --post-data='{"date":"2026-03-04","skip_collect":true,"skip_filter":true}' \
  --header='Content-Type: application/json' \
  http://task-runner:8000/ashare/collect
```

Expected: JSON response with `task_id`, `status`, `duration_seconds`.

**Step 2: Test /ashare/diagnose from n8n container**

```bash
docker exec n8n_app wget -qO- --post-data='{"dry_run":true}' \
  --header='Content-Type: application/json' \
  http://task-runner:8000/ashare/diagnose
```

Expected: JSON response with diagnose result.

**Step 3: Test /ashare/watchlist from n8n container**

```bash
docker exec n8n_app wget -qO- --post-data='{"force":false}' \
  --header='Content-Type: application/json' \
  http://task-runner:8000/ashare/watchlist
```

Expected: JSON response (likely "skipped" outside trading hours).

**Step 4: Check OpenAPI docs accessible**

```bash
docker exec n8n_app wget -qO- http://task-runner:8000/openapi.json | head -20
```

Expected: OpenAPI spec JSON with all endpoints listed.

---

## Summary

| Phase | Task | Description | Est. Time |
|-------|------|-------------|-----------|
| 1 | Task 1 | collect.py `run()` returns dict | 15 min |
| 1 | Task 2 | watchlist_monitor.py public `scan_once()` | 10 min |
| 1 | Task 3 | diagnose.py — verify existing API | 5 min |
| 2 | Task 4 | task-runner project scaffold + health endpoint | 15 min |
| 2 | Task 5 | ashare router — all 3 endpoints | 20 min |
| 2 | Task 6 | diagnose + watchlist endpoint tests | 10 min |
| 3 | Task 7 | Dockerfile + docker-compose.yml | 15 min |
| 3 | Task 8 | Update Dockers docs | 5 min |
| 4 | Task 9 | End-to-end manual verification | 10 min |
| **Total** | | | **~1.5 hours** |
