# oh-my-superpowers

Pi Agent + Skills 开发套件。聚焦两件事：
1. **Skills** — 工具封装单元，构建 Agent 的基础
2. **Agents** — 有身份的角色，由 Skills 驱动

## IRON RULES

1. NO SKILL DESIGN WITHOUT reading `docs/specs/00_skills/README.md`.
2. NO AGENT DESIGN WITHOUT passing the Agent 身份审问（见 `docs/specs/01_agents/README.md`）。
3. 不要兼容性：正确的设计 > 兼容性。
4. 修复后必须运行相关测试或命令验证，未验证不能说"fixed"或"已修复"。
5. 用户要求讨论、分析、brainstorming 时，不要改代码。等用户明确要求实现后再动手。

## 架构（四层模型）

```
Tools/Scripts  ← CLI 化的可执行单元（bash/python/node）
Skills         ← SKILL.md + scripts/ + references/（告知 Agent WHEN/WHAT）
Agents         ← Pi frontmatter + system prompt（有身份的角色编排）
CLI            ← omp 命令（安装/卸载/测试）
```

详见 `docs/specs/02_framework/architecture.md`。

## 项目结构

```
skills/                   # Skill 单元（每个独立）
├── markdown-to-anything/ # Markdown 转 PDF/PNG 等格式
├── round-table/          # 多 AI runtime 圆桌讨论（claude/codex/pi 并行）
├── team/                 # 通用 tmux agent 编排（one-shot 驱动 claude/codex/pi）
└── <skill-name>/
    ├── SKILL.md          # 元数据 + CLI 命令文档（不写相对路径）
    ├── scripts/          # 脚本（CLI 封装的实现，不直接被模型调用）
    ├── references/       # 给 Agent 读的参考文档
    └── tests/            # T1 静态测试

agents/                   # Pi Agent 定义（每个独立）
├── skill-review.md       # Skill 质量审查官
└── <name>.md             # Pi frontmatter + system prompt

bin/
└── omp                   # 项目 CLI（install/remove/list/test）

docs/
├── specs/                # 项目级开发规范（不放设计文档）
│   ├── 00_skills/        # Skills 规范（格式、最佳实践、脚本设计等）
│   ├── 01_agents/        # Pi Agent 规范
│   └── 02_framework/     # 本框架规范（架构、安装、标准、评分表）
└── design/               # 设计文档（brainstorming 输出，YYYY-MM-DD-<name>-design.md）
```

## 安装

```bash
# Bootstrap（仅需一次，将项目安装到 ~/.oh-my-superpowers/）
./install.sh

# 局部安装（安装到当前项目目录的 .agents/skills/ 或 .pi/agents/）
omp install skill <name>
omp install agent <name>

# 全局安装（安装到 ~/.agents/skills/ 或 ~/.pi/agents/）
omp install skill <name> --global
omp install agent <name> --global
```

详见 `docs/specs/02_framework/installation.md`。

## 环境变量

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `OMP_HOME` | omp 安装路径 | `~/.oh-my-superpowers` |
| `OMP_DEFAULT_MODEL_PI` | Pi runtime 默认模型 | `openai-codex/gpt-5.4-mini` |

**默认模型原则**：所有需要调用 LLM 的组件（CLI、skill 脚本）统一通过 `OMP_DEFAULT_MODEL_PI` 环境变量获取默认模型，不在代码中硬编码模型名。优先级：`--model 命令行 > agents.json 显式声明 > OMP_DEFAULT_MODEL_PI > 硬编码 fallback`。

## 开发流程

```
BrainStorm → Plan → Code → Review → Test → Commit
```

- **Skill 开发**：先读 `docs/specs/00_skills/README.md`，再用 `brainstorming` skill
- **Agent 开发**：先读 `docs/specs/01_agents/README.md`，再用 `brainstorming` skill
- **Review**：用 `skill-review`（已有）/ `agent-review`（待建）
- **测试分层**：T1 静态检查 → T2 E2E（`pi -p`）→ T3 LLM-as-judge

## 完成标准

提交前必须全部通过：

- [ ] 相关测试通过（至少 T1 静态检查）
- [ ] 无语法错误（`py_compile` / `node --check`）
- [ ] SKILL.md 无相对路径脚本调用
- [ ] Python：类型注解完整（3.10+ 风格）、Docstring 完整（Google 风格）
- [ ] 无硬编码敏感信息

## PR 期望

- **标题**：`feat:` / `fix:` / `docs:` / `refactor:` 前缀，简短描述
- **范围**：一个 PR 对应一个连贯的工作单元
- **测试**：新功能附带测试，Bug 修复附带复现用例
- **禁止**：调试代码、注释掉的代码块、TODO 遗留

## 技术栈

| 层 | 技术 |
|----|------|
| 脚本 | Bash（简单任务）/ Python 3.10+（数据处理）/ Node.js or Bun（浏览器/复杂 CLI）|
| 测试 | unittest/pytest（T1）/ `pi -p` 或 `claude -p`（T2 E2E）/ LLM-as-judge（T3）|
| 包管理 | uv（Python）/ npm or bun（Node）|
| Agent 运行时 | Pi（核心）/ Claude Code（开发辅助）|
| 安装 | symlink via omp |

## 代码风格（Python）

### 导入排序

标准库 → 第三方 → 本地模块，组内按字母排序：

```python
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests
```

### 类型注解

- Python 3.10+ 联合类型：`str | None`（非 `Optional[str]`）
- 复杂类型用 type alias：`Post = dict[str, Any]`

### 命名

| 类型 | 规则 | 示例 |
|------|------|------|
| 模块 | 小写下划线 | `my_module.py` |
| 类 | 大驼峰 | `MyClass` |
| 函数 | 小写下划线 | `my_function()` |
| 私有函数 | 前缀下划线 | `_private_func()` |
| 常量 | 全大写 | `MAX_COUNT` |

### Docstring（Google 风格）

```python
def fetch_data(count: int = 20) -> list[dict]:
    """获取数据。

    Args:
        count: 返回数量。

    Returns:
        数据列表，出错时返回空列表。
    """
```

### 错误处理

- 数据获取函数：捕获异常后返回空列表/字典，不抛出
- 用 `logger.exception()` 记录错误
- 网络请求设置 timeout（默认 15 秒）

### 并发

```python
with ThreadPoolExecutor(max_workers=min(8, len(urls))) as pool:
    contents = list(pool.map(_fetch_detail, urls))
```

## 禁止事项

1. 禁止在 SKILL.md 中写相对路径脚本调用（如 `bash scripts/foo.sh`）
2. 禁止正则解析 HTML（使用 html.parser）
3. 禁止硬编码敏感信息
4. 禁止直接修改 `~/.oh-my-superpowers/` 下的文件，只修改源码目录

## Tool CLI Architecture

两层结构：`omp` 是唯一 PATH 入口，通过目录名路由到 `cli/<tool>/main.py`。

| 文件 | 开发时位置 | 安装后位置 | 作用 |
|------|-----------|-----------|------|
| `omp`（唯一产品入口） | `bin/omp` | `~/.local/bin/omp` | 统一 CLI 入口 |
| 工具 CLI 模块 | `cli/<tool>/main.py` | `$OMP_HOME/cli/<tool>/main.py` | typer app，定义子命令接口 |
| 实现脚本 | `skills/<tool>/scripts/` | `$OMP_HOME/skills/<tool>/scripts/` | 业务逻辑实现 |

**关键规则：**

- `omp` 是唯一进入 PATH 的命令，没有 `omp-xxx` 中间层
- `omp <tool>` 自动路由到 `$OMP_HOME/cli/<tool>/main.py`（通过 `uv run`）
- `cli/<tool>/main.py` 使用 typer + PEP 723 inline dependencies
- 实现脚本通过 `$OMP_HOME` 引用，禁止相对路径
- SKILL.md 中只写 `omp <tool> <subcommand> [args]`，不写路径
- 详见 [CLI 开发规范](docs/specs/02_framework/cli-development-guide.md)

## 规范参考

- [Skills 规范](docs/specs/00_skills/README.md)：Skills 开发核心原则 + 详细文档索引
- [Pi Agents 规范](docs/specs/01_agents/README.md)：Agent 身份审问 + Pi 框架索引
- [Framework 规范](docs/specs/02_framework/README.md)：架构、安装设计索引
- [Hooks 开发指南](docs/specs/02_framework/hooks.md)：生命周期事件、输出协议、设计原则
- [CLI 开发规范](docs/specs/02_framework/cli-development-guide.md)：命令结构、--help 规范、工具模块模板、输出设计
- [CLI Checklist](docs/specs/02_framework/cli-checklist.md)：新增/修改 CLI 时逐项确认
- [CDP 开发指南](docs/specs/00_skills/cdp-development-guide.md)：web-operator CDP 架构、开发模式、踩坑经验

## 开源项目参考

- [SkillsIndex](~/Github/SkillsIndex.md)：当用户需要一个新的skills，首先看看优秀开源项目中是否已经存在？再跟客户讨论需求是否已经被开源项目满足
- [Pi Coding Agent](~/Github/pi-mono): Pi coding agent的官方代码仓库
- [Obsidian](~/Obsidian/): 用户的`Obsidian`笔记，经常看看笔记目录

## Deep Research

如果一个问题需要网络搜索/社交媒体等更多出道的输入，请使用`omp run researcher`命令，比如：

```bash
omp run researcher -m litellm-local/qwen3.5-27b --mode stream "请快速研究下Claude Code的记忆机制"
```
