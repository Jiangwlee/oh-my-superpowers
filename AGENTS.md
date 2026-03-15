# AGENTS.md - OpenclawSkills 开发指南

本项目开发了一系列满足 Openclaw 规范的 Skills（智能体技能），主要用于金融数据抓取、分析与研究。

## IRON RULES

- NO SKILL DESIGN WITHOUT reading `Skills-Dev-Guide.md` and `Claude-Skill-Dev-Guide.md`.
- Every skill in `skills/` is independent and autonomous.
- 不要兼容性：正确的设计 > 兼容性。不得为了兼容而增加代码，也不得在注释中添加"兼容"相关表述。
- NO DEPLOY WITHOUT reading [Deployment.md](Deployment.md) first.

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

apps/
└── ashare-platform/           # A股平台应用（backend FastAPI）
    └── backend/
        ├── app/pipelines/     # 数据处理流水线
        ├── app/services/      # 语义增强等服务
        └── tests/

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
│   ├── tests/
│   ├── references/
│   ├── evolution/
│   ├── strategy/
│   └── SKILL.md
├── agent-roundtable/
├── bb-browser/
├── code-insight/
├── explore-project/
├── github-researcher/
├── markdown-to-anything/
├── openclaw-github-tracker/
├── skill-review/
└── unified-memory/

n8n/                           # n8n workflows
github_cache/                  # 研究用第三方仓库缓存（含 INDEX.md）
```

**层次关系**：`packages/ashare-data` 是纯基础设施（数据采集/格式转换），`skills/ashare-assistant` 是 LLM 工作流，二者通过固定默认目录 `~/.ashare-assistant` 共享数据目录，不存在代码依赖倒置。

## 如何运行项目

```bash
# 激活虚拟环境（项目根目录的 uv 环境）
source .venv/bin/activate

# 安装 ashare-data 包（开发模式）
uv pip install -e packages/ashare-data

# 运行 ashare-assistant 测试
python -m unittest discover -s skills/ashare-assistant/tests -p "test_*.py"

# 运行 ashare-platform 测试
python -m pytest apps/ashare-platform/backend/tests/

# 语法检查单个文件
python -m py_compile <file.py>
```

## 构建与测试

```bash
# 单元测试（ashare-assistant）
python -m unittest discover -s skills/ashare-assistant/tests -p "test_*.py"

# 单元测试（ashare-platform）
python -m pytest apps/ashare-platform/backend/tests/ -v

# 语法检查
python -m py_compile <file.py>
```

## 完成标准

提交前必须全部通过：

- [ ] 相关测试通过（unittest 或 pytest）
- [ ] 无语法错误（`py_compile`）
- [ ] 类型注解完整（Python 3.10+ 风格）
- [ ] Docstring 完整（Google 风格）
- [ ] 无硬编码敏感信息

## PR 期望

- **标题**：`feat:` / `fix:` / `docs:` / `refactor:` 前缀，简短描述
- **范围**：一个 PR 对应一个连贯的工作单元
- **测试**：新功能附带测试，Bug 修复附带复现用例
- **禁止**：不得在 PR 中包含调试代码、注释掉的代码块、TODO 遗留

## 规范参考

- [Agent Skills](https://github.com/agentskills/agentskills): Openclaw 遵从的 Skills 规范
- [Tools](https://docs.openclaw.ai/tools/browser): Openclaw 内置工具
- [Skills Development Guide](Skills-Dev-Guide.md)：Skills开发经验，当发现一种有效的Skill编写模式时，可追加到此文件中。
- [Claude Skill Development Guide](Claude-Skill-Dev-Guide.md)：Claude官方Skill开发手册。
- [File Header Spec](File-Header-Spec.md)：文件头规范，要求前 20 行让 AI 理解文件全貌。所有 Markdown 和 Python 文件必须遵循。
- [JVQuant 平台参考](docs/jvquant-reference.md)：JVQuant 券商交易接口文档，含 API 规格、计费标准、费用优化策略。

## 研究与参考

开发新 Skill 时先搜索，避免重复造轮子：

```bash
gh search repos "<关键词>" --language python --sort stars
```

对关联度高的项目，clone 至 `github_cache/<主题>/` 并在 `github_cache/INDEX.md` 建立索引。

## 技术栈

- **语言**: Python 3.10+
- **HTTP 客户端**: Scrapling Fetcher（基于 curl_cffi，TLS 指纹模拟）
- **HTML 解析**: Scrapling Selector（CSS/XPath 选择器，lxml 后端）
- **测试**: unittest / pytest

**Scrapling 用法**：
- `Fetcher.get(url)` 返回 Response 对象（继承自 Selector）
- Response 支持链式调用 `.css()/.xpath()/.re()` 提取结构化数据
- 核心模块：`ashare_data.core.scraper` 封装 Scrapling API

## 代码风格

### 1. 导入排序

标准库 → 第三方 → 本地模块，组内按字母排序：

```python
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import scrapling
from ashare_data import fetchers
```

### 2. 类型注解

- Python 3.10+ 联合类型: `str | None`（非 `Optional[str]`）
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

### 4. Docstring（Google 风格）

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

- 数据获取函数：捕获异常后返回空列表/字典，不抛出
- 用 `logger.exception()` 记录错误
- 网络请求设置 timeout（默认 15 秒）

```python
def fetch_data(url: str) -> list[dict]:
    try:
        return data
    except Exception as e:
        logger.exception("fetch_data 出错: %s", e)
        return []
```

### 6. 并发

```python
with ThreadPoolExecutor(max_workers=min(8, len(urls))) as pool:
    contents = list(pool.map(_fetch_detail, urls))
```

### 7. 日志

```python
logger = logging.getLogger(__name__)
# 使用 logger.debug() / logger.warning() / logger.exception()
```

## 禁止事项

1. 禁止正则解析 HTML——使用 Scrapling Selector
2. 禁止手写 `urllib.request` 或 `html.parser`——使用 Scrapling
3. 禁止硬编码敏感信息
4. 禁止 rsync 部署，只用 `cp` / `scp`
5. 禁止直接修改部署目录下的文件，只修改 `skills/<skill-name>/` 源码

## Skills 目录结构与部署规则

**源码目录是唯一修改入口，部署目录是只读副本，不直接修改。**

```
skills/<skill-name>/          ← 源码（在此修改）
```

部署前必须先读：
- 通用规则：[Deployment.md](Deployment.md)
- Skill 专属：`skills/<skill-name>/DEPLOYMENT.md`（如存在）

部署目标：
- 通用部署规则：详见 [Deployment.md](Deployment.md)
- ashare-assistant：详见 [skills/ashare-assistant/DEPLOYMENT.md](skills/ashare-assistant/DEPLOYMENT.md)
- unified-memory：详见 [skills/unified-memory/DEPLOYMENT.md](skills/unified-memory/DEPLOYMENT.md)
- 访问 Tencent VPS：`ssh root@tencent-vps`
