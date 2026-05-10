# kickoff Skill State-Machine Refactor

> 把 kickoff 从「wave + commit-driven review」重构为「task 状态机 + journal.md 过程渗透」，让 compact 抗性来自过程留痕而非临终总结，并把"反凭记忆"从行为提示升级为 task 入口的强证据要求。

## 目录

- [设计方案](#设计方案)
- [前置决议变更](#前置决议变更)
- [假设与风险登记](#假设与风险登记)
- [Spike 计划](#spike-计划)
- [Spike 结果](#spike-结果)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 背景与目标

当前 kickoff 在长任务执行时暴露三个痛点：

1. **凭记忆执行**：task 进入实现阶段后，agent 不读真实代码就开始猜，已被多次实测证实。
2. **compact 后续不上**：现有协作方案是触发 handoff 在 /compact 前生成总结文档；handoff 是"事后回忆"，临终时上下文已被噪音污染，挤不出真正关键的指针。
3. **wave 粒度造成 review 节奏不灵活**：wave（≤10 commit / 500 行）是硬触发，小任务也被强制走完整 review 流程；agent 没有"按风险弹性 review"的自主权。

成功标准：

- 任意 task 进入 edit 之前，journal 里必须留有可重跑的 verify 命令和事实陈述（不是"我已读过"这种行为提示）。
- 跨 /compact 的会话只需读 `story.md + journal.md + omp kickoff status` 即可续上，不依赖 LLM 临终总结。
- review 触发时机由 developer 根据状态机自主决定，最终标准统一在"进 Phase 3 前所有 task 必须达到 reviewed/dropped 终态"。

### 架构

**两文件状态容器 + 一命令恢复指针**

```
stories/<YYYY-MM-DD>-<slug>/
├── story.md     # 静态契约：Goal / Scope / 必读 / 测试环境 / 红线 / 任务计划 / Phase 3 时追加 Summary
└── journal.md   # 动态过程流：所有事件按时间序列追加（TASK 入/出 entry + ISSUE append-only）
```

恢复入口：`omp kickoff status`（不依赖 hook，跨 runtime 通用，按需调用）。

**两角色**

| 角色 | 职责 |
|---|---|
| **developer** | 实施工作（写代码、commit、维护 journal、推进 task 状态）；任意时刻派遣 reviewer 推进 done → reviewed；必要时派遣 sub-agent 做窄域 explore（只读，隔离上下文） |
| **reviewer** | 隔离上下文 cross review；输出 PASS/NEEDS_FIX/BLOCKED；不得修改文件 |

reviewer 派遣可选：默认 sub-agent (`agents/code-reviewer.md`)，备选跨 runtime tmux 派 codex（参考 `references/commands.md`）。

**Task 状态机**

```
planned → in_progress → done → reviewed   （正向终态）
              ↓           ↓
              dropped   needs_fix → done    （needs_fix 必须重新 commit）
              ↓
              dropped
```

合法迁移仅以下：

| From | To | 触发 |
|---|---|---|
| planned | in_progress | developer 进入实现，journal 写四段证据 |
| planned | dropped | scope 调整 |
| in_progress | done | 至少一次 commit；journal 写 decision/diff |
| in_progress | dropped | 决定不做 |
| done | reviewed | reviewer verdict = PASS |
| done | needs_fix | reviewer verdict = NEEDS_FIX |
| needs_fix | done | 修复 commit |

终态：`reviewed`、`dropped`。
**禁止迁移**：planned → done、in_progress → reviewed、needs_fix → reviewed（必须经 done）。

**Journal Entry 协议**

TASK 入口（4 段证据，未填齐不得进入 edit）：

```markdown
## T2 implement [in_progress] 14:22
assumption:  我以为是什么
verify:      我跑了什么命令（rg / sed / cat 等可重跑命令）
fact:        命令输出告诉我代码实际是什么
edit target: 准备改哪些文件 / 哪些函数
```

TASK 出口：

```markdown
## T2 implement [done] 14:55
decision: 关键决策一句话
gotcha:   坑点（可空）
diff:     改动文件列表 + 行数
```

REVIEWED entry（可批量）：

```markdown
## T2,T3 [reviewed] 16:10
verdict:  PASS
reviewer: codex sub-agent
batch:    T2 + T3
```

ISSUE append-only：

```markdown
## ISSUE-001 open 14:50
source: T2 review
fact:   ingest.py 缺 path 长度校验
plan:   T5 决定是否升 task

## ISSUE-001 update fixed 16:30
by:     T5 commit abc1234
```

当前状态规则：每个 task / ISSUE 的当前状态 = 最后一条同 ID entry 的状态标记。**不允许改动旧 entry**——只允许追加。

**story.md 模板要点**

- 删除 frontmatter（`mode` 因不分流没用，`runtime` 易腐）。
- `## 必读文件` 表格用语义锚点（函数 / 类 / 章节标题），不用行号；增加 `验证命令` 列，给 developer 一个起手 grep。
- `## 参考文档` 段独立，与"必读文件"职责不同（一次性建立背景 vs 每 task 入口对照事实）。
- `## Out of Scope` 强制写——防 scope creep 的负面清单。
- Phase 3 收尾在同文件末尾追加 `## Summary`（不再独立 story-summary.md）。

**omp kickoff status 输出**

```
Story: stories/2026-05-10-wiki-pdf/
Tasks:
  T1 explore        [reviewed]
  T2 implement      [reviewed]
  T3 wire-up        [done]        ← reviewable
  T4 docs           [done]        ← reviewable
  T5 e2e            [in_progress]
    Evidence: ✓ assumption ✓ verify ✓ fact ✓ edit target

Open issues: 1 (ISSUE-001)
Uncommitted:  scripts/ingest.py (+18 -2)
Phase 3 ready: NO (1 in_progress, 2 awaiting review)
```

进 Phase 3 前 status 自检——任一非终态 task 存在则阻断。

### 关键决策

- **删除 wave 概念**：review 时机改由 developer 基于状态机自主决定。最终统一标准是"进 Phase 3 前所有 task ∈ {reviewed, dropped}"，不再有"≤10 commit / 500 行"硬触发。
- **单 agent 编码（developer 不外包实现）**：sub-agent 上下文短、训练记忆比例反而更高，外包实现不解决凭记忆问题。sub-agent 只用于窄域 explore（只读，隔离上下文）和 review（隔离上下文）。
- **过程渗透 vs 临终总结**：信息保留改成"每个 task 边界都强制写入"，handoff 不再独立产出文档；compact 后通过 status + 读 story.md/journal.md 续接。
- **journal 字段固定但保持 Markdown**：assumption/verify/fact/edit target/decision/gotcha/diff/source/plan/by 等是固定字段名（不是固定 schema），同时保留 grep 可达性。
- **ISSUE 与 task 状态分离**：review 不通过用 needs_fix 状态表达，简单返工 fix→done loop 即可；旁路问题或跨 task 问题用 ISSUE-NNN 表达，append-only。两者不重叠。
- **不分 fast/long 模式**：单一流程，不让 LLM 自行判定走哪条路（容易把"看起来简单"的任务塞进 fast 路径，恰是凭记忆问题高发场景）。
- **不引入 hook 机制**：恢复指针走 `omp kickoff status` 命令——按需调用、跨 runtime 通用、与 handoff skill 互不干扰。未来若证明命令仍依赖 LLM 自觉，再考虑加 SessionStart hook。
- **task 入口"四段证据"是软门槛**：靠 SKILL.md 写规则 + status 命令做 `Evidence: ✓✓✗✗` 检查辅助；不会 100% 拦糊弄，但比"假设+必读"难一个数量级。已接受这种执法强度。

---

## 前置决议变更

本次重构显式 override 以下既有决议：

### A. 废止 wave / JIT 拆分机制

- **来源决议**：`docs/brainstorming/specs/2026-04-19-brainstorming-coding-orchestrator-redesign.md` §「coding-orchestrator JIT 拆分」+ §「story-memory.md 机制」
- **原决议要点**：coding-orchestrator 按 wave JIT 写 task spec；`story-memory.md` 作为 per-story 显式记忆；wave 粒度（≤10 commit / 500 行）。
- **变更**：wave 概念整体废止；`story-memory.md` 与 `story-summary.md` 都并入新 `journal.md` / `story.md` Summary 段；JIT 拆分由 task 状态机驱动取代。
- **理由**：实践中 wave 是硬触发，对小任务造成节奏卡点；记忆形式上是分文件，写时要决策"这条记哪儿"，反而增负。状态机驱动 + 时间序列 journal 更直接。

### B. 内化 compact 抗性，但不重新发明 hook

- **来源决议**：`docs/brainstorming/specs/2026-04-20-handoff-skill-design.md`（handoff skill 三 hook 闭环）
- **保留**：handoff skill 作为通用 compact 工具继续独立存在，PreCompact/PostCompact/UserPromptSubmit 三 hook 不动。
- **变更**：kickoff 不再依赖 handoff 抓取 story 关键信息；通过 journal.md 的过程渗透 + `omp kickoff status` 实现自身 compact 抗性。两个 skill 形成"通用 vs story 专属"分工，互不干扰。

### C. brainstorming → kickoff 契约保持

- **来源决议**：`memory: decision_brainstorming_orchestrator_handoff` + `skills/brainstorming/scenarios/feature.md` Step 5 Invariant
- **未变**：brainstorming 仍然只产 design doc；kickoff（前 coding-orchestrator）仍自行从 design doc init story。
- **影响**：kickoff `omp kickoff story init --design-doc <path>` 入参签名保留；只是 init 后落盘的内部结构变了（从 4 件套改成 2 件套）。

---

## 假设与风险登记

| # | 假设/赌注 | 类别 | 错了的代价 | 验证手段 | 处理 |
|---|----------|------|-----------|---------|------|
| A1 | task 入口"四段证据"作为软门槛 + status 检查器辅助，能显著降低凭记忆率（从主观经验降到可观察迹象） | 🟡 | 软门槛被 LLM 糊弄，凭记忆问题不解决 | 重构后 dogfood 跑 3-5 个真实 story，观察 evidence 字段质量 | 接受为已知风险；后续若失败再加更硬执法（CLI 执法 / hook） |
| A2 | journal.md 自由文本 + 固定字段名 + grep 检索，能撑得住单 story 量级（200-500 行）的过程记录 | 🟢 | journal 不可读 / 状态识别错乱 | 文档直接答 + 实测 grep | 不做 spike，先按设计实施 |
| A3 | 不引入 hook，靠 `omp kickoff status` 命令做恢复指针，能让 compact 后会话续接成功率显著高于现状 handoff | 🟡 | 命令仍要 LLM 自觉调用，不调用就回到现状 | dogfood 实测；status 命令本身简单（list 文件 + 解析 entry），不做 spike | 在 SKILL.md 显式要求"新会话第一动作跑 status"；若实测仍依赖 LLM 自觉，下一轮加 SessionStart hook |
| A4 | 旧 stories 目录用 archive 流程一次性归档处理，不写 migration | 🟢 | 用户已接受 Break Don't Bend | 文档直接答 | SKILL.md 写明"旧结构 story 走 archive" |
| A5 | dogfood 自举（用 kickoff 重构 kickoff）切换时机：Step 2 完成 commit 后立即把 stories/ 切到新模板 | 🟢 | 第一波改动用旧模板，过渡期混合 | 文档直接答 | 在 Step 2 task description 里写明 cutover 步骤 |
| A6 | 把 review 决策权完全交给 developer，会不会出现"一直 defer 不 review"的滚雪球 | 🟡 | Phase 3 前积压大量 done task，一次性背一堆 review | dogfood 观察；状态机本身保证终态，所以"积压"是自找麻烦不是协议失效 | 在 SKILL.md `Hard Gate` 段加："准备进 Phase 3 但仍有 ∈ done 的 task → 阻断"；不引入软触发或行数兜底 |

无 🔴 项。重构属于协议层 + 文档层调整，状态机和 journal 协议都可在文档中证明良构，不需要 spike 跑代码验证。

---

## Spike 计划

无（无 🔴 风险项）。

## Spike 结果

无（无 spike）。

---

## 行动原则

- **Break, Don't Bend**：旧的 `story-memory.md` / `story-summary.md` / `tasks.yaml` / wave 机制全部删除，不留 alias 或 legacy 兼容读取。**禁止：** 在新 SKILL.md / templates / scripts 中出现 `story-memory`、`story-summary`、`tasks.yaml`、`wave`、`legacy_` 等旧概念命名（只允许出现在本 design doc 的"前置决议变更"段引用旧决议时）。
- **Explicit Contract**：task 状态机迁移规则、journal entry 字段名、ISSUE append-only 规则、Hard Gate 条款必须显式落到 references 文档；状态查询规则（"最后一条同 ID 决定当前状态"）必须显式写明。**禁止：** 隐式约定；同一规则在 SKILL.md 与 references 出现两份不一致表述。
- **Single Source of Truth**：`story.md` 是契约 SoT（静态需求 / 必读 / 红线 / 任务计划），`journal.md` 是过程 SoT（task 状态、ISSUE 状态、决策、坑点），两者职责不重叠。**禁止：** 同一信息（如 task 当前状态）出现在两处；不允许把 journal 的状态摘要回写到 story.md。
- **Zero-Context Entry**：每个新增 / 重写的 reference 文档前 20 行说明文件职责、何时读、与其他文档的关系。**禁止：** 文档无目录、无入口说明、读起来需要先读其他三份才能理解。
- **First Principles over Analogy**：状态机和 journal 协议从"compact 抗性 + 反凭记忆"两个根本需求推导，不抄业界长任务管理模式（如 Jira workflow / GTD / Kanban）。**禁止：** 用"业界通常这样做"作为决策理由；为对称感引入未被需求要求的状态。

---

## 行动计划

### 文件结构设计

| 操作 | 文件路径 | 职责 |
|------|----------|------|
| 新增 | `docs/brainstorming/specs/2026-05-10-kickoff-state-machine-refactor.md` | 本设计文档（已写） |
| 重写 | `skills/kickoff/SKILL.md` | developer 角色、状态机概述、Hard Gate、Phase 流程、CLI Reference、References 表 |
| 重写 | `skills/kickoff/templates/story.md` | 新 story.md 模板（删 frontmatter / 加参考文档段 / 必读文件用锚点 + 验证命令 / Phase 3 Summary 段） |
| 新增 | `skills/kickoff/templates/journal.md` | journal.md 骨架与字段说明（TASK 入/出 entry、ISSUE append-only） |
| 新增 | `skills/kickoff/references/state-machine.md` | task 状态机详细规则、合法迁移、查询规则、Evidence 检查 |
| 新增 | `skills/kickoff/references/journal-protocol.md` | journal entry 字段名、追加规则、状态查询规则、grep 检索模式 |
| 重写 | `skills/kickoff/references/review.md` | 去 wave，新 reviewer 派遣选项（sub-agent / codex tmux），verdict 直接驱动状态迁移 |
| 修改 | `skills/kickoff/references/commands.md` | 去除 worktree 并行示例（与单 agent 路线冲突），调整 review dispatch 描述 |
| 修改 | `skills/kickoff/agents/code-reviewer.md` | orchestrator → developer；severity 表 LOW 注释更新；output 段说明 verdict 直接驱动 done→reviewed/needs_fix |
| 删除 | `skills/kickoff/references/story-memory-guideline.md` | 概念已废止 |
| 删除 | `skills/kickoff/references/story-summary.md` | 已并入 story.md 末尾 Summary 段 |
| 修改 | `cli/kickoff/main.py` | 删除 task 子命令组（含 wave-update）；新增 status 命令 |
| 新增 | `skills/kickoff/scripts/status.py` | omp kickoff status 实现：解析 story.md / journal.md，输出当前状态摘要 |
| 新增 | `tests/skills/kickoff/test_status.py` | T1 静态测试：journal 解析、状态查询、合法迁移、Evidence 检查 |

### 任务步骤

#### Task 1: 重写 SKILL.md 与模板

**Files:**
- 重写: `skills/kickoff/SKILL.md`
- 重写: `skills/kickoff/templates/story.md`
- 新增: `skills/kickoff/templates/journal.md`

- [ ] **Step 1: 写 SKILL.md 新骨架** — developer 角色段；状态机概述（合法迁移表）；Hard Gate（按 Step 2 列出的条款）；Phase 描述（init / 实施 + 状态机 review 循环 / E2E + Summary）；CLI Reference（archive / story init / status）；References 表（state-machine.md / journal-protocol.md / review.md / commands.md）；Storage 段保留（项目根 + .gitignore）。
- [ ] **Step 2: 写 Hard Gate 表**（替换原 wave 相关条款）：
  - 需求未澄清 → 停下让用户先澄清
  - 准备进 Phase 3，但仍有 task ∉ {reviewed, dropped} → 阻断
  - Task 从 in_progress 直接跳到 reviewed（绕过 done）→ 阻断
  - Task done 后绕过 review 直接声明完成 → 阻断
  - reviewer 在 developer 主上下文里自评 → 禁止
  - reviewer NEEDS_FIX 连续 3 次未 PASS → 停下提给用户
  - reviewer BLOCKED → 先解决 blocker 再重派
  - E2E 失败 → 修复重跑
  - omp kickoff 子命令退出码非零 → 读 stderr 处理，不静默吞错
- [ ] **Step 3: 重写 templates/story.md** — 去掉 frontmatter；新增 `## 参考文档` 段（可选，可空）；`## 必读文件` 表格用 `文件 / 锚点 / 读什么 / 验证命令` 四列；`## Out of Scope` 强制段；`## Task 计划` 列表带验收一句话；末尾 `## Summary`（注释为 Phase 3 收尾时追加）。
- [ ] **Step 4: 新建 templates/journal.md** — 顶部说明文件职责、字段名、追加规则；给出 TASK 入口 / 出口 / REVIEWED / ISSUE open / ISSUE update 五种 entry 的样板。
- [ ] **Step 5: 提交** — `feat(kickoff): rewrite SKILL.md + templates around task state machine`

#### Task 2: 调整 CLI（删 task 子命令组、加 status）

**Files:**
- 修改: `cli/kickoff/main.py`
- 新增: `skills/kickoff/scripts/status.py`

- [ ] **Step 1: 删除 task 子命令组** — 移除 `task_app`、`task_update`、`task_show`、`task_wave_update`、`app.add_typer(task_app, ...)`；同时移除文件顶部 docstring 中对 task 的描述。
- [ ] **Step 2: 新增 status 命令** — `omp kickoff status [--story <slug or YYYY-MM-DD-slug>] --story-dir <root>`；不指定 story 时报告 active story（最近一个非 archives 目录）。
- [ ] **Step 3: 实现 scripts/status.py** — 输入 story-dir + 可选 story 标识；解析 story.md 的 Task 计划列表 + journal.md 的事件流；按"最后一条同 ID 决定当前状态"规则计算每个 task 当前状态；额外计算：active in_progress task 的 Evidence 4 字段填写情况、ISSUE 当前状态、git status 未提交改动、Phase 3 ready 判断。退出码：0=成功，2=story 不存在，3=story.md/journal.md 缺失或解析失败。
- [ ] **Step 4: 提交** — `feat(kickoff): drop task subcommands, add omp kickoff status`

#### Task 3: 清理 references 与 reviewer agent

**Files:**
- 重写: `skills/kickoff/references/review.md`
- 新增: `skills/kickoff/references/state-machine.md`
- 新增: `skills/kickoff/references/journal-protocol.md`
- 修改: `skills/kickoff/references/commands.md`
- 修改: `skills/kickoff/agents/code-reviewer.md`
- 删除: `skills/kickoff/references/story-memory-guideline.md`
- 删除: `skills/kickoff/references/story-summary.md`

- [ ] **Step 1: 写 references/state-machine.md** — task 7 状态语义；合法迁移表（含禁止迁移）；查询规则（最后一条同 ID 决定当前状态）；Evidence 检查规则（in_progress task 必须 4 字段齐）；与 ISSUE 状态机的边界。
- [ ] **Step 2: 写 references/journal-protocol.md** — entry 字段名；追加规则（append-only，旧 entry 不改动）；批量 review entry 形态；ISSUE 状态查询；常用 grep 模式。
- [ ] **Step 3: 重写 references/review.md** — 去 wave；reviewer 派遣选项（默认 sub-agent；备选 tmux codex 引用 commands.md）；verdict 与状态迁移直接对应（PASS → reviewed，NEEDS_FIX → needs_fix，BLOCKED → 先解决再重派）；Reviewer Checklist 五件事保留；Severity Levels 保留。
- [ ] **Step 4: 调整 agents/code-reviewer.md** — `orchestrator` → `developer`；`review 单元 / wave` 概念替换为"自上次 reviewed 状态以来的 done task 累积 diff"；severity LOW 行注释更新；Output 段保持 PASS/NEEDS_FIX/BLOCKED。
- [ ] **Step 5: 修改 references/commands.md** — 移除 worktree 并行示例（与单 agent 路线冲突）；保留 omp dispatch 单 worker 部分（review 派遣场景仍用）；调整顶部说明从"派遣 worker 执行 task"改为"派遣 reviewer 做隔离 review"。
- [ ] **Step 6: 删除两份过期 reference** — `git rm references/story-memory-guideline.md references/story-summary.md`。
- [ ] **Step 7: 提交** — `refactor(kickoff): rebuild references around state machine + journal protocol`

#### Task 4: 同步测试

**Files:**
- 新增: `tests/skills/kickoff/__init__.py`（如不存在）
- 新增: `tests/skills/kickoff/test_status.py`
- 新增: `tests/skills/kickoff/fixtures/sample_journal.md`
- 新增: `tests/skills/kickoff/fixtures/sample_story.md`

- [ ] **Step 1: 写失败测试** — 至少覆盖：journal 解析（5 类 entry）、状态查询（最后一条同 ID 决定）、Evidence 4 字段检查（缺一不可进 in_progress）、合法迁移检测（禁止 planned → done）、批量 reviewed entry（一条 entry 推进多 task）、ISSUE append-only（旧 entry 修改应被 status 检测出）。
- [ ] **Step 2: 实现/调整 scripts/status.py 让测试通过** — 若 Task 2 已完成主体实现，本步只补缺漏。
- [ ] **Step 3: 跑 `uv run pytest tests/skills/kickoff/ -v` 确认全部 PASS**。
- [ ] **Step 4: 提交** — `test(kickoff): add status parser tests for state machine + journal protocol`

#### Task 5: 完成核查

**目的：** 防止虚报"任务完成"而实际存在遗漏或偏差。

- [ ] **Step 1: 对照本 spec 逐 Task 核查** — 打开本文档"任务步骤"，确认 Task 1-4 每个 Step 已完成（产出文件 + commit）。
- [ ] **Step 2: 对照设计方案验证无偏差** — 重读"架构"与"关键决策"段，对比已实现内容：
  - 状态机迁移表与 references/state-machine.md 一致
  - Hard Gate 与 SKILL.md 一致
  - omp kickoff status 输出与设计一致
  - 旧概念（wave / story-memory / story-summary / tasks.yaml）确认已无残留 grep 命中
- [ ] **Step 3: 跑 `omp kickoff --help` + `omp kickoff status --help` + `omp kickoff story init --help` + `omp kickoff archive --help`** — 确认 CLI 层次干净，无 task 残留。
- [ ] **Step 4: 用新 kickoff dogfood 一遍**（轻量验证）— `omp kickoff archive --story-dir stories --dry-run`；用本设计 doc 跑 `omp kickoff story init --slug kickoff-state-machine-refactor --design-doc docs/brainstorming/specs/2026-05-10-kickoff-state-machine-refactor.md --story-dir stories`；确认 story.md 与 journal.md 骨架按新模板生成。
- [ ] **Step 5: 向用户汇报** —
  ```
  ## 完成核查报告
  - 已完成 Tasks: X / 5
  - 未完成 Steps（如有）: [列举]
  - 与 spec 偏差（如有）: [列举]
  - 结论: ✅ 全部完成，无偏差 / ⚠️ 存在问题（见上）
  ```

---

## Redline 影响清单（design-guard）

本节是 design-guard 红线对照——本次重构每条产出已显式核对的红线。完整清单在对话讨论中已建立，落档摘要：

| # | Redline | 兑现方式 |
|---|---------|---------|
| 1 | brainstorming 只产 design doc，kickoff 自行 init story | 不改 brainstorming；保留 `story init --design-doc` 入参 |
| 2 | Skill 独立自治 | SKILL.md / references 不引用其他 skill 内部文件 |
| 3 | SKILL.md 渐进式披露 | 主流程进 SKILL.md，状态机规则进 references/state-machine.md，journal 协议进 references/journal-protocol.md |
| 4 | CLI 化（禁相对路径） | 所有命令走 `omp kickoff <verb>`；scripts/status.py 由 main.py 子命令调用 |
| 5 | description 精确触发 | frontmatter 不放宽 trigger（保留 `/kickoff` 显式触发） |
| 6 | tests 不放 skill 目录 | 测试统一进 `tests/skills/kickoff/` |
| 7 | Story 落项目根 + .gitignore | story.py 解析逻辑不动 |
| 8 | omp CLI 架构强制前置已完成 | 已跑 `omp kickoff --help`，已读 `cli/kickoff/main.py`，已写下层次图 |
| 9 | 默认模型原则 | status 命令不调 LLM，无 --model；reviewer 派遣保留 --model |
| 10 | Break, Don't Bend | 旧文件 / 概念整体删除，不留 alias |
| 11 | wave-JIT 决议 override | 本文档"前置决议变更"段 §A 显式记录 |
| 12 | handoff skill 独立保留 | kickoff 不发明 hook 机制；用 `omp kickoff status` 命令 |
| 13 | 清理 cli/kickoff/main.py 死代码 | Task 2 Step 1 移除 task 子命令组 |
| 14 | task 状态机入口唯一 | references/state-machine.md 写明合法迁移 + 禁止迁移；SKILL.md Hard Gate 阻断绕行 |
| 15 | ISSUE append-only | references/journal-protocol.md 写明；scripts/status.py 检测旧 entry 修改 |
