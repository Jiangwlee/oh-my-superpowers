# Team Skill — 通用 tmux Agent 编排层

> 标准化的 tmux agent 编排层，one-shot 驱动 claude/codex/pi 协作完成任务。面向 AI orchestrator，降低推理成本，提高任务执行精度。

## 目录

- [设计方案](#设计方案)
  - [背景与目标](#背景与目标)
  - [架构](#架构)
  - [CLI 接口](#cli-接口)
  - [run.sh 核心逻辑](#runsh-核心逻辑)
  - [references 双层体系](#references-双层体系)
  - [SKILL.md 编排 SOP](#skillmd-编排-sop)
  - [关键决策](#关键决策)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 背景与目标

当前 AI orchestrator（如 Claude Code session）需要驱动其他 AI runtime 协作完成任务时，必须手写 tmux 命令、记住各 runtime 的 CLI 参数差异、手动处理输出清洗和完成检测。这些操作重复性高、出错率高，且推理成本不必要地消耗在工具细节上。

**目标：** 提供一个极薄的"笨但可靠的发射台"，将 tmux + 多 runtime CLI 操作封装为简单命令，让 orchestrator 专注于编排逻辑而非工具细节。

**成功标准：**
- orchestrator 无需了解 tmux 命令即可 dispatch 任务
- 三种 runtime 的调用方式统一为 `omp-team run <runtime>`
- 退出码语义清晰，orchestrator 可靠判断成功/失败/超时

### 架构

```
skills/team/
├── SKILL.md              # 编排 SOP 入口：何时用、怎么编排
├── scripts/
│   ├── run.sh            # 核心：spawn + wait + collect 原子操作
│   ├── status.sh         # 查询 tmux session 状态
│   └── clean.sh          # 清理 ANSI + 规范化输出
├── references/
│   ├── README.md         # 入口索引：模式速查 + 场景→模式映射
│   ├── patterns/         # 编排原则（orchestrator handbook）
│   │   ├── pipeline.md           # 线性链式 A → B → C
│   │   ├── fan-out-fan-in.md     # 并行分发 + 结果聚合
│   │   ├── discussion.md         # 多 agent 共享上下文讨论
│   │   └── batch.md              # 大量短命 worker 批量执行
│   ├── scenarios/        # 业务场景 SOP（角色 + 职责 + 步骤 + 指定 pattern）
│   │   ├── code-and-review.md    # → uses: pipeline
│   │   ├── debate.md             # → uses: fan-out-fan-in
│   │   └── round-table.md        # → uses: discussion（轻量版，非 round-table skill）
│   ├── prompts/          # 常用 prompt 框架（orchestrator 填入具体内容）
│   │   ├── coding-task.md        # 编码任务 prompt 模板
│   │   ├── code-review.md        # 代码审查 prompt 模板
│   │   └── role-activation.md    # 角色激活 prompt 模板
│   └── runtime-reference.md      # 三种 runtime CLI 速查
└── tests/
    └── t1_static.sh      # 静态检查
```

**CLI 入口：** `bin/omp-team` — bash dispatcher，路由到 `scripts/`。

**层次关系：**
- `omp-team run` 是原子操作：spawn 一个 runtime + 等待完成 + 返回输出
- 编排逻辑不在 team scripts 里，在 SKILL.md 的场景 SOP 里，由 orchestrator 执行
- team 不管多轮、不管重试、不管权限——这些是 orchestrator 的事
- 并发由 orchestrator 负责：多次调用 `omp-team run &` + `wait`

### CLI 接口

**dispatcher (`bin/omp-team`)：**

```bash
#!/usr/bin/env bash
SCRIPTS="${OMP_HOME:-$HOME/.oh-my-superpowers}/skills/team/scripts"

case "${1:-}" in
  run)    shift; exec bash "$SCRIPTS/run.sh" "$@" ;;
  status) shift; exec bash "$SCRIPTS/status.sh" "$@" ;;
  clean)  shift; exec bash "$SCRIPTS/clean.sh" "$@" ;;
  *)      echo "Usage: omp-team {run|status|clean} [args]"; exit 1 ;;
esac
```

**命令总览：**

| 命令 | 用途 | 示例 |
|------|------|------|
| `omp-team run <runtime> "<prompt>"` | one-shot 执行 | `omp-team run codex "实现登录模块"` |
| `omp-team run <runtime> --prompt-file <path>` | 从文件读取 prompt | `omp-team run claude --prompt-file design.md` |
| `omp-team status [session-name]` | 查看 tmux session 状态 | `omp-team status team-20260328-abc` |
| `omp-team clean <file>` | strip ANSI + 规范化输出 | `omp-team clean /tmp/codex-output.txt` |

**`run` 完整参数：**

```
omp-team run <runtime> [prompt] [options]
  <runtime>              claude | codex | pi
  [prompt]               内联 prompt（与 --prompt-file 互斥）
  --prompt-file <path>   从文件读取 prompt
  --model <model>        覆盖默认模型
  --timeout <seconds>    超时秒数（默认 300）
  --output-file <path>   指定输出文件（默认临时文件）
  --cwd <dir>            worker 工作目录（默认 $PWD）
```

**输出协议：**
- stdout：clean 后的 worker 输出（orchestrator 直接消费）
- stderr：team 自身的状态日志（spawn/wait/timeout 信息）
- 退出码：`0` 成功 / `1` 执行错误 / `124` 超时

### run.sh 核心逻辑

三步原子操作：spawn → wait → output。

**0. PREPARE**

解析参数。若为 inline prompt（`omp-team run codex "prompt text"`），写入临时文件 `/tmp/team-<session>-prompt.md`，统一走 prompt_file 路径。生成 output_file 路径 `/tmp/team-<session>-output.txt`（除非 `--output-file` 指定）。

**1. SPAWN**

生成唯一 session name `team-<timestamp>-<random>`，按 runtime 构建命令（路径拼接进字符串）：

```bash
# claude — stdin 管道（最安全，无 shell 转义风险）
cat "$prompt_file" | claude -p --model "$model" 2>&1 | tee "$output_file"

# codex — stdin 管道，显式 `-` 声明从 stdin 读取
cat "$prompt_file" | codex exec - 2>&1 | tee "$output_file"

# pi — @file 原生语法（pi 的一等公民特性）
pi --no-session -p @"$prompt_file" --model "$model" 2>&1 | tee "$output_file"
```

启动 tmux session：
```bash
tmux new-session -d -s "$session_name" -c "$cwd" "$cmd; exit"
```

**2. WAIT**

轮询 `tmux has-session`（5s 间隔）。session 消失 = 进程结束。超时则 `tmux kill-session` + 写 timeout 标记。

**3. OUTPUT**

读 output_file → 调用 `clean.sh` strip ANSI → 输出到 stdout。

**Prompt 传递安全性：**

| 方式 | `$VAR` 展开 | 反引号执行 | 超长内容 | 结论 |
|------|------------|-----------|---------|------|
| `$(cat file)` 参数嵌入 | 危险 | 危险 | 可能超限 | 禁用 |
| stdin 管道 | 安全 | 安全 | 安全 | claude/codex 使用 |
| `@file` 语法 | 安全 | 安全 | 安全 | pi 使用 |

### references 双层体系

**patterns/（编排原则）** — orchestrator 的 handbook，描述抽象编排拓扑：

| 文件 | 拓扑 | 核心规则 |
|------|------|---------|
| `pipeline.md` | A → B → C 线性链 | 前一步输出是下一步输入，失败即停 |
| `fan-out-fan-in.md` | 并行分发 + 聚合 | 同一任务多 worker 并行，结果合并 |
| `discussion.md` | 多 agent 共享上下文 | 每轮所有参与者看到前一轮所有输出 |
| `batch.md` | 大量短命 worker | 独立任务并行执行，互不依赖 |

每个 pattern 文档包含：拓扑图、适用条件、编排规则、失败处理原则、退出条件。

**scenarios/（业务场景）** — 具体场景 SOP，明确指定 pattern：

| 文件 | pattern | 描述 |
|------|---------|------|
| `code-and-review.md` | pipeline | 编码与代码评审：构建上下文 → 划分任务 → 编码 → review → 修复循环 |
| `debate.md` | fan-out-fan-in | 正反方对抗式辩论：多 agent 并行阐述立场 → 聚合结论 |
| `round-table.md` | discussion | 轻量圆桌：多 agent 多轮讨论，比 round-table skill 更薄（无角色 prompt 管理、无历史聚合） |

每个 scenario 文档包含：`pattern: <name>`（明确指定）、参与者配置、具体步骤、prompt 模板引用、完成判定。

**prompts/（常用 prompt 框架）** — 固化的 prompt 模板，orchestrator 填入具体内容：

| 文件 | 用途 | 核心结构 |
|------|------|---------|
| `coding-task.md` | 编码任务分配 | 角色 + 上下文 + 任务描述 + 验收标准 + 输出格式 |
| `code-review.md` | 代码审查 | 角色 + 被审代码路径 + 审查维度 + 严重程度定义 + 输出格式 |
| `role-activation.md` | 角色激活通用模板 | 身份定义 + 约束条件 + 参考文档 + 任务指令 + {placeholder} 变量 |

prompt 模板设计原则（参考 agency-agents handoff templates）：
- 角色 + 约束前置，不假设 worker 有上下文
- 使用 `{placeholder}` 变量供 orchestrator 填充
- 包含明确的验收标准（checkbox 形式）
- 要求证据（具体文件路径、测试结果），不接受空泛描述

**依赖关系：** scenario 引用 pattern + prompts。orchestrator 读 scenario 就知道用什么模式 + 具体怎么做 + 用什么 prompt 模板，不需要自己猜测。

### SKILL.md 编排 SOP

SKILL.md 正文结构：

1. **Quick Reference** — 命令速查表（run / status / clean）
2. **Runtime 选择指南** — 什么任务用什么 runtime
   - `codex`：编码实现、文件修改（YOLO，不需确认）
   - `claude`：设计、review、复杂推理
   - `pi`：轻量任务、快速验证
3. **场景编排索引** — 指向 `references/scenarios/` 下的具体 SOP
   - "需要编码+审查？→ 读 `code-and-review.md`"
   - "需要正反辩论？→ 读 `debate.md`"
   - "需要多人讨论？→ 读 `round-table.md`"
4. **Prompt 框架索引** — 指向 `references/prompts/` 下的模板
5. **Prompt 规范** — prompt 怎么写才能让 one-shot 成功率最高
   - 上下文自包含（不假设 worker 有历史）
   - 明确输出格式要求
   - 指定工作目录
   - 使用 `references/prompts/` 中的模板，填入 `{placeholder}` 变量

### 关键决策

- **每个 `run` 一个独立 tmux session**：互不干扰，orchestrator 并发调用无冲突。不用 window/pane 是因为 session 消失 = 进程结束，检测最简单。
- **stdin/`@file` 传递 prompt，禁用 `$(cat)` 参数嵌入**：避免 shell 特殊字符展开风险（`$VAR`、反引号、超长内容）。
- **stdout/stderr 分离**：stdout 给 orchestrator 消费（clean 后的 worker 输出），stderr 给人类调试（team 自身日志）。
- **退出码语义 0/1/124**：orchestrator 用 `$?` 判断，不需要解析输出。124 与 GNU `timeout` 约定一致。
- **patterns 与 scenarios 分离**：pattern 是抽象编排原则，scenario 是具体业务 SOP。scenario 明确指定 pattern，orchestrator 不猜测。
- **team 不管多轮/重试/权限**：这些是 orchestrator 的事。team 只做 one-shot 原子操作。
- **team 与 round-table 并存互补**：team 是通用编排层（原子操作），round-table 是特化场景（多人多轮讨论的完整生命周期管理）。两者独立，互不依赖。未来 round-table 有可能迁移为 team 的消费者（用 `omp-team run` 替代自己的 spawn 逻辑），但这不是当前目标。`scenarios/brainstorm.md` 描述的是用 team 原语搭建轻量讨论，与 round-table 的完整功能（角色 prompt、轮次管理、历史聚合）不重叠。
- **inline prompt 统一写临时文件**：`omp-team run codex "prompt text"` 会将 inline prompt 写入临时文件，然后统一走 prompt_file 路径。避免两套分支逻辑。
- **tmux 命令字符串拼接传递变量**：`output_file` 路径在 run.sh 主进程中生成（`/tmp/team-<session>.txt`），拼接进 tmux 命令字符串。路径由 run.sh 控制，不含特殊字符，无转义风险。不使用环境变量或临时脚本。

---

## 行动原则

- **TDD: Red → Green → Refactor**：run.sh 的 spawn/wait/timeout 逻辑先写测试再实现。**禁止：** 先写实现再补测试；无测试的功能提交。

- **Break, Don't Bend**：不兼容 round-table 的 spawn 逻辑，clean break 独立实现。**禁止：** 代码和文档中出现兼容性标记。

- **Zero-Context Entry**：SKILL.md 自包含，orchestrator 无需读其他 skill 即可使用 team。每个文件前 20 行说明职责。**禁止：** 文件无头部说明；文档无目录。

- **Explicit Contract**：退出码 0/1/124 + stdout/stderr 分离 + scenario 明确指定 pattern。**禁止：** 魔法默认值；隐式约定。

- **Fail at the Boundary**：timeout/runtime 不存在/参数错误在 run.sh 入口立即报错，返回清晰退出码。**禁止：** 内部函数做防御性校验；吞掉异常后继续执行。

- **Minimum Blast Radius**：每个 task 只解决一个模块，独立提交。**禁止：** 一个 PR 混合多模块开发。

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `skills/team/SKILL.md` | 触发描述 + 命令速查 + runtime 指南 + 场景索引 |
| 新增 | `skills/team/scripts/run.sh` | 核心：spawn → wait → output 原子操作 |
| 新增 | `skills/team/scripts/status.sh` | 查询 tmux session 状态 |
| 新增 | `skills/team/scripts/clean.sh` | strip ANSI 转义，规范化输出 |
| 新增 | `bin/omp-team` | CLI dispatcher |
| 新增 | `skills/team/references/README.md` | 入口索引：模式速查 + 场景映射 |
| 新增 | `skills/team/references/patterns/pipeline.md` | 线性链式编排原则 |
| 新增 | `skills/team/references/patterns/fan-out-fan-in.md` | 并行汇聚编排原则 |
| 新增 | `skills/team/references/patterns/discussion.md` | 多 agent 讨论编排原则 |
| 新增 | `skills/team/references/patterns/batch.md` | 批量 worker 编排原则 |
| 新增 | `skills/team/references/scenarios/code-and-review.md` | pipeline：编码与代码评审 |
| 新增 | `skills/team/references/scenarios/debate.md` | fan-out：正反方辩论 |
| 新增 | `skills/team/references/scenarios/round-table.md` | discussion：轻量圆桌讨论 |
| 新增 | `skills/team/references/prompts/coding-task.md` | 编码任务 prompt 模板 |
| 新增 | `skills/team/references/prompts/code-review.md` | 代码审查 prompt 模板 |
| 新增 | `skills/team/references/prompts/role-activation.md` | 角色激活通用模板 |
| 新增 | `skills/team/references/runtime-reference.md` | 三种 runtime CLI 差异速查 |
| 新增 | `skills/team/tests/t1_static.sh` | 静态检查 |

### 任务步骤

#### Task 1: scripts/clean.sh — ANSI 清洗工具

**Files:**
- 新增: `skills/team/scripts/clean.sh`
- 测试: `skills/team/tests/t1_static.sh`

- [ ] **Step 1: 写失败测试**

```bash
# tests/test_clean.sh
# 输入含 ANSI 转义的文本，期望输出纯文本
echo -e "\033[1;32mHello\033[0m World" > /tmp/test_ansi.txt
result=$(bash scripts/clean.sh /tmp/test_ansi.txt)
[ "$result" = "Hello World" ] || exit 1
```

- [ ] **Step 2: 实现 clean.sh**

```bash
# 读取文件，strip ANSI escape sequences，输出到 stdout
sed 's/\x1b\[[0-9;]*[a-zA-Z]//g' "$1"
```

- [ ] **Step 3: 测试通过 + 提交**

```bash
git add skills/team/scripts/clean.sh
git commit -m "feat(team): add ANSI cleaning utility"
```

#### Task 2: scripts/run.sh — 核心 spawn/wait/output

**Files:**
- 新增: `skills/team/scripts/run.sh`

- [ ] **Step 1: 写失败测试**

```bash
# 使用 mock runtime（echo 命令）验证：
# 1. tmux session 创建和自动销毁
# 2. output file 生成
# 3. 退出码 0（正常）/ 124（超时）
```

- [ ] **Step 2: 实现参数解析**

解析 `<runtime>` `[prompt]` `--prompt-file` `--model` `--timeout` `--output-file` `--cwd`。

- [ ] **Step 3: 实现 spawn 逻辑**

按 runtime 构建命令（claude stdin / codex stdin / pi @file），启动 tmux session。

- [ ] **Step 4: 实现 wait 逻辑**

轮询 `tmux has-session`（5s 间隔），超时则 kill-session。

- [ ] **Step 5: 实现 output 逻辑**

调用 clean.sh strip ANSI，输出到 stdout。

- [ ] **Step 6: 测试通过 + 提交**

```bash
git add skills/team/scripts/run.sh
git commit -m "feat(team): implement run.sh spawn/wait/output"
```

#### Task 3: scripts/status.sh — 状态查询

**Files:**
- 新增: `skills/team/scripts/status.sh`

- [ ] **Step 1: 实现**

查询 `tmux list-sessions -F '#{session_name} #{session_created}'` 过滤 `team-*` 前缀。

- [ ] **Step 2: 提交**

```bash
git add skills/team/scripts/status.sh
git commit -m "feat(team): add status query utility"
```

#### Task 4: bin/omp-team — CLI dispatcher

**Files:**
- 新增: `bin/omp-team`

- [ ] **Step 1: 实现 dispatcher**

case 路由 run/status/clean 到对应 scripts。

- [ ] **Step 2: 提交**

```bash
git add bin/omp-team
git commit -m "feat(team): add CLI dispatcher"
```

#### Task 5: SKILL.md — 编排 SOP

**Files:**
- 新增: `skills/team/SKILL.md`

- [ ] **Step 1: 编写 frontmatter + 正文**

触发描述、命令速查、runtime 选择指南、场景索引、prompt 规范。

- [ ] **Step 2: 提交**

```bash
git add skills/team/SKILL.md
git commit -m "feat(team): add SKILL.md orchestration SOP"
```

#### Task 6: references/patterns/ — 编排模式 handbook

**Files:**
- 新增: `skills/team/references/README.md`
- 新增: `skills/team/references/patterns/pipeline.md`
- 新增: `skills/team/references/patterns/fan-out-fan-in.md`
- 新增: `skills/team/references/patterns/discussion.md`
- 新增: `skills/team/references/patterns/batch.md`

- [ ] **Step 1: 编写 README.md 入口索引**
- [ ] **Step 2: 编写 4 个 pattern 文档**

每个包含：拓扑图、适用条件、编排规则、失败处理、退出条件。

- [ ] **Step 3: 提交**

```bash
git add skills/team/references/
git commit -m "feat(team): add orchestration pattern handbook"
```

#### Task 7: references/scenarios/ — 业务场景 SOP

**Files:**
- 新增: `skills/team/references/scenarios/code-and-review.md`
- 新增: `skills/team/references/scenarios/debate.md`
- 新增: `skills/team/references/scenarios/round-table.md`

- [ ] **Step 1: 编写 code-and-review.md**

pipeline 模式。Orchestrator 关键职责：构建充分上下文、划分任务、编排任务顺序、构建提示词、分配编码任务、Review 代码。引用 `prompts/coding-task.md` 和 `prompts/code-review.md`。

- [ ] **Step 2: 编写 debate.md**

fan-out-fan-in 模式。多 agent 并行阐述立场，orchestrator 聚合结论。

- [ ] **Step 3: 编写 round-table.md**

discussion 模式。轻量版圆桌——比 round-table skill 更薄（无角色 prompt 管理、无历史聚合），用 omp-team run 原语搭建多轮讨论。参考 ljg-roundtable 的极简设计（action tags、ASCII 框架、引导深化）。

- [ ] **Step 4: 提交**

```bash
git add skills/team/references/scenarios/
git commit -m "feat(team): add scenario SOPs (code-and-review, debate, round-table)"
```

#### Task 8: references/prompts/ — Prompt 框架模板

**Files:**
- 新增: `skills/team/references/prompts/coding-task.md`
- 新增: `skills/team/references/prompts/code-review.md`
- 新增: `skills/team/references/prompts/role-activation.md`

- [ ] **Step 1: 编写 coding-task.md**

编码任务 prompt 模板：角色 + 上下文 + 任务描述 + 验收标准 + 输出格式。使用 `{placeholder}` 变量。参考 agency-agents/agent-activation-prompts.md 的结构。

- [ ] **Step 2: 编写 code-review.md**

代码审查 prompt 模板：角色 + 被审代码路径 + 审查维度 + 严重程度定义 + 输出格式。要求证据（具体文件路径、测试结果）。

- [ ] **Step 3: 编写 role-activation.md**

通用角色激活模板：身份定义 + 约束条件 + 参考文档 + 任务指令 + `{placeholder}` 变量。

- [ ] **Step 4: 提交**

```bash
git add skills/team/references/prompts/
git commit -m "feat(team): add prompt framework templates"
```

#### Task 9: references/runtime-reference.md — Runtime 速查

**Files:**
- 新增: `skills/team/references/runtime-reference.md`

- [ ] **Step 1: 编写三种 runtime 的 CLI 参数差异、默认模型、已知限制**
- [ ] **Step 2: 提交**

```bash
git add skills/team/references/runtime-reference.md
git commit -m "feat(team): add runtime CLI reference"
```

#### Task 10: tests/t1_static.sh — 静态检查

**Files:**
- 新增: `skills/team/tests/t1_static.sh`

- [ ] **Step 1: 实现静态检查**

检查：SKILL.md 存在且有 frontmatter、scripts 有 shebang 和 executable bit、无相对路径调用。

- [ ] **Step 2: 提交**

```bash
git add skills/team/tests/t1_static.sh
git commit -m "test(team): add T1 static checks"
```

#### Task 11: 文档更新

**Files:**
- 修改: `CLAUDE.md`（项目结构 skills 列表）

- [ ] **Step 1: 更新 CLAUDE.md 项目结构**

在 skills 列表中添加 `team/` 条目。

- [ ] **Step 2: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: add team skill to project structure"
```
