# task-runner 部署指南

## 概述

task-runner 是一个 FastAPI HTTP 服务容器，为 n8n 提供 ashare-data 的功能调用接口。

## 架构

```
n8n (HTTP Request) → task_runner:8000 → ashare_data (Python import)
                              ↓
                      ~/.ashare-assistant (volume mount)
```

## 快速启动

```bash
cd /home/bruce/Dockers/TaskRunner
docker compose up -d --build
```

## 验证运行

### 1. 检查容器状态

```bash
docker ps --filter name=task_runner
```

预期输出：`Up` 状态

### 2. 测试健康检查

```bash
docker exec n8n_app wget -qO- http://task_runner:8000/health
```

预期输出：`{"status":"ok"}`

### 3. 测试 API 端点

```bash
# 数据采集
curl -X POST http://localhost:8000/ashare/collect \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-03-04","skip_collect":true,"skip_filter":true}'

# 决策诊断
curl -X POST http://localhost:8000/ashare/diagnose \
  -H "Content-Type: application/json" \
  -d '{"dry_run":true}'

# 自选股扫描
curl -X POST http://localhost:8000/ashare/watchlist \
  -H "Content-Type: application/json" \
  -d '{"force":false}'
```

## Docker 配置

### docker-compose.yml

位于 `deployment/docker/task-runner/docker-compose.yml`:

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
      # ashare_data 源码挂载（只读）
      - /home/bruce/Projects/oh-my-superpowers/packages/ashare-data/ashare_data:/usr/local/lib/python3.12/site-packages/ashare_data:ro
      # task-runner 源码挂载
      - /home/bruce/Projects/oh-my-superpowers/packages/task-runner:/install/task-runner
      # 数据持久化
      - /home/bruce/.ashare-assistant:/home/bruce/.ashare-assistant
    networks:
      - infra_net
```

### 关键配置说明

1. **ashare_data 挂载**: 直接挂载到 site-packages，避免 editable install 问题
2. **networks**: 加入 `infra_net` 与 n8n、postgres 通信
3. **volumes**: 数据目录保持与宿主机相同路径

## 维护

### 查看日志

```bash
docker logs task_runner -f --tail 50
```

### 重启服务

```bash
docker compose restart
```

### 重新构建

修改代码后重新构建：

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### 更新 ashare-data

由于 ashare_data 是通过 volume 挂载的，修改宿主机代码后只需重启：

```bash
docker compose restart task_runner
```

## API 端点

### GET /health

健康检查端点。

**响应**:
```json
{"status": "ok"}
```

### POST /ashare/collect

执行 A 股数据采集。

**请求体**:
```json
{
  "date": "2026-03-04",
  "skip_collect": false,
  "skip_filter": false
}
```

**响应**:
```json
{
  "task_id": "uuid",
  "status": "success",
  "started_at": "2026-03-04T22:00:00Z",
  "finished_at": "2026-03-04T22:05:00Z",
  "duration_seconds": 300.0,
  "result": {
    "ok": true,
    "data_dir": "/home/bruce/.ashare-assistant/data/2026-03-04",
    "collect": {"ok_count": 5, "error_count": 0},
    "filter": {"converted": 5},
    "sentiment": {"ok": true}
  },
  "error": null
}
```

### POST /ashare/diagnose

执行决策诊断（T+1/T+5 回填）。

**请求体**:
```json
{
  "today": "2026-03-04",
  "dry_run": false
}
```

### POST /ashare/watchlist

执行自选股单次扫描。

**请求体**:
```json
{
  "force": false
}
```

## 故障排查

### 问题：容器启动失败

**检查**:
```bash
docker logs task_runner --tail 100
```

常见原因：
- ashare_data 挂载路径错误
- 权限问题

### 问题：HTTP 请求超时

**检查**:
1. task-runner 是否运行：`docker ps --filter name=task_runner`
2. 网络连通性：`docker exec n8n_app wget -qO- http://task_runner:8000/health`
3. 采集耗时是否超过 timeout（默认 10 分钟）

### 问题：数据未写入

**检查**:
```bash
ls -la ~/.ashare-assistant/data/$(date +%Y-%m-%d)
docker inspect n8n_app | grep ashare-assistant
```

确保 volume 挂载正确且权限足够。

## 性能优化

### 调整超时时间

在 n8n 的 HTTP Request 节点中设置：
- Timeout: 600000ms (10 分钟)
- Retry on Fail: Enabled
- Max Tries: 3
- Wait Between Tries: 300000ms (5 分钟)

### 并行采集

如果采集多个数据源，考虑拆分任务：
- 使用多个 task-runner 实例
- 或通过 n8n 的 Split In Batches 节点并行执行

---

**参考**: 
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Docker Compose 配置](./docker/task-runner/docker-compose.yml)

## 环境变量配置

### .env 文件

在 `docker/task-runner/.env` 中配置环境变量（复制 `.env.example`）：

```bash
# Timezone
TZ=Asia/Shanghai

# Uvicorn configuration
UVICORN_WORKERS=1
UVICORN_PORT=8000

# Ashare-Data configuration
ASHARE_OUTPUT_DIR=/home/bruce/.ashare-assistant

# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Health check settings
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_RETRIES=3
HEALTH_CHECK_START_PERIOD=10
```

### 环境变量说明

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `TZ` | `Asia/Shanghai` | 时区设置 |
| `UVICORN_PORT` | `8000` | Uvicorn 监听端口 |
| `ASHARE_OUTPUT_DIR` | `/home/bruce/.ashare-assistant` | ashare-data 输出目录 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `HEALTH_CHECK_INTERVAL` | `30s` | 健康检查间隔 |
| `HEALTH_CHECK_TIMEOUT` | `10s` | 健康检查超时 |
| `HEALTH_CHECK_RETRIES` | `3` | 健康检查重试次数 |
| `HEALTH_CHECK_START_PERIOD` | `10s` | 健康检查启动宽限期 |

### 使用方法

1. 复制示例文件：
   ```bash
   cd /home/bruce/Projects/oh-my-superpowers/deployment/docker/task-runner
   cp .env.example .env
   ```

2. 修改 `.env` 文件中的配置

3. 重启容器：
   ```bash
   docker compose down
   docker compose up -d
   ```

---

**参考**: 
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Docker Compose 配置](./docker/task-runner/docker-compose.yml)

## JVQuant 券商账户配置（可选）

### 启用券商账户数据采集

要启用 jvQuant 券商账户数据的采集，需要配置凭证信息。有两种方式：

#### 方式 1: 环境变量（推荐用于 Docker）

在 `.env` 文件中设置：

```bash
# .env 文件
JVQUANT_APP_TOKEN=your_jvquant_token
EASTMONEY_ACCOUNT=your_eastmoney_account
EASTMONEY_PASSWORD=your_eastmoney_password
```

**优点**: 
- 安全（不将凭证写入文件）
- 适合 Docker 环境
- 易于通过 CI/CD 管理

#### 方式 2: 凭证文件

创建 `~/.ashare-data/jvquant.json` 文件：

```json
{
  "token": "your_jvquant_token",
  "acc": "your_eastmoney_account",
  "pass": "your_eastmoney_password"
}
```

然后在 docker-compose.yml 中挂载：

```yaml
volumes:
  - ~/.ashare-data/jvquant.json:/root/.openclaw/jvquant.json:ro
```

**注意**: 环境变量优先级高于配置文件。

### 费用控制

jvQuant API 调用会产生费用：
- **登录费用**: 0.5 元/次
- **每日预算**: 5 元（默认，最多 10 次登录）
- **费用追踪**: `~/.ashare-assistant/broker_data/costs/YYYY-MM-DD.json`

当达到每日预算后，新的 API 调用会被拒绝并记录错误日志。

### 验证配置

启动容器后检查日志：

```bash
docker logs task_runner --tail 50
```

成功时应该看到类似：
```
[broker_account] 成功加载 jvQuant 配置
```

失败时会看到：
```
[broker_account] 未检测到 jvQuant 配置，跳过券商账户采集
```

---

**参考**: 
- [JVQuant 平台参考](../../docs/jvquant-reference.md)
- [Docker Compose 配置](./docker/task-runner/docker-compose.yml)
