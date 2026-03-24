# AGENTS.md - OpenclawSkills 开发指南

本项目开发了一系列满足 Openclaw 规范的 Skills（智能体技能），用于各种自动化和研究任务。

## IRON RULES

- NO SKILL DESIGN WITHOUT reading `Skills-Dev-Guide.md` and `Claude-Skill-Dev-Guide.md`.
- Every skill in `skills/` is independent and autonomous.
- 不要兼容性：正确的设计 > 兼容性。不得为了兼容而增加代码，也不得在注释中添加"兼容"相关表述。
- NO DEPLOY WITHOUT reading [Deployment.md](Deployment.md) first.

## 项目结构

```
skills/                        # Agent Skills（每个都是独立的）
├── agent-roundtable/          # 多智能体协作框架
├── bb-browser/                # 浏览器自动化工具
├── code-insight/              # 代码分析与洞察
├── explore-project/           # 项目探索工具
├── github-researcher/         # GitHub 趋势研究
├── markdown-to-anything/      # Markdown 转换工具
├── openclaw-browser/          # Openclaw 浏览器集成
├── openclaw-github-tracker/   # GitHub 项目情报
├── skill-review/              # Skill 审查与审计
├── unified-memory/            # 统一内存管理
└── website-operator/          # 网站操作工具

n8n/                           # n8n workflows
github_cache/                  # 研究用第三方仓库缓存（含 INDEX.md）
```

**原则**：每个 skill 在 `skills/` 下都是独立自治的，不依赖其他 skill。

## 如何运行项目

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行特定 skill 的测试
python -m unittest discover -s skills/<skill-name>/tests -p "test_*.py"

# 语法检查单个文件
python -m py_compile <file.py>
```

## 构建与测试

```bash
# 单元测试
python -m unittest discover -s skills/<skill-name>/tests -p "test_*.py"

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

## 研究与参考

开发新 Skill 时先搜索，避免重复造轮子：

```bash
gh search repos "<关键词>" --language python --sort stars
```

对关联度高的项目，clone 至 `github_cache/<主题>/` 并在 `github_cache/INDEX.md` 建立索引。

## 技术栈

- **语言**: Python 3.10+
- **HTML 解析**: html.parser（禁止正则解析 HTML）
- **测试**: unittest / pytest

## 代码风格

### 1. 导入排序

标准库 → 第三方 → 本地模块，组内按字母排序：

```python
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests
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
| 模块 | 小写下划线 | `my_module.py` |
| 类 | 大驼峰 | `MyClass` |
| 函数 | 小写下划线 | `my_function()` |
| 私有函数 | 前缀下划线 | `_private_func()` |
| 常量 | 全大写 | `MAX_COUNT` |

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

1. 禁止正则解析 HTML
2. 禁止硬编码敏感信息
3. 禁止 rsync 部署，只用 `cp` / `scp`
4. 禁止直接修改部署目录下的文件，只修改 `skills/<skill-name>/` 源码

## Skills 目录结构与部署规则

**源码目录是唯一修改入口，部署目录是只读副本，不直接修改。**

```
skills/<skill-name>/          ← 源码（在此修改）
```
