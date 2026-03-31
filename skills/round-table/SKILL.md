---
name: round-table
description: >-
  Multi-perspective roundtable debate using multiple AI runtimes (claude/codex/pi)
  with historical figure personas. Use when a topic benefits from adversarial
  multi-viewpoint discussion.
---

## Usage

<example>
User: 圆桌讨论 是否需要独立的 Agent 框架
Assistant: [启动 round-table，选角色，初始化 session，开始多轮讨论]
</example>

<example>
User: round-table 讨论下微服务 vs 单体架构的选型
Assistant: [启动 round-table，选取相关角色进行多视角辩论]
</example>

## CLI

```bash
# session 子命令
omp-round-table session init <topic>               # 创建 session
omp-round-table session end [--output-dir <path>]  # 结束，生成文档
omp-round-table session status                     # 查看 session 状态
omp-round-table session context <brief|detail>     # 获取背景上下文
omp-round-table session messages [msg-id]          # 获取消息记录

# round 子命令
omp-round-table round spawn [round-number]         # 并行启动参与者（轮次可省略，自动推断）
omp-round-table round collect                      # 收集参与者回复并写入 session
omp-round-table round watch [round] [-f] [-n lines] # 实时查看参与者输出
omp-round-table round attach                       # 连接 tmux session 直接观看

# 通用
omp-round-table post-message <role> <file> [opts]  # 追加消息
```

## Orchestrator SOP

你（当前会话的 AI agent）就是 orchestrator，负责协调整个圆桌讨论流程。

### 职责边界

| 决策类型 | 谁来做 | 说明 |
|----------|--------|------|
| 选哪些角色参与本次讨论 | **LLM 决策** | 读 roles.md，根据议题选 3-5 个 role ID |
| 每轮综述、引导问题、用户意图路由 | **LLM 决策** | 主持人职责，见下文 |
| 角色的 runtime / model / prompt 配置 | **CLI 执行** | 由 `session init --roles` 自动从 roles.md 读取，**禁止手动指定或覆盖** |
| 目录创建、meta.json、context.md、plan.md | **CLI 执行** | `session init` 自动完成，**禁止手动创建这些文件** |
| 每轮参与者的并行调用 | **CLI 执行** | `round run` / `round spawn` + `round collect` |

### 1. 读取角色库，选择参与者

加载 `references/roles.md`，根据议题选出 3-5 个 role ID。

> **LLM 决策点**：选哪些 ID。到此为止。runtime、model、prompt 由 CLI 处理。

### 2. 初始化（CLI 全权执行）

将选好的 role ID 传给 CLI，一条命令完成全部准备：

```bash
# --roles 自动拷贝预置 prompt、从 roles.md 读取 runtime/model 写入 meta.json
# --context 可传文本或文件路径，追加到 context.md
export ROUND_TABLE_SESSION=$(omp-round-table session init "<topic>" \
  --roles steve-jobs,dhh,alan-kay \
  --context "背景描述或文件路径")
```

`session init` 自动完成：创建目录、拷贝角色 prompt、写入 meta.json（含 runtime/model）、生成 context.md 和 plan.md。**不要手动创建或修改这些文件。**

- 展示参会者列表（从 `omp-round-table session status` 获取）
- 等待用户确认开始

### 3. 每轮循环（至少 3 轮）

> 详细流程见 `references/discussion-flow.md`

**a. 启动并收集**

```bash
omp-round-table round run
# spawn + wait + collect 一步完成
# 返回 JSON：每个参与者的 action 和 summary
```

**b. 综述**

根据 `round run` 返回的 JSON：
- 提炼本轮核心争议点
- 生成 ASCII 框架图（矩阵/光谱/因果环路/层级树）
- 提出下一轮引导问题
- post 综述到 session：

```bash
omp-round-table session post-message moderator <summary-file> \
  --round N --name "主持人" --action "综合" --summary "本轮一句话摘要"
```

**c. 用户参与（阻塞）**

展示摘要后询问用户：

- **继续**：接受引导问题，进入下一轮
- **结束**：进入结束阶段
- **深入**：围绕当前争议深挖
- **换人**：引入新角色

将用户回复 post 到 session：

```bash
omp-round-table session post-message user <user-input-file> \
  --round N --name "用户" --action "指令" --summary "用户意图摘要"
```

**轮次提醒：** 超过 5 轮时，在综述中提示"已进行 N 轮，建议考虑收敛"。不阻断。

### 4. 结束

```bash
omp-round-table session end --output-dir "$(pwd)/docs/round-table"
```

生成最终文档，包含：背景、各轮讨论记录、最终结论、未解决问题、行动建议。

## 主持人行为准则

- **理性之锚**：冷静客观，不偏向任何一方
- **挖深不铺广**：每轮只追一条最深的裂缝
- **求真 > 和谐**：鼓励尖锐但有建设性的交锋，拒绝表面共识
- **元认知**：在综述中暴露讨论的结构（假设、前提、推理链），不只复述内容

## 参会者行动标签

`陈述`、`质疑`、`补充`、`反驳`、`修正`、`综合`

每位参与者的发言必须：
1. 以行动标签开头
2. 回应前序发言（不许自说自话）
3. 以 `**简言之**：` 一句话压缩结尾
