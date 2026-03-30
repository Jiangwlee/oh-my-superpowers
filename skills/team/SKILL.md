---
name: team
description: >-
  Use when you need to dispatch a task to another AI runtime (claude/codex/pi)
  via tmux. Provides one-shot execution: spawn → wait → return output.
  Do NOT use for interactive/multi-turn sessions.
---

## Quick Reference

```bash
# One-shot 执行任务
omp-team run <runtime> "<prompt>"
omp-team run <runtime> --prompt-file <path>

# 查询 tmux session 状态
omp-team status [session-name]

# 清理 ANSI 转义码
omp-team clean <file>
```

### `run` 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `<runtime>` | 目标运行时：`claude` / `codex` / `pi` | 必填 |
| `"<prompt>"` | 发送给 worker 的任务指令 | 与 `--prompt-file` 二选一 |
| `--prompt-file <path>` | 从文件读取 prompt | 与内联 prompt 二选一 |
| `--model <model>` | 指定模型 | runtime 默认模型 |
| `--timeout <seconds>` | 超时时间 | 300 |
| `--output-file <path>` | 将 worker 输出写入文件 | 无（输出到 stdout） |
| `--cwd <path>` | worker 工作目录 | 当前目录 |

### 输出协议

| 通道 | 内容 |
|------|------|
| stdout | clean 后的 worker 输出（无 ANSI 转义） |
| stderr | team 状态日志（启动、等待、完成等） |
| 退出码 0 | 执行成功 |
| 退出码 1 | 执行错误 |
| 退出码 124 | 超时 |

### 示例

```bash
# 让 codex 实现一个函数
omp-team run codex "在 src/utils.py 中实现 parse_config 函数，读取 YAML 配置文件并返回 dict" \
  --cwd /path/to/project --timeout 180

# 让 claude 做代码审查（通过 prompt 文件传递代码内容）
omp-team run claude --prompt-file /tmp/review-prompt.md \
  --output-file /tmp/review.md

# 从 prompt 文件执行
omp-team run pi --prompt-file /tmp/task-prompt.md --timeout 60

# 查看运行状态
omp-team status

# 清理输出文件中的 ANSI 转义
omp-team clean /tmp/raw-output.txt
```

## Runtime 选择指南

| Runtime | 适用任务 | 特点 |
|---------|---------|------|
| `codex` | 编码实现、文件修改、重构 | YOLO 模式，不需确认，直接执行文件操作 |
| `claude` | 设计、review、复杂推理、文档撰写 | 深度思考，适合需要判断力的任务 |
| `pi` | 轻量任务、快速验证、格式转换 | 速度快，成本低，适合简单指令 |

**选择原则：**
- 需要改代码 → `codex`
- 需要思考/判断 → `claude`
- 简单/快速任务 → `pi`

## 场景编排索引

> 以下场景文档提供完整 SOP，包含具体的 omp-team 调用序列。

| 场景 | 文档 | 说明 |
|------|------|------|
| 编码 + 审查 | `references/scenarios/code-and-review.md` | Pipeline：codex 实现 → claude 审查 |
| 正反辩论 | `references/scenarios/debate.md` | Fan-out/Fan-in：多视角并行 → 聚合结论 |
| 多轮讨论 | `references/patterns/discussion.md` | Discussion：多 agent 共享上下文逐轮收敛 |

## Prompt 框架索引

> 下发给 worker 的 prompt 质量决定 one-shot 成功率。使用以下模板，填入 `{placeholder}` 变量。

| 模板 | 文档 | 用途 |
|------|------|------|
| 编码任务 | `references/prompts/coding-task.md` | 分配编码实现任务 |
| 代码审查 | `references/prompts/code-review.md` | 分配代码审查任务 |
| 角色激活 | `references/prompts/role-activation.md` | 通用角色定义与行为约束 |

## Prompt 规范

One-shot 执行没有多轮修正机会，prompt 必须一次到位：

1. **上下文自包含** — Worker 没有历史记忆。所有必要的背景信息、代码片段、文件内容必须包含在 prompt 中。
2. **明确输出格式** — 告诉 worker 输出什么格式（markdown / JSON / 代码文件），不要让 worker 猜。
3. **指定工作目录** — 通过 `--cwd` 指定，并在 prompt 中说明项目结构和目标文件位置。
4. **使用模板** — 优先使用 `references/prompts/` 中的模板，填入 `{placeholder}` 变量，确保结构完整。
5. **单一职责** — 一个 prompt 只做一件事。复杂任务拆成多步，用 pipeline 模式串联。

## 并发编排

Orchestrator（你）负责并发控制。omp-team 本身是同步阻塞的，并发通过 shell 后台任务实现：

```bash
# 并行启动多个 worker
omp-team run claude "从安全角度审查..." --output-file /tmp/security.md &
omp-team run claude "从性能角度审查..." --output-file /tmp/perf.md &
omp-team run claude "从可维护性角度审查..." --output-file /tmp/maintain.md &
wait

# 收集结果
cat /tmp/security.md /tmp/perf.md /tmp/maintain.md
```

> 并发编排模式详见 `references/patterns/` 下的模式文档（Pipeline / Fan-out/Fan-in / Discussion / Batch）。
> 完整模式索引见 `references/README.md`。
