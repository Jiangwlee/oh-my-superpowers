# AGENTS.md - OpenclawSkills 开发指南

本项目开发了一系列满足 Openclaw 规范的 Skills（智能体技能），主要用于金融数据抓取、分析与研究。

## IRON RULES

- NO SKILL DESIGN WITHOUT reading `Skills-Dev-Guides.md` and `Claude-Skill-Dev-Guide.md`.
- Every skill in `skills/` is independent and autonomous
- 不要兼容性：正确的设计 > 兼容性。不得为了兼容而增加代码，也不得在注释中添加“兼容”相关表述。

## 规范参考

- [Agent Skills](https://github.com/agentskills/agentskills): Openclaw 遵从的 Skills 规范
- [Tools](https://docs.openclaw.ai/tools/browser): Openclaw 内置工具
- [Skills Development Guide](Skills-Dev-Guide.md)：Skills开发经验，当发现一种有效的Skill编写模式时，可追加到此文件中。
- [Claude Skill Development Guide](Claude-Skill-Dev-Guide.md)：Claude官方Skill开发手册。
- [File Header Spec](File-Header-Spec.md)：文件头规范，要求前 20 行让 AI 理解文件全貌。所有 Markdown 和 Python 文件必须遵循。
- [JVQuant 平台参考](docs/jvquant-reference.md)：JVQuant 券商交易接口文档，含 API 规格、计费标准、费用优化策略。
## 代码参考

- [n8n-workflows](https://github.com/Zie619/n8n-workflows)：外部参考仓库。开发 `n8n` 工作流时可参考此仓库的类似场景。

## 部署与编排

### n8n + task-runner 架构

本项目已集成基于 n8n 的自动化编排系统：

```
┌─────────────────────────────────────────────────────────┐
│                    infra_net (Docker)                     │
│                                                          │
│  n8n_app ──HTTP──▶ task_runner ──import──▶ ashare_data  │
│  :5678              :8000                                │
│                       │                                  │
│                       ▼                                  │
│              ~/.ashare-assistant (volume mount)          │
└─────────────────────────────────────────────────────────┘
```

**组件说明**:
- **n8n**: 工作流编排引擎，负责定时触发、条件分支、错误处理
- **task-runner**: FastAPI HTTP 服务，封装 ashare-data 功能为 REST API
- **ashare-data**: A 股数据采集库，通过 volume 挂载到 task-runner

**部署文档**: 参见 [`deployment/`](deployment/) 目录
- `00_Deployment.md` - 总览和快速开始
- `01_n8n.md` - n8n 详细部署指南
- `02_task-runner.md` - task-runner 详细部署指南

**Docker 配置**: 参见 `deployment/docker/` 目录
- `docker/n8n/docker-compose.yml`
- `docker/task-runner/docker-compose.yml`

## 技术栈
## 技术栈

- **语言**: Python 3.10+
- **HTTP 客户端**: Scrapling Fetcher（基于 curl_cffi，TLS 指纹模拟）
- **HTML 解析**: Scrapling Selector（CSS/XPath 选择器，lxml 后端）
- **测试**: unittest / pytest

说明
----
- Scrapling 提供 `Fetcher.get(url)` 返回 Response 对象（继承自 Selector）
- Response 支持链式调用 `.css()/.xpath()/.re()` 提取结构化数据
- 避免使用 `urllib.request` 和 `html.parser` 手写解析器
- 核心模块：`ashare_data.core.scraper` 封装 Scrapling API

## 研究与参考

开发新的Skills时，要避免重复造轮子。对于用户的需求，首先要在使用`gh search`命令在github上检索相关项目，对于关联度较高的项目，下载代码至`github_cache`目录并深入研究。
`github_cache`管理规范：
1.为每个研究主题建立一个子目录，比如：`github_cache/skills`. 与该主题相关的项目将下载至该目录中。
2.用`github_cache/INDEX.md`为所有github项目建立索引，方便快速检索项目。

---

## 代码风格

### 1. 导入排序

标准库 → 第三方 → 本地模块，组内按字母排序：

```python
import json
import logging
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from typing import Any

import requests
from ashare_data import fetchers
```

### 2. 类型注解

- Python 3.10+ 联合类型: `str | None` (非 `Optional[str]`)
- 复杂类型用 type alias:

```python
Post = dict[str, Any]
Posts = list[Post]
```

### 3. 命名

| 类型 | 规则 | 示例 |
|------|------|------|
| 模块 | 小写下划线 | `taoguba.py` |
| 类 | 大驼峰 | `TaogubaFetchersTest` |
| 函数 | 小写下划线 | `fetch_taoguba_hot()` |
| 私有函数 | 前缀下划线 | `_fetch_detail()` |
| 常量 | 全大写 | `_BASE_URL` |

### 4. Docstring (Google 风格)

```python
def fetch_data(count: int = 20) -> list[dict]:
    """获取数据。

    Args:
        count: 返回数量。

    Returns:
        数据列表，出错时返回空列表。
    """
```

### 5. 错误处理

- 数据获取函数: 捕获异常后返回空列表/字典，不抛出
- 用 `logger.exception()` 记录错误
- 网络请求设置 timeout (默认 15 秒)

```python
def fetch_data(url: str) -> list[dict]:
    try:
        return data
    except Exception as e:
        logger.exception("fetch_data 出错: %s", e)
        return []
```

### 6. HTML 解析

**禁止正则**，必须用 `html.parser`：

```python
from html.parser import HTMLParser

class _MyParser(HTMLParser):
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div" and self._get_attr(attrs, "id") == "first":
            self._in_content = True

    def _get_attr(self, attrs, key: str) -> str:
        for name, val in attrs:
            if name == key:
                return val or ""
        return ""
```

### 7. 并发

用 `ThreadPoolExecutor`:

```python
with ThreadPoolExecutor(max_workers=min(8, len(urls))) as pool:
    contents = list(pool.map(_fetch_detail, urls))
```

### 8. 日志

`logger = logging.getLogger(__name__)`，用 `logger.debug()` / `logger.warning()` / `logger.exception()`

---

## 项目结构

```
packages/
└── ashare-data/               # A股数据采集基础设施包（pip install -e）
    ├── ashare_data/
    │   ├── core/              # config（路径）/ http_client / cache
    │   ├── fetchers/          # 各数据源采集模块（broker/funding/news/taoguba…）
    │   ├── collect.py         # 统一采集入口（ashare-collect CLI）
    │   └── filter_to_markdown.py  # raw JSON → filtered Markdown
    └── pyproject.toml

skills/
├── ashare-assistant/          # A股交易助手 Skill（LLM 工作流）
│   ├── scripts/               # 交易分析脚本（依赖 ashare_data 包）
│   │   ├── run_analysis.py    # 子代理流水线调度（5阶段）
│   │   ├── trade_review.py    # 交易复盘（确定性）
│   │   ├── holding_insight.py # 持仓洞察（确定性）
│   │   ├── risk_check.py      # 风险检查
│   │   ├── decision_logger.py # 决策日志写入
│   │   ├── prompts/           # LLM prompt 模板
│   │   └── core/shared.py     # Skill 内部共享工具
│   ├── tests/                 # 单元测试
│   ├── references/            # 参考文档
│   ├── evolution/             # 演进记录
│   ├── strategy/              # 策略配置
│   └── SKILL.md
├── agent-roundtable/
├── github-researcher/
├── markdown-to-anything/
└── openclaw-github-tracker/

n8n/                           # n8n workflows
```

**层次关系**：`packages/ashare-data` 是纯基础设施（数据采集/格式转换），`skills/ashare-assistant` 是 LLM 工作流，二者通过固定默认目录 `~/.ashare-assistant` 共享数据目录，不存在代码依赖倒置。

---

## 禁止事项

1. 禁止正则解析 HTML
2. 禁止硬编码敏感信息
3. 禁止 rsync 部署，只用 `cp` / `scp`

---

## Skills 目录结构与部署规则

**源码目录是唯一修改入口，部署目录是只读副本，不直接修改。**

```
skills/<skill-name>/          ← 源码（在此修改）
```

修改 skill 的正确流程：

```bash
# 1. 在源码目录修改
vim skills/<skill-name>/SKILL.md
```

**NO DEPLOY WITHOUT reading the relevant DEPLOYMENT.md first.**
部署目标因 skill 和平台不同而异，不得凭记忆套用任何硬编码命令。执行任何部署前，必须先读：
- 通用规则：[Deployment.md](Deployment.md)
- Skill 专属：`skills/<skill-name>/DEPLOYMENT.md`（如存在）

**禁止直接修改任何部署目录下的文件。**

---

## 部署

- 通用部署规则：详见 [Deployment.md](Deployment.md)
- ashare-assistant 完整部署指南：详见 [skills/ashare-assistant/DEPLOYMENT.md](skills/ashare-assistant/DEPLOYMENT.md)
- unified-memory 部署指南：详见 [skills/unified-memory/DEPLOYMENT.md](skills/unified-memory/DEPLOYMENT.md)
- 访问`tencent-vps`: `ssh root@tencent-vps`

---

## 测试环境

使用当前项目根目录下的uv虚拟环境`.venv`作为测试环境。

## 测试检查清单

```bash
# 运行 ashare-assistant 全部测试（含 ashare_data 模块测试）
python -m unittest discover -s skills/ashare-assistant/tests -p "test_*.py"

# 语法检查
python -m py_compile <file.py>
```

- [ ] 测试通过
- [ ] 无语法错误
- [ ] 类型注解完整
- [ ] Docstring 完整
- [ ] HTML 解析用 html.parser

---

立即使用`unified-memory`skill加载最近的20个topic
