# A-Share Platform Deployment

当前部署入口已经切换为 `ashare-platform`，不再依赖 `n8n` 或 `task-runner`。

## 部署目录

当前唯一有效的 Compose 配置：

- `docker/ashare-platform/docker-compose.yml`

本目录下的旧 `n8n` / `task-runner` 部署文档已废弃并移除。

## 快速开始

### 1. 配置环境变量

在 `deployment/docker/ashare-platform/.env` 中配置：

```env
ASHARE_THEME_SEMANTIC_ENRICH_ENABLED=1
ASHARE_MARKET_REVIEW_SEMANTIC_ENRICH_ENABLED=1
OPENAI_BASE_URL=http://127.0.0.1:10000/v1
OPENAI_MODEL=qwen3.5-27b
OPENAI_API_KEY=sk-...
```

说明：

- `.env` 属于本地部署配置，不应提交到 Git
- 当前容器通过 host 网络访问宿主机上的 LLM 和 Chrome CDP

### 2. 构建并启动

```bash
docker compose -f deployment/docker/ashare-platform/docker-compose.yml build
docker compose -f deployment/docker/ashare-platform/docker-compose.yml up -d
```

### 3. 验证运行

```bash
docker ps --filter name=ashare_platform_backend
curl http://127.0.0.1:8000/health
```

### 4. 初始化历史数据

```bash
docker exec ashare_platform_backend python -m app.cli init-data --days 30
```

### 5. 运行最近一个交易日全流程

```bash
docker exec ashare_platform_backend python -m app.cli collect-all
```

## 访问方式

当前 compose 使用 `network_mode: host`，因此可直接从宿主机访问：

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/market-emotion/history`

## 容器行为

镜像内使用 `supervisord` 管理两个进程：

- `uvicorn`
- `cron`

定时任务：

- 每个工作日 `15:30` 运行 `collect-all`
- 脚本会先判断当天是否为真实交易日，非交易日自动跳过

时区：

- 运行时使用 `Asia/Shanghai`

## 依赖说明

### Chrome CDP

部分同花顺接口需要真实浏览器会话。当前容器通过宿主机 `9222` 端口访问 Chrome DevTools：

```bash
http://127.0.0.1:9222
```

### LLM

当前语义增强使用 OpenAI-compatible 接口：

```bash
http://127.0.0.1:10000/v1
```

已用于：

- `theme_pool` 语义字段
- `market_review` 摘要与 Markdown 报告

## 常用验证命令

```bash
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/market-emotion/history?days=3"
curl "http://127.0.0.1:8000/theme-pool/daily?trade_date=2026-03-20&limit=3"
curl http://127.0.0.1:10000/v1/models
curl http://127.0.0.1:9222/json/version
```

## Credits

- Workflow design based on `n8n-workflows` best practices
- Reference: https://github.com/Zie619/n8n-workflows
