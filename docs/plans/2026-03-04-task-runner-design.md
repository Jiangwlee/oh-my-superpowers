# task-runner：通用任务执行 HTTP 服务设计方案

**日期**: 2026-03-04
**作者**: Bruce
**状态**: Design Approved
**前置文档**: [ashare-data n8n 集成设计](2026-03-04-ashare-data-n8n-integration-design.md)（已废弃，由本文档替代）

---

## 一、背景与动机

原方案试图在 n8n 容器内直接执行 Python CLI（`ashare-collect` 等），但 n8n 官方容器是 Alpine + Node.js 镜像，**没有 Python 环境**。

本方案将架构调整为：独立的 Python HTTP 服务容器（`task-runner`），n8n 通过 HTTP Request 节点调用。task-runner 不仅服务 ashare-data，未来可集成更多后端能力。

## 二、架构

```
┌───────────────────────────────────────────────────────┐
│                   infra_net (Docker)                   │
│                                                       │
│  n8n_app ──HTTP──▶ task_runner ──import──▶ ashare_data │
│  :5678              :8000                              │
│                       │                                │
│                       ▼                                │
│              ~/.ashare-assistant (volume mount)         │
│                                                       │
│  postgres                                             │
│  :5432                                                │
└───────────────────────────────────────────────────────┘
```

- **task-runner**：FastAPI 应用，独立 Docker 容器，仅在 `infra_net` 内通信，不暴露宿主机端口
- **ashare-data**：保持独立 package，通过 `pip install -e` 挂载到 task-runner 容器
- **数据目录**：宿主机 `~/.ashare-assistant` 挂载到容器内**相同路径**，`config.py` 无需修改

## 三、关键决策

| # | 决策 | 选项 | 理由 |
|---|------|------|------|
| 1 | 部署方式 | 独立 Docker 容器（Sidecar） | 已有 `infra_net` 基础设施，容器间通信天然隔离 |
| 2 | 服务命名 | `task-runner` | 简洁直接，强调"执行任务"的本质 |
| 3 | HTTP 框架 | FastAPI | 自带 OpenAPI 文档、async 支持、Pydantic 类型校验 |
| 4 | 执行模式 | 同步，预留异步 | 当前任务耗时可控（几分钟），API 响应包含 `task_id` 字段为异步预留 |
| 5 | 端口 | 容器内 8000，不映射宿主机 | 唯一消费者是同网络的 n8n，减少攻击面 |
| 6 | 代码位置 | `packages/task-runner/` + `~/Dockers/TaskRunner/` | 业务代码在本项目，Docker 配置在 Dockers 仓库 |
| 7 | ashare-data 集成 | 独立 package + `pip install -e` | 保持 ashare-data 独立可用性（CLI 命令不依赖 FastAPI） |
| 8 | API 路由 | 按服务分组 RESTful | `/ashare/collect`、`/ashare/diagnose` 等，语义清晰 |

## 四、项目结构

```
packages/task-runner/
├── task_runner/
│   ├── __init__.py
│   ├── app.py                # FastAPI 应用入口
│   ├── models.py             # 通用响应模型
│   └── routers/
│       ├── __init__.py
│       ├── health.py         # GET /health
│       └── ashare.py         # /ashare/* 路由
├── pyproject.toml
└── Dockerfile

~/Dockers/TaskRunner/
├── docker-compose.yml
└── .env.example
```

## 五、API 设计

### 5.1 通用响应模型

```python
class TaskResult(BaseModel):
    task_id: str            # UUID，预留异步扩展
    status: str             # "success" | "failed"
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    result: dict | None     # 任务特有的返回数据
    error: str | None       # 失败时的错误信息
```

### 5.2 端点列表

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `POST` | `/ashare/collect` | 数据采集 |
| `POST` | `/ashare/diagnose` | 决策诊断 |
| `POST` | `/ashare/watchlist` | 自选股监控（单次扫描） |

### 5.3 请求/响应示例

**请求**：
```
POST /ashare/collect
Content-Type: application/json

{
  "date": "2026-03-04",
  "skip_collect": false,
  "skip_filter": false
}
```

**成功响应**：
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "success",
  "started_at": "2026-03-04T22:05:00",
  "finished_at": "2026-03-04T22:08:32",
  "duration_seconds": 212.0,
  "result": {
    "raw_files": 12,
    "filtered_files": 8,
    "data_dir": "/home/bruce/.ashare-assistant/data/2026-03-04"
  },
  "error": null
}
```

**失败响应**：
```json
{
  "task_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "status": "failed",
  "started_at": "2026-03-04T22:05:00",
  "finished_at": "2026-03-04T22:05:03",
  "duration_seconds": 3.0,
  "result": null,
  "error": "网络超时：无法连接 eastmoney.com"
}
```

## 六、ashare-data 改造

task-runner 需要以 Python 函数方式调用 ashare-data，而非 CLI。当前 `main()` 函数耦合了参数解析、print 输出和 sys.exit，不适合被 import。

**改造模式**：每个 CLI 脚本拆出核心函数（纯逻辑），`main()` 变薄壳。

```python
# collect.py 改造后

def run_collect(
    date: str | None = None,
    skip_collect: bool = False,
    skip_filter: bool = False,
    **kwargs,
) -> dict:
    """核心采集逻辑，可被 import 调用。

    Args:
        date: 目标日期 YYYY-MM-DD，默认今日。
        skip_collect: 跳过数据采集。
        skip_filter: 跳过 filter 转换。

    Returns:
        {"raw_files": 12, "filtered_files": 8, "data_dir": "..."}
    """
    ...


def main() -> None:
    """CLI 入口，薄壳。"""
    parser = argparse.ArgumentParser(...)
    args = parser.parse_args()
    result = run_collect(date=args.date, skip_collect=args.skip_collect, ...)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)
```

**改造清单**：

| 脚本 | 拆出的核心函数 | 优先级 |
|------|--------------|--------|
| `collect.py` | `run_collect()` | P0 |
| `diagnose.py` | `run_diagnose()` | P0 |
| `watchlist_monitor.py` | `run_watchlist_scan()` | P0 |
| `collect_eastmoney_guba.py` | `run_eastmoney_collect()` | P1 |
| `collect_taoguba_stock.py` | `run_taoguba_collect()` | P1 |

## 七、Docker 配置

### 7.1 Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装 task-runner 依赖
RUN pip install --no-cache-dir fastapi uvicorn

# ashare-data 和 task-runner 通过 volume 挂载后 pip install -e
# 见 docker-compose.yml 和 entrypoint.sh

EXPOSE 8000

CMD ["uvicorn", "task_runner.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 7.2 docker-compose.yml

```yaml
services:
  task-runner:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: task_runner
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
    volumes:
      # ashare-data 源码（pip install -e，开发热更新）
      - /home/bruce/Projects/oh-my-superpowers/packages/ashare-data:/install/ashare-data:ro
      # task-runner 源码
      - /home/bruce/Projects/oh-my-superpowers/packages/task-runner:/install/task-runner:ro
      # 数据持久化（挂载到相同路径，config.py 无需修改）
      - /home/bruce/.ashare-assistant:/home/bruce/.ashare-assistant
    networks:
      - infra_net

networks:
  infra_net:
    external: true
```

### 7.3 容器启动流程

容器 entrypoint 负责 `pip install -e` 两个包，然后启动 uvicorn。修改宿主机代码后重启容器即可生效。

## 八、n8n 工作流调用方式

n8n 中使用 HTTP Request 节点：

```
Method: POST
URL: http://task-runner:8000/ashare/collect
Body (JSON): {"date": "{{ $now.format('yyyy-MM-dd') }}"}
Timeout: 600000  (10 分钟)
Retry on Fail: true
Max Tries: 3
Wait Between Tries: 300000 (5 分钟)
```

判断结果用 IF 节点：`{{ $json.status === "success" }}`。

## 九、实施计划

### Phase 1: ashare-data 改造（1-2 天）

拆出核心函数（`run_collect`、`run_diagnose`、`run_watchlist_scan`），`main()` 变薄壳。添加单元测试。

### Phase 2: task-runner 骨架（0.5 天）

创建 `packages/task-runner/`，实现 FastAPI 应用、通用模型、health 端点。

### Phase 3: ashare router 集成（0.5 天）

实现 `/ashare/*` 路由，调用 ashare-data 核心函数。

### Phase 4: Docker 部署（0.5 天）

创建 Dockerfile、docker-compose.yml，部署到 `~/Dockers/TaskRunner/`，验证容器间通信。

### Phase 5: n8n 工作流（0.5 天）

创建 n8n 工作流，配置 HTTP Request 节点调用 task-runner，测试端到端流程。

## 十、风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 容器内 `~/.ashare-assistant` 路径映射 | 挂载到相同绝对路径，config.py 无需改动 |
| 采集耗时超过 HTTP 超时 | n8n 端设 10 分钟超时 + 3 次重试；未来可加异步模式 |
| ashare-data 改造影响现有 CLI | 改造原则：只拆函数不改逻辑，CLI 行为不变 |
| Docker 用户权限 | python:3.12-slim 默认 root，数据目录权限无问题 |
