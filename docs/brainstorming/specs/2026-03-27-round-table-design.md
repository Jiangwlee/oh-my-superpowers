# Round Table
#
# 用途：多 AI runtime 圆桌讨论 skill，通过 claude/codex/pi 并行运行不同模型
#       模拟多视角结构化辩论，用于软件开发与 AI Agent 设计的需求、架构与设计讨论

> 让多个 AI agent 以历史名人身份、通过不同 runtime 和模型进行多轮圆桌讨论，解决单模型单上下文讨论缺乏多样性的问题。

## 目录

- [设计方案](#设计方案)
  - [背景与目标](#背景与目标)
  - [架构](#架构)
  - [CLI 设计](#cli-设计)
  - [数据模型](#数据模型)
  - [执行流程](#执行流程)
  - [角色系统](#角色系统)
  - [Prompt 注入策略](#prompt-注入策略)
  - [最终输出文档](#最终输出文档)
  - [关键决策](#关键决策)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 背景与目标

**痛点：** 现有圆桌讨论 skill（如 ljg-roundtable）在同一上下文用同一模型扮演所有角色，导致观点趋同、多样性不足。模型的"思维风格"受限于单一 runtime 的 system prompt。

**核心洞察：** claude code / codex / pi 各自的 system prompt 和工具链构成了架构级的"认知框架"差异——这不是用户 prompt 能模拟的。混合 runtime 是真正的多样性来源。

**成功标准：**
1. 3+ 个不同 runtime/model 的 AI agent 并行参与讨论
2. 每轮讨论有结构化的上下文传递，参与者能回应前序发言
3. 用户能在每轮后参与、引导讨论方向
4. 讨论结束后生成完整的决策文档

### 架构

#### 四层映射

| 层 | 实现 |
|----|------|
| **Tools/Scripts** | `scripts/session.sh`（JSONL 读写 + CLI 子命令）、`scripts/spawn.sh`（tmux 启动参与者） |
| **Skill** | `SKILL.md`（触发 + 高层 SOP）、`references/`（角色库、prompt 模板、详细流程） |
| **Agent** | 不需要独立 agent 文件——orchestrator 就是当前会话的 claude/codex/pi，其行为由 SKILL.md SOP + references/discussion-flow.md 驱动 |
| **CLI** | `bin/omp-round-table`（dispatcher，委托到 scripts/） |

#### 组件关系

```
Orchestrator（当前会话的 claude/codex/pi）
  │
  ├── omp-round-table start        → scripts/session.sh init
  ├── omp-round-table get-context   → scripts/session.sh get-context
  ├── omp-round-table get-messages  → scripts/session.sh get-messages
  ├── omp-round-table post-message  → scripts/session.sh post-message
  ├── omp-round-table end           → scripts/session.sh end
  ├── omp-round-table spawn          → scripts/spawn.sh（CLI 化，orchestrator 通过命令调用）
  │
       ├── tmux: claude -p "..." --model opus > response.md
       ├── tmux: codex -p "..." --model gpt-5.4 > response.md
       └── tmux: pi -p "..." --model qwen3.5-27b > response.md
```

### CLI 设计

```bash
omp-round-table start <topic>                      # 创建 session，初始化角色和上下文
omp-round-table get-context <brief|detail>          # 获取背景上下文（brief: 摘要; detail: 完整）
omp-round-table get-messages                        # 历史摘要 + 最近一轮完整消息（含 msg-id）
omp-round-table get-messages <msg-id>               # 获取指定消息详情
omp-round-table post-message <role> <content-file>  # 追加消息到 session
omp-round-table spawn <round-number>                # 并行启动所有参与者（tmux + stdout 重定向）
omp-round-table end                                 # 结束讨论，生成最终文档
```

#### get-messages 输出格式

**无参数（默认）：**

```
=== 历史摘要 ===
[Round 1] 围绕"是否需要独立 Agent 框架"展开定义，Jobs 主张体验优先，
Torvalds 认为过度抽象，Musk 提出第一性原理分析...

=== Round 2（最近一轮）===
[msg-005] 【Steve Jobs】【质疑】：框架的复杂度本身就是...
[msg-006] 【Elon Musk】【反驳】：如果从第一性原理出发...
[msg-007] 【Linus Torvalds】【补充】：看看实际 benchmark...
[msg-008] 【Andrej Karpathy】【陈述】：从 scaling law 角度...
[msg-009] 【Alan Kay】【综合】：回到 Smalltalk 的设计...
```

**指定 msg-id：**

```
[msg-006] Round 2 | Elon Musk | 反驳
---
如果从第一性原理出发，我们需要问的不是"要不要框架"...
（完整内容）
```

### 数据模型

#### Session 目录结构

```
~/.local/share/oh-my-superpowers/round-table/
  └── <session-id>/                  # 时间戳格式: 20260327T143000
      ├── meta.json                  # session 元信息
      ├── context.md                 # 问题背景（静态，初始化时写入）
      ├── plan.md                    # 讨论计划（静态，初始化时写入）
      ├── messages.jsonl             # 所有消息记录（追加写入）
      ├── participants/              # 各角色完整 prompt（落盘可观察）
      │   ├── steve-jobs.md
      │   ├── elon-musk.md
      │   └── ...
      └── responses/                 # 临时：每轮 stdout 输出
          └── round-1-steve-jobs.md
```

#### meta.json

```json
{
  "session_id": "20260327T143000",
  "topic": "是否需要独立 Agent 框架",
  "created_at": "2026-03-27T14:30:00",
  "status": "active",
  "current_round": 2,
  "participants": [
    {
      "id": "steve-jobs",
      "name": "Steve Jobs",
      "role": "产品视觉家",
      "runtime": "claude",
      "model": "opus"
    }
  ]
}
```

#### messages.jsonl

每行一条消息，追加写入：

```json
{"msg_id": "msg-001", "round": 1, "role": "steve-jobs", "name": "Steve Jobs", "action": "陈述", "summary": "一句话摘要", "content": "完整内容...", "timestamp": "2026-03-27T14:31:00"}
{"msg_id": "msg-002", "round": 1, "role": "moderator", "name": "主持人", "action": "综合", "summary": "本轮摘要", "content": "核心争议点在于...", "timestamp": "2026-03-27T14:35:00"}
{"msg_id": "msg-003", "round": 1, "role": "user", "name": "用户", "action": "指令", "summary": "继续", "content": "我觉得 Jobs 说的有道理，但...", "timestamp": "2026-03-27T14:36:00"}
```

#### 摘要生成链路

`get-messages`（无参数）输出的"历史摘要"由以下链路生成：

1. **每轮结束时**，orchestrator 生成本轮综述，通过 `post-message moderator <summary-file>` 写入 messages.jsonl，其中 `action` 为 `"综合"`，`summary` 字段为一句话摘要
2. **`get-messages` 执行时**，`session.sh` 从 messages.jsonl 中过滤所有 `role == "moderator" && action == "综合"` 的消息，拼接其 `summary` 字段作为"历史摘要"
3. **最近一轮完整消息**：按 `round == max(round)` 过滤，输出所有消息的 `[msg-id] 【name】【action】：summary` 格式

即：摘要由 orchestrator（AI）生成并写入，`get-messages` 只做过滤和格式化，不做任何生成。

### 执行流程

```
Orchestrator（当前会话）
│
├─ Phase 0: 初始化
│   ├─ omp-round-table start "议题"
│   ├─ 生成 session-id（时间戳）
│   ├─ 写入 meta.json、context.md、plan.md
│   ├─ 根据议题从角色库选 3-5 人 → 生成 participants/*.md（prompt 落盘）
│   └─ 展示参会者列表，确认开始
│
├─ Phase 1: 每轮循环（至少 3 轮）
│   │
│   ├─ Step 1: 构建本轮 prompt
│   │   ├─ 注入: context(brief) + 历史摘要 + 上轮完整消息 + 引导问题
│   │   └─ 来源: omp-round-table get-context brief + get-messages
│   │
│   ├─ Step 2: 并行启动参与者（tmux）
│   │   ├─ claude -p "<prompt>" --model opus > responses/round-N-steve-jobs.md
│   │   ├─ codex -p "<prompt>" --model gpt-5.4 > responses/round-N-elon-musk.md
│   │   └─ pi -p "<prompt>" --model qwen3.5-27b > responses/round-N-linus.md
│   │
│   ├─ Step 3: 收集回复
│   │   ├─ 等待所有 tmux 进程结束
│   │   └─ omp-round-table post-message <role> <response-file>（逐个追加）
│   │
│   ├─ Step 4: Orchestrator 综述
│   │   ├─ 提炼核心争议点
│   │   ├─ 生成 ASCII 框架图（结构化展示本轮讨论）
│   │   ├─ 提出下一轮引导问题
│   │   └─ omp-round-table post-message moderator <summary-file>
│   │
│   └─ Step 5: 用户参与（阻塞）
│       ├─ 展示摘要、结论、下一步计划 → 等待用户输入
│       ├─ 用户回复 → omp-round-table post-message user <user-input>
│       └─ 指令: 继续 / 结束 / 深入 / 换人
│
└─ Phase 2: 结束
    ├─ omp-round-table end
    ├─ 生成最终文档 → docs/round-table/YYYY-MM-DD-<topic>.md
    └─ 更新 meta.json status → "completed"
```

### 角色系统

#### 预设角色库

| 角色 | 人物 | 视角定位 | Runtime | Model | 选用场景 |
|------|------|----------|---------|-------|----------|
| 产品视觉家 | Steve Jobs | 用户体验极致主义，简洁 > 功能 | claude | opus | 产品需求、UX 决策 |
| 第一性原理工程 | Elon Musk | 从物理定律出发，质疑所有惯例 | codex | gpt-5.4 | 架构选型、技术方向 |
| 务实开发者 | Linus Torvalds | 代码说话，厌恶过度设计，性能优先 | pi | qwen3.5-27b | 实现方案、代码设计 |
| 系统思想家 | Alan Kay | 面向对象本源思考，长期架构视野 | claude | sonnet | 系统架构、抽象设计 |
| AI 架构师 | Andrej Karpathy | Scaling law 思维，AI-native 设计 | claude | sonnet | AI/ML 架构、模型选型 |
| 魔鬼代言人 | Richard Stallman | 自由/开放/伦理约束，挑战商业假设 | codex | gpt-5.4 | 开源策略、伦理审查 |

#### 张力网络

- **Jobs vs Torvalds**：体验优先 vs 性能优先
- **Musk vs Stallman**：商业创新 vs 伦理约束
- **Alan Kay vs Torvalds**：长期架构 vs 实用主义
- **Karpathy vs Jobs**：AI-native 技术驱动 vs 人本设计
- **Stallman vs Musk**：开放自由 vs 快速迭代

#### 角色选取规则

- 默认选 3-5 人，由 orchestrator 根据议题从角色库中选取
- 用户可在启动时指定角色，或在讨论中通过"换人"指令引入新角色
- 支持用户自定义角色（指定名字、身份、立场、runtime、model）

#### 行动标签

沿用参考实现的标签体系：`陈述`、`质疑`、`补充`、`反驳`、`修正`、`综合`

每位参与者的发言必须：
1. 以行动标签开头，表明本次发言的性质
2. 回应前序发言（不许自说自话）
3. 以 `**简言之**：` 一句话压缩结尾

### Prompt 注入策略

每个参与者的 one-shot prompt 由四层拼接：

```
[Layer 1] 角色身份（来自 participants/<role>.md）
  - 人物名、身份定位、核心思想体系
  - 行为准则：忠于其真实思想体系发言，引用经典著作/观点

[Layer 2] 讨论背景（omp-round-table get-context brief）
  - 议题、目标、约束条件的简要概述

[Layer 3] 对话历史（omp-round-table get-messages）
  - 历史轮次摘要 + 最近一轮完整消息
  - 参与者可通过 get-messages <msg-id> 获取更多细节

[Layer 4] 本轮指令
  - 引导问题（由 orchestrator 提出）
  - 行动标签要求（陈述/质疑/补充/反驳/修正/综合）
  - 输出格式要求（【人物名】【行动标签】：... + **简言之**：...）
```

### 最终输出文档

讨论结束后生成 Markdown 文档，存放于 `docs/round-table/`：

**文件命名：** `YYYY-MM-DD-<topic-slug>.md`

**文档结构：**

```markdown
# 圆桌讨论：<议题>

- **日期**：2026-03-27
- **参与者**：Steve Jobs (claude/opus), Elon Musk (codex/gpt-5.4), ...
- **轮次**：4

## 背景

（问题背景、约束条件、讨论目标）

## 讨论记录

### Round 1: <引导问题>

- 【Steve Jobs】【陈述】：...
- 【Elon Musk】【反驳】：...
- **核心争议**：...
- **用户反馈**：...

### Round 2: <引导问题>
...

## 最终结论

（共识点、决策结果）

## 未解决的开放问题

（讨论中暴露但未穷尽的方向）

## 行动建议

（基于讨论结果的具体下一步）
```

### SKILL.md 草案

#### Frontmatter

```yaml
---
name: round-table
description: >-
  Use when a software design, AI agent architecture, or technical strategy
  topic needs structured multi-perspective debate from multiple AI runtimes
  (claude/codex/pi) running different models in parallel. Orchestrates a real
  multi-agent roundtable with historical figure personas, shared context
  management, and iterative user participation.
  Do NOT use for quick Q&A, single-perspective analysis, code generation,
  or topics that don't benefit from adversarial multi-viewpoint debate.
---
```

#### Body 结构（高层 SOP）

SKILL.md body 只写 7 步高层 SOP，详细流程委托给 references：

```markdown
## Orchestrator SOP

1. **读取角色库** — 加载 `references/roles.md` 了解可用角色
2. **初始化** — `omp-round-table start "<topic>"`，生成 context.md 和 plan.md，选角色并落盘 prompt 到 participants/
3. **每轮循环**（至少 3 轮，详见 `references/discussion-flow.md`）:
   a. 构建 prompt（四层拼接，详见 `references/prompt-templates.md`）
   b. `omp-round-table spawn <round>`（并行启动参与者）
   c. 收集回复 → `omp-round-table post-message <role> <file>`
   d. 综述 → `omp-round-table post-message moderator <summary>`
   e. 展示摘要 → 等待用户指令（继续/结束/深入/换人）
4. **结束** — `omp-round-table end`，生成最终文档
```

加载时机标注：
- 启动时加载 `references/roles.md`
- 进入每轮循环前加载 `references/discussion-flow.md`
- 构建 prompt 时加载 `references/prompt-templates.md`

### 关键决策

- **混合 runtime 而非单 runtime 多模型**：claude code / codex / pi 各自的 system prompt 和工具链构成架构级认知差异，这是单纯切换模型无法获得的多样性来源。
- **stdout 重定向而非 tmux capture-pane**：`claude -p` / `codex` / `pi` 都支持 stdout 输出，进程结束即回复完成，最简洁可靠。
- **JSONL 而非 SQLite**：消息是追加写入的时序数据，JSONL 天然适合；且文本格式便于调试和人工检查。
- **上下文分层（brief/detail）**：one-shot 注入时控制 token 消耗，brief 用于常规注入，detail 按需获取。
- **静态内容预先落盘**：context.md、plan.md、participants/*.md 在初始化时写入，提高可观察性，方便调试和审查。
- **阻塞式用户交互**：orchestrator 本身就是当前会话的 AI agent，直接问用户最自然。
- **至少 3 轮**：确保讨论有足够深度，避免一轮定论。
- **无硬性最大轮次，5 轮后软提醒**：用户每轮都有退出控制权，且每轮的多 runtime 调用成本可感知，无需硬上限。超过 5 轮时 orchestrator 在摘要中提示"已进行 N 轮，建议考虑收敛"，不阻断。

---

## 行动原则

- **TDD: Red → Green → Refactor**：每个 CLI 命令先写测试，再实现。**禁止：** 先写实现再补测试。
- **Break, Don't Bend**：CLI 接口一步到位，不留兼容层。**禁止：** deprecated 标记、v1/v2 路径。
- **Zero-Context Entry**：每个脚本文件前 20 行说明职责和用法。**禁止：** 无头部说明的脚本。
- **Explicit Contract**：session 数据格式（meta.json、messages.jsonl）必须有明确 schema，不依赖隐式约定。**禁止：** 魔法默认值、未声明的字段。
- **Minimum Blast Radius**：按 CLI 命令逐个实现和提交，不捆绑。**禁止：** 一个 PR 混合多个不相关的命令实现。

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `skills/round-table/SKILL.md` | Skill 定义（触发条件 + CLI 命令文档） |
| 新增 | `skills/round-table/scripts/session.sh` | Session 管理（init/get-context/get-messages/post-message/end） |
| 新增 | `skills/round-table/scripts/spawn.sh` | tmux 并行启动参与者 |
| 新增 | `skills/round-table/references/README.md` | 参考文档索引 |
| 新增 | `skills/round-table/references/roles.md` | 预设角色库（人物、runtime、model 映射） |
| 新增 | `skills/round-table/references/prompt-templates.md` | Prompt 模板（四层结构） |
| 新增 | `skills/round-table/references/discussion-flow.md` | 讨论流程详细 SOP |
| 新增 | `skills/round-table/assets/participant-prompt.md` | 参与者 prompt 模板 |
| 新增 | `skills/round-table/assets/output-doc.md` | 最终文档模板 |
| 新增 | `skills/round-table/tests/test_session.sh` | T1 session.sh 测试 |
| 新增 | `skills/round-table/tests/test_spawn.sh` | T1 spawn.sh 测试 |
| 新增 | `bin/omp-round-table` | CLI 入口 dispatcher |
| 修改 | `CLAUDE.md` | 项目结构中新增 round-table skill |

### 任务步骤

#### Task 0: 环境验证（技术前提）

- [ ] **Step 1: 验证各 runtime 的 one-shot 模式和 stdout 行为**

```bash
# 验证 claude -p
echo "hello" | claude -p "say hi" > /tmp/test-claude.md && cat /tmp/test-claude.md

# 验证 codex（确认 -p flag 或等效的 non-interactive 模式）
# 验证 pi -p
```

- [ ] **Step 2: 验证 tmux spawn + stdout 重定向**

```bash
tmux new-session -d -s test-rt 'claude -p "say hi" > /tmp/test-tmux.md'
# 等待完成后检查输出
```

- [ ] **Step 3: 记录各 runtime 的实际命令格式**

将验证结果记录到 `references/runtime-commands.md`，作为 spawn.sh 的实现依据。

#### Task 1: Session 管理脚本（核心数据层）

**Files:**
- 新增: `skills/round-table/scripts/session.sh`
- 测试: `skills/round-table/tests/test_session.sh`

- [ ] **Step 1: 写失败测试**

```bash
# test_session.sh — 测试 session init / get-context / get-messages / post-message
test_init_creates_session_dir()   # 验证 start 创建目录和 meta.json
test_get_context_brief()          # 验证 brief 模式输出摘要
test_get_context_detail()         # 验证 detail 模式输出完整内容
test_post_message_appends_jsonl() # 验证消息追加到 messages.jsonl
test_get_messages_default()       # 验证：历史摘要 + 最近一轮完整消息
test_get_messages_by_id()         # 验证：指定 msg-id 返回详情
test_end_generates_document()     # 验证 end 生成最终文档
```

- [ ] **Step 2: 运行测试确认失败**

```bash
bash skills/round-table/tests/test_session.sh
# 预期：FAIL（脚本不存在）
```

- [ ] **Step 3: 实现 session.sh**

实现 6 个子命令：`init`、`get-context`、`get-messages`、`post-message`、`end`、`status`

- [ ] **Step 4: 运行测试确认通过**

```bash
bash skills/round-table/tests/test_session.sh
# 预期：PASS
```

- [ ] **Step 5: 提交**

```bash
git add skills/round-table/scripts/session.sh skills/round-table/tests/test_session.sh
git commit -m "feat(round-table): add session management script"
```

#### Task 2: Spawn 脚本（参与者启动）

**Files:**
- 新增: `skills/round-table/scripts/spawn.sh`
- 测试: `skills/round-table/tests/test_spawn.sh`

- [ ] **Step 1: 写失败测试**

```bash
# test_spawn.sh — 测试参与者启动逻辑
test_spawn_creates_tmux_session()  # 验证 tmux session 创建
test_spawn_parallel_execution()    # 验证多参与者并行启动
test_spawn_stdout_redirect()       # 验证 stdout 重定向到 responses/
test_spawn_wait_completion()       # 验证等待所有进程结束
```

- [ ] **Step 2: 运行测试确认失败**
- [ ] **Step 3: 实现 spawn.sh**

核心逻辑：读取 meta.json 中的 participants 列表，为每个参与者在 tmux 中启动对应 runtime 命令，stdout 重定向到 `responses/round-N-<role>.md`，等待所有进程完成。

- [ ] **Step 4: 运行测试确认通过**
- [ ] **Step 5: 提交**

```bash
git add skills/round-table/scripts/spawn.sh skills/round-table/tests/test_spawn.sh
git commit -m "feat(round-table): add participant spawn script"
```

#### Task 3: CLI 入口 + SKILL.md

**Files:**
- 新增: `bin/omp-round-table`
- 新增: `skills/round-table/SKILL.md`

- [ ] **Step 1: 实现 CLI dispatcher**

```bash
#!/usr/bin/env bash
# omp-round-table — Round Table 圆桌讨论 CLI
# 子命令: start | get-context | get-messages | post-message | spawn | end
SKILL="${OMP_HOME:-$HOME/.oh-my-superpowers}/skills/round-table"
case "${1:-}" in
  start)        shift; exec bash "$SKILL/scripts/session.sh" init "$@" ;;
  get-context)  shift; exec bash "$SKILL/scripts/session.sh" get-context "$@" ;;
  get-messages) shift; exec bash "$SKILL/scripts/session.sh" get-messages "$@" ;;
  post-message) shift; exec bash "$SKILL/scripts/session.sh" post-message "$@" ;;
  spawn)        shift; exec bash "$SKILL/scripts/spawn.sh" "$@" ;;
  end)          shift; exec bash "$SKILL/scripts/session.sh" end "$@" ;;
  *)            echo "Usage: omp-round-table {start|get-context|get-messages|post-message|spawn|end}" ;;
esac
```

- [ ] **Step 2: 编写 SKILL.md**

包含 frontmatter（name、description）、CLI 命令文档、orchestrator 流程 SOP。

- [ ] **Step 3: 提交**

```bash
git add bin/omp-round-table skills/round-table/SKILL.md
git commit -m "feat(round-table): add CLI entry point and SKILL.md"
```

#### Task 4: References（角色库 + Prompt 模板 + 流程文档）

**Files:**
- 新增: `skills/round-table/references/README.md`
- 新增: `skills/round-table/references/roles.md`
- 新增: `skills/round-table/references/prompt-templates.md`
- 新增: `skills/round-table/references/discussion-flow.md`
- 新增: `skills/round-table/assets/participant-prompt.md`
- 新增: `skills/round-table/assets/output-doc.md`

- [ ] **Step 1: 编写 references/README.md（索引）**

```markdown
| 场景 | 文档 |
| 需要选角色 | [roles.md](roles.md) |
| 需要构建 prompt | [prompt-templates.md](prompt-templates.md) |
| 需要理解流程 | [discussion-flow.md](discussion-flow.md) |
```

- [ ] **Step 2: 编写角色库、prompt 模板、流程文档**
- [ ] **Step 3: 编写 assets 模板**
- [ ] **Step 4: 提交**

```bash
git add skills/round-table/references/ skills/round-table/assets/
git commit -m "feat(round-table): add role library, prompt templates, and flow docs"
```

#### Task 5: 文档更新

**Files:**
- 修改: `CLAUDE.md`

- [ ] **Step 1: 更新 CLAUDE.md 项目结构**

在 skills 列表中新增 `round-table/` 条目。

- [ ] **Step 2: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: add round-table skill to project structure"
```
