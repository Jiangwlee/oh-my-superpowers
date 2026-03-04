# Ashare-data 集成到 n8n 工作流设计方案

**日期**: 2026-03-04  
**作者**: Bruce  
**状态**: Design Approved  
**关联技能**: n8n-workflow-patterns, brainstorming

---

## 一、背景与动机

### 1.1 当前架构问题

当前 `ashare-data` 包集成了数据采集、处理和编排逻辑，存在以下问题：

- **职责混杂**：爬虫逻辑、数据处理、调度编排耦合在一起
- **难以复用**：编排逻辑（定时触发、条件分支、错误处理）硬编码在 Python 脚本中
- **运维复杂**：依赖 cron 系统任务，监控和调试不便
- **扩展困难**：新增数据源需要修改 Python 代码，无法通过配置快速调整

### 1.2 目标架构

将职责分离，形成清晰的层次结构：

```
┌─────────────────────────────────────────────────────────┐
│                    n8n Orchestration Layer              │
│  ├─ 定时触发（Cron Trigger）                            │
│  ├─ 流程编排（条件分支、重试、路由）                      │
│  ├─ 错误处理（重试机制、错误日志）                        │
│  └─ 结果通知（状态标记、文件监控）                        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 Ashare-data CLI Layer                   │
│  ├─ 数据采集（爬虫模块）                                │
│  ├─ 数据处理（格式转换）                                │
│  └─ 标准化接口（统一 CLI 规范）                          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
            ~/.ashare-assistant/（数据持久化层）
```

### 1.3 设计原则

1. **单一职责**：每个模块只做一件事，做好一件事
2. **配置驱动**：通过 CLI 参数和环境变量控制行为，避免硬编码
3. **可观测性**：清晰的输出格式、错误日志、状态标记
4. **容器友好**：适配 Docker 部署环境，便于扩展和维护

---

## 二、关键决策

### 决策 1：CLI 参数规范化

**决策内容**：所有 CLI 工具统一以下参数规范

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--output_dir` | 路径 | `ASHARE_OUTPUT_DIR` 环境变量 | 输出目录，解耦路径绑定 |
| `--output_format` | 枚举 | `json` | 输出格式：`json` 或 `markdown` |
| `--date` | 日期 | 当前日期 | 指定日期，格式 `YYYY-MM-DD` |
| `--help` | 标志 | - | 显示帮助文档 |

**理由**：
- `--output_dir` 实现路径解耦，适应不同部署环境（Docker 挂载、本地测试等）
- `--output_format` 统一输出格式，便于 n8n 工作流处理
- `--date` 支持手动指定日期，方便调试和历史数据回放
- `--help` 符合 Unix CLI 规范，便于自文档化

**替代方案**：
- 使用环境变量 `ASHARE_DATE` 替代 `--date` 参数（不采纳，CLI 显式参数更直观）
- 默认输出目录使用硬编码 `~/.ashare-assistant`（不采纳，需适配 Docker 挂载）

### 决策 2：输出文件命名规范

**决策内容**：输出文件路径为 `{output_dir}/{DATE}/{command}.{format}`

**示例**：
```bash
/data/ashare-assistant/2026-03-04/ashare-collect.json
/data/ashare-assistant/2026-03-04/ashare-diagnose.markdown
```

**理由**：
- 按日期分类，便于时间序列查询和历史数据追溯
- 文件名简洁（仅命令名 + 格式），便于脚本解析和监控
- 目录层级清晰，适配文件监控工具

**替代方案**：
- 扁平结构 `{output_dir}/{command}_{DATE}.{format}`（不采纳，日期维度难以聚合）
- 按模块分类 `{output_dir}/{module}/{command}.{format}`（不采纳，过度复杂）

### 决策 3：错误处理策略

**决策内容**：
- CLI 返回码：`0` 表示成功，非 `0` 表示失败（不区分错误类型）
- 详细错误通过日志和错误文件记录
- n8n 工作流层面实现重试机制（最多 3 次，间隔 5 分钟）

**理由**：
- 简单统一的错误码降低开发复杂度
- 详细错误信息通过日志系统处理，符合日志最佳实践
- 重试逻辑放在 n8n 层，复用 n8n 内置的重试能力

**替代方案**：
- 区分错误类型返回不同码（如 1=网络，2=解析，3=IO）（不采纳，增加维护成本）
- Python 脚本内部实现重试（不采纳，重复逻辑，难以集中监控）

### 决策 4：Docker 集成方式

**决策内容**：
- **安装方式**：容器启动时自动 `pip install -e /install/ashare-data`
- **数据挂载**：宿主机 `~/.ashare-assistant` 挂载到容器 `/data/ashare-assistant`
- **源码挂载**：宿主机 `packages/ashare-data` 挂载到容器 `/install/ashare-data`

**理由**：
- `pip install -e` 支持开发热更新，修改宿主机代码后容器自动生效
- 数据目录挂载确保持久化，容器重启不丢失数据
- 启动脚本自动化安装，避免手动干预

**替代方案**：
- 构建自定义 Dockerfile（不采纳，开发效率低，每次修改需重新构建）
- 宿主机运行脚本，n8n 通过 HTTP 调用（不采纳，增加网络复杂度）

### 决策 5：文件头文档规范

**决策内容**：所有 CLI 脚本前 20 行必须包含 Google 风格的文档字符串，描述功能、用法、参数、输出格式、异常处理等信息

**理由**：
- 符合项目 File-Header-Spec 规范
- 便于 AI 理解和代码生成
- 自文档化，减少额外文档维护成本

**替代方案**：
- 外部 Markdown 文档（不采纳，容易与代码不同步）
- 仅依赖类型注解（不采纳，不足以描述业务逻辑）

---

## 三、设计方案

### 3.1 Ashare-data CLI 规范

#### 3.1.1 文件头模板

```python
"""Ashare-collect - A 股数据采集工具

功能：
  采集 A 股市场数据（新闻、资金、板块、论坛等），输出为 JSON 或 Markdown 格式。
  数据采集源包括：金融界、同花顺、淘股吧、东方财富股吧等。

用法：
  ashare-collect --output_dir {dir} --output_format {json|markdown}
  ashare-collect --help  # 显示帮助

参数：
  --output_dir    输出目录（可选，默认从 ASHARE_OUTPUT_DIR 环境变量读取，否则 ~/.ashare-assistant）
  --output_format 输出格式：json | markdown（可选，默认 json）
  --date          指定日期 YYYY-MM-DD（可选，默认当前日期）
  
返回：
  0=成功，非 0=失败（错误码不区分类型，详细错误通过日志记录）

输出文件：
  {output_dir}/{DATE}/{command}.{format}
  
异常处理：
  捕获所有异常，记录错误日志到 {output_dir}/logs/error.log，返回错误码 1

作者：Bruce
维护者：Bruce
"""
```

#### 3.1.2 参数解析模块

创建 `ashare_data/core/cli.py` 统一参数解析逻辑：

```python
"""统一 CLI 参数解析模块。

提供标准化的参数解析、输出路径生成、日志配置等功能。
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def parse_base_args(description: str, epilog: str | None = None) -> argparse.ArgumentParser:
    """创建基础参数解析器。

    Args:
        description: 命令描述（用于 --help）
        epilog: 附加说明（可选）

    Returns:
        配置好的 ArgumentParser 实例
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument(
        "--output_dir",
        default=os.getenv("ASHARE_OUTPUT_DIR", str(Path.home() / ".ashare-assistant")),
        help="输出目录（默认从 ASHARE_OUTPUT_DIR 环境变量读取）",
    )
    parser.add_argument(
        "--output_format",
        choices=["json", "markdown"],
        default=os.getenv("ASHARE_OUTPUT_FORMAT", "json"),
        help="输出格式：json 或 markdown（默认 json）",
    )
    parser.add_argument(
        "--date",
        default=os.getenv("DATE", datetime.now().strftime("%Y-%m-%d")),
        help="指定日期 YYYY-MM-DD（默认当前日期）",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="启用详细日志输出"
    )
    return parser


def setup_logging(verbose: bool = False) -> None:
    """配置日志。

    Args:
        verbose: 是否启用详细日志
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_output_dir(output_dir: str, date: str) -> Path:
    """生成输出目录路径。

    Args:
        output_dir: 基础输出目录
        date: 日期字符串 YYYY-MM-DD

    Returns:
        完整输出目录 Path 对象
    """
    return Path(output_dir).expanduser() / date
```

#### 3.1.3 CLI 入口函数

```python
def main() -> int:
    """CLI 入口函数。

    Returns:
        0=成功，非 0=失败
    """
    parser = parse_base_args(description="A 股数据采集工具")
    # 添加命令特有参数
    # parser.add_argument("--skip-news", action="store_true", ...)
    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        # 执行核心逻辑
        result = _collect_data(args)
        logger.info("数据采集完成")
        return 0
    except Exception as e:
        logger.exception("数据采集失败")
        return 1


def _collect_data(args: argparse.Namespace) -> None:
    """执行数据采集逻辑。

    Args:
        args: 解析后的参数
    """
    output_dir = get_output_dir(args.output_dir, args.date)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 采集逻辑...
    # 输出文件：{output_dir}/ashare-collect.{args.output_format}
```

---

### 3.2 Ashare-data 改造清单

| 脚本 | 当前状态 | 改造任务 | 优先级 |
|------|---------|---------|--------|
| `collect.py` | ✅ 有 CLI | 1. 添加文件头文档<br>2. 统一参数解析<br>3. 标准化输出路径 | P0 |
| `diagnose.py` | ✅ 有 CLI | 同上 | P0 |
| `watchlist_monitor.py` | ✅ 有 CLI | 同上 | P0 |
| `collect_eastmoney_guba.py` | ✅ 有 CLI | 同上 | P1 |
| `collect_taoguba_stock.py` | ✅ 有 CLI | 同上 | P1 |
| `post_close_decision_pipeline.py` | ✅ 有 CLI | 同上 | P1 |
| `filter_to_markdown.py` | ⚠️ 部分有 CLI | 统一参数规范 | P2 |

**改造步骤**：
1. 创建 `ashare_data/core/cli.py`（共用参数解析模块）
2. 逐个改造脚本，添加文件头和统一参数
3. 添加单元测试验证参数解析
4. 更新 README 文档说明新规范

---

### 3.3 n8n 工作流设计

#### 3.3.1 工作流概览

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│ Cron Trigger│────▶│ Execute Command  │────▶│ Switch       │
│  工作日      │     │ ashare-collect   │     │ (exitCode)   │
│  15:30 UTC  │     │                  │     └──────┬───────┘
└─────────────┘     └──────────────────┘            │
                                                     │
                              ┌──────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
            ┌──────────────┐    ┌──────────────────┐
            │ Write File   │    │ Execute Command  │
            │ success_flag │    │ 记录错误日志      │
            │ (成功分支)    │    │ (失败分支)        │
            └──────────────┘    └──────────────────┘
                                      │
                                      ▼
                              ┌──────────────────┐
                              │ Wait (5 分钟)     │
                              │ 最多重试 3 次      │
                              └──────────────────┘
```

#### 3.3.2 节点配置详情

**节点 1: Cron Trigger**
- **类型**: `n8n-nodes-base.cron`
- **配置**:
  ```json
  {
    "rule": {
      "interval": [
        {
          "field": "betweenHours",
          "betweenHours": [15, 16],
          "betweenMinutes": [30, 30]
        }
      ],
      "daysOfWeek": [1, 2, 3, 4, 5]
    }
  }
  ```
- **说明**: 北京时间每天 15:30 触发（UTC 时间 7:30）

**节点 2: Execute Command**
- **类型**: `n8n-nodes-base.executeCommand`
- **配置**:
  ```json
  {
    "command": "ashare-collect --date {{ $now.format('yyyy-MM-dd') }} --output_dir /data/ashare-assistant --output_format json",
    "execution": {
      "timeout": 300
    }
  }
  ```
- **说明**: 采集当日数据，输出到 Docker 容器内路径

**节点 3: Switch**
- **类型**: `n8n-nodes-base.switch`
- **配置**:
  ```json
  {
    "conditions": {
      "string": [
        {
          "value1": "={{ $json.exitCode }}",
          "operation": "equals",
          "value2": "0"
        }
      ]
    }
  }
  ```
- **说明**: 根据 exitCode 判断成功/失败分支

**节点 4: Write File (成功分支)**
- **类型**: `n8n-nodes-base.writeBinaryFile` 或 `n8n-nodes-base.set`
- **配置**:
  ```json
  {
    "filePath": "/data/ashare-assistant/status/success_flag",
    "content": "={{ $now.format('yyyy-MM-dd HH:mm:ss') }}"
  }
  ```

**节点 5: Execute Command (失败分支)**
- **类型**: `n8n-nodes-base.executeCommand`
- **配置**:
  ```json
  {
    "command": "echo \"{{ $now.format('yyyy-MM-dd HH:mm:ss') }} ERROR: exitCode={{ $json.exitCode }}\" >> /data/ashare-assistant/logs/error.log",
    "execution": {
      "timeout": 30
    }
  }
  ```

**节点 6: Wait (重试逻辑)**
- **类型**: `n8n-nodes-base.wait` 或 `n8n-nodes-base.if`
- **配置**:
  ```json
  {
    "waitTime": 300,
    "retryCount": 3
  }
  ```
- **说明**: 失败后等待 5 分钟，最多重试 3 次

#### 3.3.3 错误处理增强

**方案 A: 使用 n8n 内置错误处理**
- 启用 Workflow 级别的错误处理
- 配置 `errorWorkflow` 节点处理所有异常

**方案 B: 手动重试逻辑**
- Switch 节点判断 exitCode
- 失败分支调用 `ashare-collect` 重试
- 使用计数器节点跟踪重试次数

**推荐方案 B**（更灵活，可自定义重试策略）

---

### 3.4 Docker 容器配置

#### 3.4.1 Docker Compose 配置

创建 `docker-compose.yml`（如果尚未使用 docker-compose）：

```yaml
version: '3.8'

services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    container_name: n8n_app
    restart: unless-stopped
    ports:
      - "10003:5678"
    environment:
      - TZ=Asia/Shanghai
      - N8N_DIAGNOSTICS_ENABLED=false
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=your_secure_password
    volumes:
      # n8n 数据
      - n8n_data:/home/node/.n8n
      # ashare-data 源码（热更新）
      - /home/bruce/Projects/oh-my-superpowers/packages/ashare-data:/install/ashare-data
      # ashare-assistant 数据（持久化）
      - /home/bruce/.ashare-assistant:/data/ashare-assistant
    entrypoint: ["tini", "--", "/docker-entrypoint.sh"]
    command: ["sh", "-c", "/docker-entrypoint.d/10-install-ashare.sh && /docker-entrypoint.sh"]

volumes:
  n8n_data:
```

#### 3.4.2 启动脚本

创建启动脚本 `/home/bruce/Dockers/N8N/n8n_data/docker-entrypoint.d/10-install-ashare.sh`：

```bash
#!/bin/bash
set -e

echo "=== Ashare-data 启动安装脚本 ==="

# 检查是否已安装
if [ ! -d "/usr/local/lib/python3.12/site-packages/ashare_data" ]; then
    echo "检测到 ashare-data 未安装，开始安装..."
    pip install -e /install/ashare-data
    echo "安装完成，版本信息："
    ashare-collect --version || echo "无版本信息"
else
    echo "ashare-data 已安装，跳过安装步骤"
fi

# 确保数据目录存在
echo "创建数据目录..."
mkdir -p /data/ashare-assistant/{data,logs,status,cache,broker_data,signals,memory}

# 检查 Python 环境
echo "Python 环境信息："
python --version
pip --version

echo "=== 启动完成 ==="

# 执行原 entrypoint
exec "$@"
```

**权限设置**:
```bash
chmod +x /home/bruce/Dockers/N8N/n8n_data/docker-entrypoint.d/10-install-ashare.sh
```

#### 3.4.3 容器重启流程

**方式 A: 修改宿主机代码**
```bash
# 修改 ashare-data 后，只需重启容器
docker restart n8n_app
# 容器启动脚本会自动安装最新版本的代码（-e 参数）
```

**方式 B: 强制重新安装**
```bash
# 删除已安装版本
docker exec n8n_app pip uninstall -y ashare-data
# 重启容器重新安装
docker restart n8n_app
```

---

## 四、实施计划

### Phase 1: Ashare-data 规范化（预计 1-2 天）

**任务**:
1. 创建 `ashare_data/core/cli.py`（统一参数解析）
2. 改造 `collect.py`（添加文件头、统一参数）
3. 改造 `diagnose.py`
4. 改造 `watchlist_monitor.py`
5. 添加单元测试验证参数解析
6. 更新 README 文档

**验收标准**:
- 所有 CLI 工具支持 `--help`
- 所有 CLI 工具支持 `--output_dir --output_format --date`
- 输出文件命名符合 `{output_dir}/{DATE}/{command}.{format}`
- 单元测试通过率 100%

### Phase 2: Docker 容器配置（预计 0.5 天）

**任务**:
1. 创建 Docker Compose 配置（或修改现有 docker run 命令）
2. 创建启动脚本 `10-install-ashare.sh`
3. 测试容器启动和数据挂载
4. 验证 `pip install -e` 自动安装

**验收标准**:
- 容器启动后 `ashare-collect --help` 可用
- 输出到 `/data/ashare-assistant` 的数据可访问
- 宿主机修改代码后，重启容器自动生效

### Phase 3: n8n 工作流开发（预计 0.5 天）

**任务**:
1. 设计 n8n 工作流画布
2. 配置 Cron Trigger
3. 配置 Execute Command 节点
4. 配置 Switch 和重试逻辑
5. 配置错误日志和状态标记
6. 测试工作流执行

**验收标准**:
- 工作日 15:30 自动触发
- 成功时写入 `success_flag` 文件
- 失败时记录 `error.log` 并重试
- 手动 Webhook 触发可用

### Phase 4: 集成测试（预计 0.5 天）

**任务**:
1. 模拟网络错误测试重试机制
2. 验证输出文件格式正确性
3. 监控日志输出
4. 性能测试（数据采集耗时）

**验收标准**:
- 所有测试场景通过
- 数据采集耗时 < 10 分钟
- 无未捕获异常

---

## 五、风险与缓解

### 风险 1: Docker 权限问题

**问题**: 容器内进程可能无权写入挂载目录

**缓解措施**:
- 预先检查宿主机目录权限
- 在 Docker Compose 中添加 `user` 配置
- 测试 `docker run --user` 参数

### 风险 2: 爬虫反爬策略变化

**问题**: 数据源网站修改反爬机制导致采集失败

**缓解措施**:
- 在 `ashare_data/core/http_client.py` 中添加 User-Agent 轮换
- 添加请求间隔控制
- 监控失败率，自动切换备用数据源

### 风险 3: n8n 超时限制

**问题**: 数据采集耗时超过 n8n 执行超时

**缓解措施**:
- 调整 n8n 超时配置 `N8N_EXECUTION_TIMEOUT`
- 使用 Webhook 异步触发（提交任务后立即返回，后台处理）
- 分模块采集，并行执行

---

## 六、后续扩展

### 6.1 多数据源并行采集

将采集任务拆分为多个独立脚本，通过 n8n 并行执行：

```
ashare-collect-news     # 新闻采集
ashare-collect-funding  # 资金流采集
ashare-collect-forum    # 论坛采集
```

n8n 工作流中使用 `SplitInBatches` 节点并行执行。

### 6.2 数据质量监控

新增 `ashare-diagnose` 命令，自动检查数据完整性：

```bash
ashare-diagnose --output_dir /data/ashare-assistant --output_format json
```

输出内容包括：
- 数据完整性检查
- 异常值检测
- 数据源健康状态

### 6.3 告警通知集成

通过 n8n 集成告警渠道：

- **邮件通知**: 采集失败时发送邮件
- **钉钉/飞书**: 企业 IM 实时通知
- **Slack**: 开发团队协作通知

---

## 七、参考资料

- [n8n Execute Command 节点文档](https://docs.n8n.io/nodes/built-in/nodes/executecommand/)
- [n8n Cron Trigger 文档](https://docs.n8n.io/nodes/built-in/nodes/cron/)
- [File-Header-Spec](/home/bruce/Projects/oh-my-superpowers/File-Header-Spec.md)
- [Ashare-data 源码](/home/bruce/Projects/oh-my-superpowers/packages/ashare-data/)
- [n8n-workflows 参考](/home/bruce/Github/n8n-workflows/)

---

**文档版本**: v1.0  
**最后更新**: 2026-03-04  
**审批状态**: 设计已批准，待实施
