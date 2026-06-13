# CLI Development Guide

CLI 开发规范。适用于所有 `omp` 子命令和 `cli/<tool>/main.py` 工具模块。

> **决策背景**：2026-04-07 圆桌讨论决议。详见 `docs/round-table/` 对应记录。

---

## 核心原则

### 1. 统一入口

`omp` 是唯一的产品界面。用户只需记住一个命令。

```
omp <tool> <action> [args]       # 工具调用
omp install / remove / list ...  # 项目管理
omp run <agent> [prompt]         # 运行 agent
```

### 2. `--help` 是一等公民

每个命令和子命令的 `--help` 输出是该命令用法的**权威描述**（source of truth），同时面向 LLM agent 和人类开发者。

SKILL.md 引导 LLM 使用 `--help`，而不是在 SKILL.md 中穷举参数：

```markdown
# SKILL.md 中的正确写法
不确定参数时，先运行 `omp web-operator search --help` 查看完整用法。

# 错误写法（在 SKILL.md 中穷举参数）
--limit N    限制返回数量（默认 10）
--format F   输出格式（json|csv）
```

### 3. SKILL.md = Workflow SOP

SKILL.md 负责描述**业务场景下如何组合多个 CLI 命令完成任务**，给出一般性用法示例。不负责描述单个命令的完整参数。

分层关系：

```
omp <tool> --help  → 单个工具的完整 API（权威、自描述）
SKILL.md           → 业务场景 SOP（何时用、怎么组合、示例）
```

---

## 架构

### 两层结构（无中间分发器）

```
omp                              # 唯一入口（~/.local/bin/omp）
 │
 ├── install / remove / list ... # 内置命令（项目管理）
 ├── run <agent> [prompt]        # 内置命令（运行 agent）
 ├── test <skill>                # 内置命令（测试）
 │
 └── <tool> <subcommand> [args]  # 工具路由 → cli/<tool>/main.py
     │
     └── cli/<tool>/main.py      # 工具入口（typer/argparse）
```

`omp <tool>` 通过 tool 名匹配 `cli/` 下的目录名，调用 `cli/<tool>/main.py`。没有 `bin/omp-xxx` 中间层。

### 文件位置

| 文件 | 开发时 | 安装后 |
|------|--------|--------|
| `omp`（唯一产品入口） | `bin/omp` | `~/.local/bin/omp` |
| 工具 CLI 模块 | `cli/<tool>/main.py` | `$OMP_HOME/cli/<tool>/main.py` |
| 实现脚本 | `skills/<tool>/scripts/` | `$OMP_HOME/skills/<tool>/scripts/` |

`omp` 是唯一进入用户 PATH 的命令。工具 CLI 模块和实现脚本都留在 `$OMP_HOME` 内部。

### 路由机制

`omp` 收到 `omp <tool> ...` 时：

1. 在 `$OMP_HOME/cli/<tool>/` 目录下查找 `main.py`
2. 找到 → `exec uv run $OMP_HOME/cli/<tool>/main.py <剩余参数>`
3. 未找到 → 报错 `unknown tool '<tool>'`，提示 `omp --help`

使用 `uv run` 确保 `main.py` 的第三方依赖（typer、rich 等）通过 PEP 723 inline metadata 自动解析，无需预装。

例外：`omp serve` 是高频本地工作台入口，顶层路由直接用当前 Python 执行 `cli/serve/main.py`，避免二次 `uv run` 启动开销。该例外只适用于已确认依赖由顶层运行环境满足的工具。

### 自动路由注册

`omp --help` 应动态列出所有已安装的工具。实现方式：启动时扫描 `$OMP_HOME/cli/` 下含 `main.py` 的子目录，提取工具名和描述，注册为子命令组。

### 环境变量

工具 CLI 启动时自动加载 `$OMP_HOME/.env`（如果存在），用于注入配置：

```bash
# ~/.oh-my-superpowers/.env
CDP_PORT=9222
DEFAULT_SEARCH_LIMIT=10
```

加载优先级：`CLI 参数 > 环境变量（.env）> 代码默认值`

---

## 命名约定

| 层级 | 规则 | 示例 |
|------|------|------|
| 顶层命令 | `omp` 固定 | `omp` |
| 工具名 | 小写连字符，对应 `cli/` 下目录名 | `web-operator`, `insight`, `deep-research` |
| noun（可选） | 小写连字符，资源名词 | `taoguba`, `kdocs`, `session` |
| verb | 小写连字符，动作动词 | `search`, `jinghua`, `init` |
| flag | `--long-flag` 小写连字符 | `--limit`, `--output-dir` |
| 位置参数 | 按重要性排序，必填在前 | `<query> [limit]` |

子命令层级最多三层：`omp <tool> <noun> <verb>`。

```bash
omp insight capture                    # 工具 + verb（2 层）
omp web-operator taoguba jinghua       # 工具 + noun + verb（3 层）
omp round-table session init           # 工具 + noun + verb（3 层）
```

---

## `--help` 输出规范

### 必须包含

1. **用法行**（Usage）：`omp <tool> <subcommand> [OPTIONS] <REQUIRED_ARGS> [OPTIONAL_ARGS]`
2. **一句话描述**：说明这个命令做什么
3. **子命令/参数列表**：每项一行，含类型和默认值
4. **至少一个 Example**：展示最常用的调用方式

### 格式模板

```
usage: omp <tool> <subcommand> [OPTIONS] <ARGS>

<一句话描述>

Commands:
  sub1        描述
  sub2        描述

Options:
  --flag VALUE    描述（default: 默认值）
  --verbose       描述

Examples:
  omp <tool> sub1 "hello"
  omp <tool> sub1 --flag value "hello"
```

### 质量标准

- **简洁**：--help 进入 LLM 上下文窗口，越短越好
- **机器友好**：参数名、类型、默认值一目了然
- **人类友好**：Example 可直接复制粘贴运行
- **错误引导**：参数错误时输出 usage 提示，指向 `--help`

---

## 工具 CLI 模块开发规范

### 目录结构

```
cli/
├── insight/
│   └── main.py          # typer app，实现 capture/recall/evaluate/list/...
├── web-operator/
│   └── main.py          # typer app，实现 search/read-url/open-post/...
├── deep-research/
│   └── main.py          # typer app，实现 init/...
└── <tool-name>/
    └── main.py          # 统一入口
```

### main.py 模板

```python
#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp <tool-name> — 一句话描述。"""

import os
import subprocess
import sys
from pathlib import Path

import typer

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))

# 加载 .env
_env_file = OMP_HOME / ".env"
if _env_file.is_file():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

app = typer.Typer(
    name="<tool-name>",
    help="一句话描述",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def sub1(
    query: str = typer.Argument(..., help="搜索关键词"),
    limit: int = typer.Option(10, "--limit", "-l", help="返回数量"),
) -> None:
    """子命令描述。"""
    # 调用实现脚本或直接实现
    script = OMP_HOME / "skills" / "<tool-name>" / "scripts" / "sub1.sh"
    sys.exit(subprocess.call(["bash", str(script), query, str(limit)]))


if __name__ == "__main__":
    app()
```

### 分层原则

```
bin/omp                          # 入口层：路由分发
cli/<tool>/main.py               # CLI 层：参数定义 + action 路由 + 输出格式化
skills/<tool>/scripts/<module>   # 业务层：实现逻辑（纯函数或独立脚本）
```

- **main.py 职责单一**：参数解析 + 调用业务函数/脚本 + 序列化输出。不含业务逻辑。
- **业务层独立**：实现脚本不依赖 typer、不直接读写 argv。接受参数，返回/输出结果。

### 关键规则

1. **统一入口**：每个工具只有一个 `main.py`，用 typer 管理所有子命令
2. **`$OMP_HOME` 引用**：通过 `OMP_HOME` 定位实现脚本，禁止相对路径
3. **自动加载 .env**：启动时读取 `$OMP_HOME/.env`，`os.environ.setdefault` 不覆盖已有值
4. **`--help` 由 typer 自动生成**：只需写好 docstring 和参数 help 字符串
5. **subprocess 调用外部脚本**：bash/node 脚本通过 subprocess 调用，保持进程退出码
6. **`--version`**：`omp --version` 输出版本号（格式 `omp x.y.z`）

### 混合语言工具

部分工具的实现脚本是 bash 或 node（如 web-operator 的 cdp.mjs、site scripts）。`main.py` 作为统一入口，内部通过 `subprocess` 分发：

```python
@app.command()
def search(
    site: str = typer.Argument(..., help="搜索平台"),
    query: str = typer.Argument(..., help="搜索关键词"),
    limit: int = typer.Option(10, "--limit", "-l", help="返回数量"),
) -> None:
    """搜索指定平台。"""
    script = OMP_HOME / "skills" / "web-operator" / "scripts" / "sites" / site / "search.sh"
    if not script.is_file():
        typer.echo(f"error: unknown search site '{site}'", err=True)
        raise typer.Exit(2)
    sys.exit(subprocess.call(["bash", str(script), query, str(limit)]))
```

---

## 实现脚本开发规范

### 输出设计

| 通道 | 用途 | 格式 |
|------|------|------|
| stdout | 业务结果 | JSON 单行（不 pretty-print，管道友好） |
| stderr | 进度、警告、调试 | 自由文本 |
| stdin | 结构化输入（pipeline 场景） | JSON |

- **JSON 单行**：stdout 输出的 JSON 不得 pretty-print（`json.dumps` 不传 indent），确保管道可组合
- **错误要有用**：说明错了什么、期望什么、怎么修
- **大小可控**：默认输出有上限，提供 `--limit` / `--offset`

### 管道组合性

前一命令的 stdout 可直接 pipe 到下一命令的 stdin：

```bash
omp insight recall "AI agents" | jq '.[] | .content'
omp web-operator search google "query" | omp web-operator read-url --json
```

设计命令时考虑：输出能否被下游消费？输入能否来自上游？

### 参数设计

| 原则 | 做法 |
|------|------|
| 必填用位置参数 | `omp web-operator search google "query"` |
| 可选用 flag | `--limit 10`, `--format json` |
| 有合理默认值 | 不传 `--limit` 时使用内置默认 |
| 禁止交互式输入 | Agent 环境无 TTY，所有输入通过参数/stdin |

### 幂等与安全

- **幂等优先**：`create-if-not-exists` 优于 `create-and-fail`
- **破坏性操作**：需要 `--force` 或 `--confirm` 显式确认
- **dry-run**：有副作用的命令提供 `--dry-run` 预览

### 退出码

| 退出码 | 含义 | 示例场景 |
|--------|------|---------|
| 0 | 成功 | 正常完成 |
| 1 | 业务失败 | 校验不通过、API 返回错误 |
| 2 | 用法错误 | 未知命令、缺参数、stdin 非法 JSON |
| 4 | 权限/环境缺失 | 必要环境变量未设置、认证过期 |

### 错误处理链

```
业务层（scripts/）抛出异常
    → CLI 层（main.py）catch
        → stderr 输出错误信息（错了什么、期望什么、怎么修）
        → 设置退出码（1=业务失败，2=用法错误，4=权限缺失）
```

- 环境变量校验：需要环境变量的子命令，在入口处立即校验，缺失则 stderr 报错并 exit 4
- 业务错误：业务层抛异常，CLI 层 catch 后输出到 stderr 并 exit 1
- **禁止吞错误**：不允许 catch 后静默继续执行

---

## 与 SKILL.md 的协作

### SKILL.md 中引用 CLI 的正确方式

```markdown
## CLI

### 搜索
omp web-operator search google <query> [limit]

### 读取 URL
omp web-operator read-url <url> [--limit N] [--json]

> 完整参数说明：运行 `omp web-operator search --help`
```

### SKILL.md 不该做的事

- 穷举所有参数和 flag 的详细说明（交给 --help）
- 描述脚本内部实现（交给代码注释）
- 写相对路径脚本调用（只写 `omp <tool>` 命令）

---

## 新增工具 CLI 的流程

1. **确认归属**：新命令属于已有 tool 还是需要创建新 tool？
2. **创建目录**：`cli/<tool-name>/main.py`（新 tool 时）
3. **写 --help 先**：先定义命令接口（typer 参数 + docstring），再写实现
4. **实现逻辑**：在 `main.py` 中直接实现，或在 `skills/<tool>/scripts/` 下写脚本
5. **注册路由**：确保 `cli/<tool-name>/` 目录名与 `omp <tool-name>` 一致（自动路由）
6. **更新 SKILL.md**：在对应 SKILL.md 中添加用法示例（引用 --help，不穷举）
7. **检查 checklist**：运行 CLI Checklist 逐项确认
