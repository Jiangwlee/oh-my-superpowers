# Ashare-Data 部署指南

## 概述

本文档提供 ashare-data 系统的完整部署指南，包括：
- n8n 工作流自动化平台
- task-runner HTTP 服务
- ashare-data 数据采集

## 快速开始

### 1. 启动基础设施

#### PostgreSQL（可选，用于 n8n 持久化）

```bash
cd /home/bruce/Dockers/Infrastructure
docker compose up -d postgres
```

#### n8n

```bash
cd /home/bruce/Dockers/N8N
docker compose up -d
```

访问：http://localhost:10003

#### task-runner

```bash
cd /home/bruce/Dockers/TaskRunner
docker compose up -d --build
```

验证：
```bash
docker exec n8n_app wget -qO- http://task_runner:8000/health
# 输出：{"status":"ok"}
```

### 2. 导入工作流

1. 打开 n8n UI: http://localhost:10003
2. Settings → Import from File
3. 选择文件：`/home/bruce/Projects/oh-my-superpowers/deployment/workflows/ashare-daily-simple.json`
4. 激活工作流（开关 ON）

### 3. 验证部署

```bash
# 检查所有容器
docker ps --filter name="n8n\|task_runner"

# 测试 task-runner 端点
curl http://task_runner:8000/health
curl -X POST http://task_runner:8000/ashare/diagnose \
  -H "Content-Type: application/json" \
  -d '{"dry_run":true}'

# 检查数据目录
ls -la ~/.ashare-assistant/
```

## 文档结构

```
deployment/
├── 00_Deployment.md      # 本文件（总览）
├── 01_n8n.md            # n8n 详细部署
├── 02_task-runner.md    # task-runner 详细部署
├── README.md            # 快速入门
└── docker/
    ├── n8n/
    │   └── docker-compose.yml
    └── task-runner/
        └── docker-compose.yml
```

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    infra_net (Docker)                    │
│                                                          │
│  n8n_app ──HTTP──▶ task_runner ──import──▶ ashare_data  │
│  :5678              :8000                                │
│                       │                                  │
│                       ▼                                  │
│              ~/.ashare-assistant (volume mount)          │
│                                                          │
│  postgres                                                │
│  :5432                                                   │
└─────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. n8n

- **用途**: 工作流编排引擎
- **功能**: 
  - Cron Trigger 定时触发（工作日 22:00）
  - HTTP Request 调用 task-runner
  - 条件分支、错误处理、重试逻辑
- **访问**: http://localhost:10003

### 2. task-runner

- **用途**: HTTP 服务，封装 ashare-data 功能
- **技术栈**: FastAPI + Python 3.12
- **端点**:
  - `GET /health` - 健康检查
  - `POST /ashare/collect` - 数据采集
  - `POST /ashare/diagnose` - 决策诊断
  - `POST /ashare/watchlist` - 自选股扫描
- **网络**: 仅内部通信（infra_net），不暴露宿主机端口

### 3. ashare-data

- **用途**: A 股数据采集与处理
- **功能**:
  - 多源数据采集（新闻、资金、论坛等）
  - 格式转换（JSON → Markdown）
  - 情绪分析
  - 决策日志回填
- **数据目录**: `~/.ashare-assistant/`

## 维护

### 查看日志

```bash
# n8n
docker logs n8n_app -f --tail 50

# task-runner
docker logs task_runner -f --tail 50
```

### 重启服务

```bash
# 单个服务
docker compose restart n8n_app
docker compose restart task_runner

# 全部服务
cd ~/Dockers/N8N && docker compose restart
cd ~/Dockers/TaskRunner && docker compose restart
```

### 更新代码

修改 ashare-data 代码后：

```bash
# 重启 task-runner 即可生效（热更新）
docker compose restart task_runner
```

## 故障排查

### 问题：容器未运行

**检查**:
```bash
docker ps --filter name="n8n\|task_runner"
docker logs <container_name> --tail 100
```

### 问题：网络不通

**检查**:
```bash
# 确认容器在同一网络
docker network inspect infra_net

# 测试连通性
docker exec n8n_app wget -qO- http://task_runner:8000/health
```

### 问题：数据未写入

**检查**:
```bash
# Volume 挂载
docker inspect n8n_app | grep ashare-assistant
docker inspect task_runner | grep ashare-assistant

# 权限
ls -la ~/.ashare-assistant/

# 错误日志
cat ~/.ashare-assistant/logs/error_*.log
```

## 下一步

1. 阅读详细文档：
   - [01_n8n.md](./01_n8n.md) - n8n 部署指南
   - [02_task-runner.md](./02_task-runner.md) - task-runner 部署指南

2. 自定义配置：
   - 调整采集时间（Cron Trigger）
   - 添加告警通知（钉钉/飞书/Slack）
   - 扩展更多服务（Scrapling、LiteLLM 等）

3. 性能优化：
   - 添加监控端点
   - 集成 Prometheus + Grafana
   - 并行化处理

---

**参考**: 
- [n8n 官方文档](https://docs.n8n.io/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [ashare-data 源码](../../packages/ashare-data/)

