# brainstorming × coding-orchestrator Redesign
#
# 用途：brainstorming 场景化 + coding-orchestrator 渐进式拆分 + story 级显式记忆 的联合设计
# 目录：设计方案 / 假设与风险登记 / 行动原则 / 行动计划

> 将 brainstorming 重构为"方法论 + 场景路由"，为 feature 场景建立与 coding-orchestrator 的结构化交接；coding-orchestrator 从"开工前一次性写完所有 task"改为"按 wave JIT 写"，并落地 `story-memory.md` 作为 per-story 显式记忆。三件事耦合，一并设计一并实现。

## 目录

- [设计方案](#设计方案)
  - [背景与动机](#背景与动机)
  - [场景定义](#场景定义)
  - [brainstorming 主骨架与路由](#brainstorming-主骨架与路由)
  - [场景 SOP](#场景-sop)
  - [S3 → coding-orchestrator 交接契约](#s3--coding-orchestrator-交接契约)
  - [coding-orchestrator JIT 拆分](#coding-orchestrator-jit-拆分)
  - [story-memory.md 机制](#story-memorymd-机制)
  - [文件布局](#文件布局)
  - [关键决策](#关键决策)
- [假设与风险登记](#假设与风险登记)
- [Spike 计划](#spike-计划)
- [Spike 结果](#spike-结果)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 背景与动机

当前 brainstorming 与 coding-orchestrator 之间存在三个已被实测暴露的缺陷：

1. **brainstorming 是单一大 SOP，多场景压在 14 步里**：skill 设计、agent 设计、feature 开发、纯讨论、fast 小修复全部共用一条流水线，实操中大量分支靠 `Topic-specific Gate`、`Judge mode`、`Recommend execution` 几个 step 内部判断——文档难维护，agent 实际执行时也常常"走错分支"。

2. **brainstorming 与 coding-orchestrator 之间有隐式翻译层**：brainstorming 产出 `docs/brainstorming/specs/*.md`（叙事 + 行动计划），coding-orchestrator 需要重新理解这份文档、再写出 `stories/<slug>/{story.md, tasks.yaml, tasks/task-NN.md}`。两份产物描述同一件事，漂移不可避免。

3. **coding-orchestrator 一次性写完所有 task 上下文，风险高**：mindora-ui/stories/agents-teams-url-routing 有 23 个 task，task-15 / 19 / 21 的正确写法都依赖前序 task 的 E2E 反馈——如果开工前就把 23 个 task.md 写死，后续反馈无法顺畅回流，要么 task 实际跑偏、要么反复重写 spec。同 story 的 `handoff.md` 只是状态快照，不是"worker 开工前应读"的学习日志；跨 task 的 gotcha 目前只在 orchestrator 大脑里流转，压缩后即失忆。

三个问题耦合——修 brainstorming 不碰交接契约等于白修；不碰 JIT 拆分等于把 feature 场景的"一次性写死"习惯继承到新的结构里；不修记忆则 JIT 拆分缺乏反馈输入。因此合并到同一设计。

### 场景定义

brainstorming 的核心不变：**需求澄清**。在此之上把触发情形显式分成三类：

| ID | 场景 | 触发 | 产物 | 下游 |
|---|---|---|---|---|
| **S2** | Skill / Agent development | "设计 skill/agent"、"新建 skill/agent"、"skill/agent brainstorm" | design doc（用 skill/agent 模板）+ skill/agent 目录骨架 | 手工实现 或 S3 |
| **S3** | Feature / Refactoring | "开发/实现/加功能/修复/重构 X" | design doc（normal/fast 模板）+ `stories/<slug>/{story.md, tasks.yaml 骨架, tasks/task-01.md, story-memory.md}` | coding-orchestrator |
| **S1** | Open discussion | 其他一切情形（兜底） | 可选轻量 decision note，默认无产物 | 无 |

判定顺序：**匹配 S2 → 匹配 S3 → 落 S1**。触发语明确时直接进场景；模糊时（如"我想让 X 更好"）向用户抛一次 S2/S3/S1 的选择 gate，不默认落 S1——避免把有实施意图的请求吞成闲聊。

### brainstorming 主骨架与路由

`SKILL.md` 重写为**方法论框架 + 公用骨架 + 场景路由**，不再承担具体 SOP 细节。主骨架仅 4 步：

```
0. [前置] 场景判定 → 显式触发匹配 或 gate 选择
1. Explore project context — 读文件、近期 commits、skill/agent 生态
2. Ask clarifying questions — purpose / scope 为基线；其余问题启发式产生
3. Challenge Gate — 最强反对论 + 3 项检验
4. Propose approaches — Normal: 2-3 选项 + 取舍；inline 场景直给建议
↓
分流到 scenarios/{open, skill-agent, feature}.md
```

**Clarifying 问题的原则**（公用骨架与所有场景共享）：

- purpose（这件事要解决什么？）和 scope（哪些在范围内／外？）是两条**基线**——每次 brainstorming 都问。
- 其余问题必须是**启发式**的——agent 在 Explore 阶段观察到具体的模糊点 / 冲突 / 风险点之后，**针对实际发现**提出 1-3 个精准问题。
- **禁止预设场景专属 clarifying 清单**——预设等于替 agent 把思考路径写死，与 brainstorming 的核心能力冲突。场景文件可以提供**探索焦点**（看哪些文件、对齐哪些判据），但不预设提问清单。

两处顺序调整：

- **Propose approaches 放到 Risk & Spike 之前**。Risk 是对具体方案的风险，必须先有候选方案；先列 risk 会变成抽象焦虑清单。
- **Risk & Spike 移出公用骨架**，作为 S2/S3 的 SOP 组成部分。S1 不强制 risk 登记。

Visual companion 作为横切能力，不进主骨架顺序——任何一步判断视觉化有帮助时 offer 一次即可。

### 场景 SOP

#### S1 Open discussion

位置：`scenarios/open.md`

- 继续对话直到用户主动结束
- 如果讨论结论值得沉淀：可选写轻量 decision note 到 `docs/brainstorming/discussions/YYYY-MM-DD-<topic>.md`（注意：不进 `specs/`）
- 不强制 Risk & Spike、Spec review、执行链产物
- 出口：用户满意 或 用户改口转向 S2/S3（重走场景判定）

#### S2 Skill/Agent development

位置：`scenarios/skill-agent.md`

内化现有 `Path A Skill Gate` / `Path B Agent Gate` 为该场景的开头步骤：

1. 身份审问（吸收 `references/skill-fundamentals.md` / `references/agent-fundamentals.md` 的判断逻辑）
   - Skill 判定失败 → 场景退化为 S1
   - Agent 判定失败 → 自动降级到 Skill 判定
2. Risk & Spike（🔴 阻断，调用 `references/risk-and-spike.md`）
3. Present design section-by-section
4. Write design doc（`assets/skill-design-template.md` 或 `assets/agent-design-template.md`）
5. Spec review loop（调用 `spec-document-reviewer-prompt.md`）
6. 产出 skill/agent 目录骨架：
   - Skill：`skills/<name>/{SKILL.md 扉页, references/, assets/}` 空骨架
   - Agent：`agents/<name>.md` 骨架（含 frontmatter + 身份段）
7. Recommend execution：skill/agent 代码实现可选择 inline 或进入 S3

**场景探索焦点**（Explore 阶段看什么，不是预设提问）：
- 现有 `skills/` 与 `agents/` 生态（是否已有可扩展的同类）
- `references/skill-fundamentals.md` / `agent-fundamentals.md` 的身份判据
- 用户描述里是否已暗含触发语／身份／范围信号

Explore 完如果还有真实模糊，再向用户启发式追问——不预先列问题。

#### S3 Feature / Refactoring

位置：`scenarios/feature.md`

1. Risk & Spike（🔴 阻断）
2. Present design section-by-section
3. Write design doc（`assets/design-doc-template-normal.md` 或 `-fast.md`）
4. Spec review loop
5. **产出执行链四件套**（详见下节交接契约）：
   - `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story.md`（完整叙事；**顶部 `> Design: /docs/brainstorming/specs/<date>-<slug>.md` 回链**）
   - `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/tasks.yaml`（骨架，wave≥2 的 `spec: null`）
   - `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/tasks/task-01.md`（仅 wave 1，供 orchestrator 立即 dispatch）
   - `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story-memory.md`（空文件占位）
6. 移交 coding-orchestrator

**生产者 / 消费者边界**：brainstorming 是 design doc 的唯一生产者，设计文档留在 `docs/brainstorming/specs/` 作为设计理由 SSOT；coding-orchestrator 只读不写，通过 story.md 顶部回链抵达。story 目录不承载设计文档本体，避免职责扩散到 brainstorming。

**场景探索焦点**（Explore 阶段看什么，不是预设提问）：
- 涉及的代码位点与最近 commits（是否跨多个独立子系统 → 是否应拆多 story）
- 是否存在旧实现（默认按 Break-Don't-Bend 移除，不设兼容层）
- 已有 `stories/` 里的相近 story（命名、拆分粒度、story-memory 里的可复用发现）

Explore 完如果还有真实模糊，再向用户启发式追问——不预先列问题。

**Fast 分支**：单文件 + 无歧义 + 零 🔴 risk 命中时，不产 design doc、不产执行链，直接 inline 建议执行。Fast 是 S2/S3 内部的"成本模式"分支，不独立为场景。

### S3 → coding-orchestrator 交接契约

brainstorming 在 S3 结束时写的 `tasks.yaml` 骨架，必须满足以下契约：

```yaml
story: <slug>
created: 2026-04-19
updated: 2026-04-19

tasks:
  - id: "01"
    title: <action-oriented>
    status: pending
    wave: 1
    depends_on: []
    spec: tasks/task-01.md      # 仅 wave 1 非 null
    files_modified: [<预估>]
    test_layer: integration
    # worker/reviewer/started/completed/commits/notes 留 orchestrator 填

  - id: "02"
    title: <action-oriented>
    status: pending
    wave: 2
    depends_on: ["01"]
    spec: null                  # wave≥2 的 spec 由 orchestrator JIT 写
    files_modified: [<预估>]
    test_layer: component
```

**brainstorming 的边界**（生产者）：
- 必写：依赖图（`id / title / wave / depends_on`）、`test_layer`（按 decomposition Rule 1）、`files_modified` 预估
- 必写：wave 1 所有 task 的 `task-NN.md` 完整 spec（让 orchestrator 可立即 dispatch）
- 必写：`story.md` 顶部 `> Design: /docs/brainstorming/specs/<date>-<slug>.md` 回链——让消费者能一跳到设计理由
- 不写：wave ≥ 2 的 `task-NN.md`（留 orchestrator 按反馈 JIT 写）
- 必须自检：调用 `references/task-decomposition-rules.md` 的 Rule 1-5 自检清单，不通过不落盘

**coding-orchestrator 的边界**（消费者）：
- 接手 brainstorming 写好的骨架，Story Intake 从"新建"变为"校验"
- 每 wave 开工前补齐该 wave 所有 task 的 `task-NN.md`、写回 `tasks.yaml[N].spec`
- 拒绝 dispatch `spec: null` 的 task
- **不改 design doc**——对设计理由的所有修订走 brainstorming（可能触发 spec review loop 回修）

### coding-orchestrator JIT 拆分

在 SKILL.md 增一条硬约束：**dispatch wave N 之前必须读反馈写 spec**。

流程图示（以 A → {B,C,D→E} → F 为例）：

```
brainstorming 落盘：
  tasks.yaml: wave 1 = {A}, wave 2 = {B,C,D}, wave 3 = {E}, wave 4 = {F}
  task-01.md 完整写好；其余 spec: null

orchestrator 执行：
  → dispatch A (wave 1)
  → A 完成 → 读 A.commits + A.worker 报告 Deviations/Issues Found + story-memory.md
  → 写 task-02.md / task-03.md / task-04.md（wave 2）
  → dispatch {B, C, D} 并行
  → D 完成 → 再写 task-05.md（wave 3）
  → dispatch E
  → {B, C, E} 全部完成 → 写 task-06.md（wave 4）
  → dispatch F
```

**实现层面的硬约束**：

1. `scripts/task.py` 的 `update --status executing` 增加前置检查：若目标 task 的 `spec` 为 None / 缺失 / 空串（用 `not target.get("spec")` 判定，覆盖 `null` / 缺省 key / 空字符串三种情况），拒绝并返回 exit code 2，提示"JIT spec missing"。
2. `tasks.yaml` 中 `spec: null` 视为合法待写状态，不等同于错误。
3. orchestrator 对每个 wave 的"开工前准备"独立追踪（可在 tasks.yaml story 级添加 `next_wave_prepared: <int>` 字段，可选；但倾向不加，让 orchestrator 通过读 `spec == null` 自然驱动）。

**依赖判定**：wave N 开工前，需满足 wave N 内所有 task 的 `depends_on` 全部 `status: completed`。JIT 写 spec 时必须读这些依赖任务的输出。

### story-memory.md 机制

**定位**：per-story 的显式"worker/reviewer 开工前应读"学习日志。与 `handoff.md`（状态快照）正交。

**位置**：`<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story-memory.md`

**生命周期**：

1. brainstorming 在 S3 结束时创建空文件（仅含一行标题）
2. worker 每完成 task 回传"Issues Found / Deviations"段，orchestrator 判断哪些属于**跨 task 可复用发现**，提炼后 append 到 story-memory.md（不是 raw log）
3. 每 wave 开工前写新 task spec 时，orchestrator 将 `../story-memory.md` 列入 **Worker Refs** 段，worker 开工前必读
4. reviewer 同样将 story-memory.md 列为必读——避免重复提出已知 false positive
5. story 结束时，orchestrator 审视 story-memory.md：
   - 真正跨 story 可复用的条目 → **提升**到就近的 `CLAUDE.md`（代码位点本地）或 `insight` memory（项目全局）
   - 仅当前 story 相关 → 随 story 归档

**文件格式**（约定而非强制模板）：

```markdown
# Story Memory: <slug>

## Patterns
- <跨 task 复用的发现，例："fetch hooks must cancel when depended entity id changes"; 出处：task-15, task-19>

## Gotchas
- <踩过的坑，例："useEntitySessionRouting 的 entitiesReady/sessionsReady 必须区分未加载 vs 已加载为空">

## Known False Positives (for reviewers)
- <避免 reviewer 重复提出，例："store.draftInputs 不走 persist middleware 是 intentional，讨论见 task-03">
```

**反 pattern**（避免 Ralph 的 progress.txt 陷阱）：
- ❌ 把 raw worker 报告原样 append——那是日志不是记忆
- ❌ 全局 memory（跨 story）塞到 story-memory.md——用 CLAUDE.md / insight 承接
- ❌ worker 自己 append——只有 orchestrator 写入，保证是经过判断的提炼
- ❌ story 归档后再读它——归档文件只是归档，复用信息必须在归档前提升

### 文件布局

```
skills/brainstorming/
├── SKILL.md                              ← 重写：方法论 + 公用骨架 4 步 + 场景路由
├── scenarios/                            ← 新建目录
│   ├── open.md                           ← S1 SOP
│   ├── skill-agent.md                    ← S2 SOP（内化 Skill/Agent Gate）
│   └── feature.md                        ← S3 SOP（含 coding-orchestrator 交接契约）
├── references/                           ← 保留为"横切方法论与判据"
│   ├── challenge-gate.md                 ← 保留
│   ├── risk-and-spike.md                 ← 保留
│   ├── document-writing.md               ← 保留
│   ├── principles-library.md             ← 保留
│   ├── skill-fundamentals.md             ← 保留（被 scenarios/skill-agent.md 引用）
│   ├── agent-fundamentals.md             ← 保留（同上）
│   └── design-patterns.md                ← 保留（同上）
├── assets/                               ← 保留（模板）
│   ├── design-doc-template-normal.md
│   ├── design-doc-template-fast.md
│   ├── skill-design-template.md
│   └── agent-design-template.md
├── spec-document-reviewer-prompt.md      ← 保留
└── visual-companion.md                   ← 保留（横切）

skills/coding-orchestrator/
├── SKILL.md                              ← 修改：Story Intake 改为"校验"；加 JIT 硬约束
├── references/
│   ├── task-decomposition-rules.md       ← 保留（被 brainstorming S3 引用）
│   ├── handoff-guideline.md              ← 保留（与 story-memory.md 区分说明）
│   └── ...                               ← 其余保留
├── scripts/task.py                       ← 修改：status=executing 前置检查 spec != null
├── templates/
│   ├── tasks.yaml                        ← 修改：添加 spec: null 合法性说明
│   └── ...
└── worker-refs/worker-guideline.md       ← 修改：强化"Issues Found 写给下一 wave 的 orchestrator 看"

docs/brainstorming/
├── specs/                                ← 保留
└── discussions/                          ← 新建：S1 可选产出地
```

### 关键决策

- **brainstorming 不会吞掉 coding-orchestrator**：S3 只产 tasks.yaml 骨架 + wave 1 spec，task 执行、review、debug、Rule 1-5 深度校验仍属 coding-orchestrator 职责。
- **coding-orchestrator 从单次 intake 变为多次 intake**：每 wave 一次 mini-intake（读反馈 → 写下一波 spec），不再是"开工前一次性"。
- **story-memory.md 只有 orchestrator 能写**：worker 通过完成报告把候选发现传递给 orchestrator，orchestrator 提炼后 append。避免多写入方导致质量失控。
- **scenarios/ 与 references/ 分离**：scenarios/ 是"此时此刻的 SOP 走位"；references/ 是"全场景共享的判据和方法论"。职责分界清晰。
- **不预设 clarifying 清单**：公用骨架只强制 purpose + scope；其余问题由 agent 在 Explore 后启发式产生，不写死在任何文档里——预设清单会消解 brainstorming 的核心能力。
- **Fast 模式是 S2/S3 内的成本分支，不是场景**：任务类型（feature/skill/agent）与成本模式（fast/normal）是两个独立维度。
- **S1 的轻量产物路径 `docs/brainstorming/discussions/` 与 `specs/` 物理分离**：避免"重量级实施设计"和"随手对话记录"视觉混淆。
- **三件事必须一起做**：brainstorming 改 tasks.yaml 骨架输出但 orchestrator 不改 JIT，等于把一次性翻译换成 AI 翻译；改了 JIT 不加 story-memory.md，等于 JIT 缺反馈输入；有 memory 无骨架约定，等于 worker 读不到。
- **生产者 / 消费者边界清晰**：brainstorming 产 design doc（留在 specs/）+ story 骨架；coding-orchestrator 只消费不回写设计本体。story.md 顶部链接到 design doc，不拷贝也不搬迁——职责不扩散。

---

## 假设与风险登记

| # | 假设/赌注 | 类别 | 错了的代价 | 处理 |
|---|----------|------|-----------|------|
| A1 | 3 场景（S1/S2/S3）能覆盖当前 brainstorming 的所有触发情形 | 🟡 | 遗漏场景导致新的 gate 分支被塞进 SKILL.md | 审核现有 specs/ 最近 20 篇 design doc，确认全部可归类到 3 场景；如不能则补 S4 |
| A2 | brainstorming 写 tasks.yaml 骨架时调用 Rule 1-5 自检，能产出与 orchestrator 自己拆分同等质量的任务图 | 🟡 | 骨架质量差，orchestrator 大量重写 | scenarios/feature.md 里显式要求"写完 tasks.yaml 后跑一遍 self-check 清单"；失败就改到通过 |
| A3 | wave ≥ 2 的 spec 由 orchestrator JIT 写，信息密度不会低于当前一次性写完的做法 | 🟡 | 后续 wave 的 spec 质量变差 | 反向论证：实测 story 里 task-15/19/21 都是反馈驱动写成的——JIT 本质上是把"事实如此"扶正 |
| A4 | story-memory.md 作为必读文件加入 task spec 的 Worker Refs 后，worker 真的会读并受益 | 🟡 | worker 忽略，memory 沦为摆设 | worker-guideline 强化"先读 Worker Refs"；完成报告模板加一行"story-memory.md 中哪些条目影响了本次实现" |
| A5 | `scripts/task.py` 加 `spec != null` 前置检查不会破坏现有正在跑的 story | 🟡 | 已有 story 的 tasks.yaml 不符合新契约，orchestrator 卡死 | 检查逻辑只在 `status: pending → executing` 时触发；老 story 如全 pending 可补 spec 后继续 |
| A6 | 现有 `skill-fundamentals.md` / `agent-fundamentals.md` / `design-patterns.md` 内容能平移到 scenarios/skill-agent.md 的 SOP 里，保留原信息 | 🟢 | 仅文件位置调整，内容不变 | 迁移时 diff 对比确认无信息损失 |
| A7 | `docs/brainstorming/discussions/` 作为 S1 轻量产物地，不会被误当成 `specs/` | 🟢 | 用户把 discussion 当设计文档引用 | SKILL.md 说明路径语义；S1 场景里明确标注"非实施依据" |

**无 🔴 风险**。所有关键行为由现有代码（`task.py`、SKILL.md 加载机制）和已验证的 story 实测（mindora-ui/stories）支撑，不需要跑 throwaway 代码回答。

---

## Spike 计划

无 🔴 风险，skip。

---

## Spike 结果

无。

---

## 行动原则

- **TDD: Red → Green → Refactor**：`scripts/task.py` 的 JIT 前置检查先写失败测试（模拟 `spec: null` 的 task 调 executing，断言 exit code 2），再实现；scenarios/\*.md 的 SOP 先写"预期 agent 行为"的测试用例（触发语 → 走到正确场景 → 产出正确文件），再实现。**禁止**：先写 SOP 再补验证。
- **Break, Don't Bend**：不保留旧 SKILL.md 的 14 步主流程作为兼容层；Skill/Agent Gate 的逻辑直接搬进 scenarios/skill-agent.md，旧 step 2 彻底删除。**禁止**：`legacy`、`v1/v2`、兼容别名。
- **Zero-Context Entry**：新 SKILL.md 开头明确"这是方法论 + 场景路由，具体 SOP 在 scenarios/"；scenarios/\*.md 各自开头声明"本文件是 S\<N\> 的完整 SOP，假设已走完公用骨架"。**禁止**：让 agent 读 2+ 文件才知道当前走到哪。
- **Explicit Contract**：`tasks.yaml` 骨架的 `spec: null` 约定、`story-memory.md` 的"orchestrator-only write"约定、`scripts/task.py` 的拒绝条件——全部显式文档化。**禁止**：隐式约定。
- **Minimum Blast Radius**：先交付三件事最小闭环（场景路由 + JIT 检查 + story-memory 读写约定），暂不动 `insight` 提升机制、不动 Fast 分支的细节调优。**禁止**：在首个 PR 混入无关优化。
- **Single Source of Truth**：`tasks.yaml` 仍是 task 状态 SSOT；`story-memory.md` 是学习发现 SSOT；`design doc`（specs/）是设计理由 SSOT。三者边界不重叠。**禁止**：同一信息出现在两处。

---

## 行动计划

### 文件结构设计

#### Plan A：brainstorming 重构

| 操作 | 文件路径 | 职责 |
|------|----------|------|
| 重写 | `skills/brainstorming/SKILL.md` | 方法论 + 公用骨架 4 步 + 场景路由（目标 < 100 行） |
| 新增 | `skills/brainstorming/scenarios/open.md` | S1 SOP |
| 新增 | `skills/brainstorming/scenarios/skill-agent.md` | S2 SOP（内化 Skill/Agent Gate 流程） |
| 新增 | `skills/brainstorming/scenarios/feature.md` | S3 SOP（含 coding-orchestrator 交接契约） |
| 保留 | `skills/brainstorming/references/*.md` | 横切方法论与判据，不动内容 |
| 保留 | `skills/brainstorming/assets/*.md` | 模板，不动内容 |
| 新增 | `docs/brainstorming/discussions/.gitkeep` | 占位 S1 产物目录 |

#### Plan B：coding-orchestrator 的 JIT 改造

| 操作 | 文件路径 | 职责 |
|------|----------|------|
| 修改 | `skills/coding-orchestrator/SKILL.md` | Story Intake 改为"校验 brainstorming 骨架"；Task Breakdown 改为"每 wave 开工前 JIT 写"；加 `spec != null` 硬规则 |
| 修改 | `skills/coding-orchestrator/scripts/task.py` | `cmd_update`：若 `args.status == "executing"` 且 target.spec 为 None，返回 exit 2，打印 `JIT spec missing for task <id>` |
| 修改 | `skills/coding-orchestrator/templates/tasks.yaml` | 注释里声明 `spec: null` 合法，含义是"待 orchestrator JIT 写" |
| 修改 | `skills/coding-orchestrator/worker-refs/worker-guideline.md` | 完成报告模板增一行"Story-memory impact: 本次实现是否验证/更新了 story-memory 中的假设" |
| 新增 | `skills/coding-orchestrator/tests/test_task_jit_gate.py` | `status=executing` + `spec=null` 时拒绝；`spec != null` 时通过 |

#### Plan C：story-memory 落地

| 操作 | 文件路径 | 职责 |
|------|----------|------|
| 新增 | `skills/coding-orchestrator/references/story-memory-guideline.md` | story-memory.md 写入/提升规则，orchestrator-only write 约束，反 pattern |
| 修改 | `skills/coding-orchestrator/templates/task.md` | Worker Refs 段模板添加 `../story-memory.md — 本 story 累积的 gotcha / pattern / known false positives` |
| 修改 | `skills/brainstorming/scenarios/feature.md` | 结束动作包含"创建空的 story-memory.md 占位"步骤 |

#### Plan D：交接契约测试

| 操作 | 文件路径 | 职责 |
|------|----------|------|
| 新增 | `skills/brainstorming/tests/test_scenario_routing.py`（或同等文档化测试） | 触发语 → 场景判定；覆盖 S2/S3/S1 兜底三条路径 |
| 新增 | `skills/brainstorming/tests/fixtures/feature-dispatch/` | 一个假 feature 场景的骨架产物（tasks.yaml、task-01.md、story-memory.md 空壳），供 orchestrator 测试消费 |
| 新增 | `skills/coding-orchestrator/tests/test_intake_from_brainstorming.py` | 读 fixtures → 校验 → 可以直接 dispatch wave 1 |

### 任务步骤

#### Task 1：建立场景骨架（brainstorming 侧）

- 1.1 新建 `skills/brainstorming/scenarios/` 目录
- 1.2a 写 `scenarios/open.md`：S1 SOP（轻量、无强制产物、可选 discussion note）
- 1.2b 写 `scenarios/skill-agent.md`：S2 SOP，吸收现有 Skill/Agent Gate 逻辑 + `references/skill-fundamentals.md` / `agent-fundamentals.md` 的身份判据，内化场景探索焦点
- 1.2c 写 `scenarios/feature.md`：S3 SOP，含交接契约（tasks.yaml 骨架 + wave 1 spec + story.md 回链 + story-memory.md 占位）
- 1.3 重写 `skills/brainstorming/SKILL.md` 为 < 100 行骨架 + 路由
- 1.4 删除旧 SKILL.md 里被场景吸收的 Topic-specific Gate、Judge mode、Recommend execution 等 step
- 1.5 `docs/brainstorming/discussions/` 建目录 + `.gitkeep`

**验证**：读新 SKILL.md < 100 行；手动用三条触发语（"设计 skill X"、"开发功能 Y"、"我想聊聊 Z"）走一遍，能正确路由到对应 scenarios/\*.md。

#### Task 2：coding-orchestrator JIT 前置检查

- 2.1 确认 `skills/coding-orchestrator/` 下的 pytest 约定：若无 `tests/` 目录则新建；运行方式统一为 `uv run pytest skills/coding-orchestrator/tests/`
- 2.2 先写 `tests/test_task_jit_gate.py`：构造 `spec: null` / 缺 `spec` key / `spec: ""` 三种 task，调 `cmd_update --status executing`，均断言 exit 2 + 错误消息；再构造 `spec: tasks/task-01.md` 的 task，断言正常通过
- 2.3 修改 `scripts/task.py::cmd_update`：status 切换到 executing 时用 `not target.get("spec")` 判定
- 2.4 跑测试，通过
- 2.5 **迁移保护**：`grep -l "spec: null" stories/*/tasks.yaml` 列出当前含 JIT-待写位的 story；若存在 `status: executing` + `spec: null` 组合，文档化处理（补 spec 或改回 pending）再启用检查

**验证**：单元测试绿；在真实 story 上手测一次（先把某 pending task 的 spec 清为 null，尝试 executing，应拒绝）。

#### Task 3：story-memory 规范

- 3.1 写 `skills/coding-orchestrator/references/story-memory-guideline.md`（写入规则 + 反 pattern + 生命周期）
- 3.2 修改 `skills/coding-orchestrator/templates/task.md`（task-NN.md 生成模板）的 Worker Refs 段，默认列入 `../story-memory.md`
- 3.3 修改 `skills/coding-orchestrator/worker-refs/worker-guideline.md` 的完成报告模板

**验证**：新建一个空的 story-memory.md，按一个小 feature 走完整 S3 → coding-orchestrator 流程，确认 orchestrator 在 task-01 完成后向 story-memory.md append 至少 1 条条目。

#### Task 4：交接契约测试

- 4.1 新建 fixtures：一个假 feature 的 tasks.yaml（骨架，wave 1 spec 完整，其余 null）+ task-01.md + story.md（含 `> Design:` 回链）+ story-memory.md 空壳
- 4.2 写 `skills/coding-orchestrator/tests/test_intake_from_brainstorming.py`：加载 fixtures → 调 orchestrator Story Intake 校验逻辑 → 断言可以 dispatch wave 1 task-01；运行方式 `uv run pytest skills/coding-orchestrator/tests/`
- 4.3 写 brainstorming 侧测试（或 `skills/brainstorming/tests/routing.md` 文档化自检清单）：触发语 → 场景判定路径；覆盖 S2/S3/S1 兜底三条路径

**验证**：两侧测试绿；手动从一个空白 topic 开始，走完 brainstorming S3 → coding-orchestrator intake → dispatch task-01，不需要任何人工修复 yaml 或 spec。

#### Task 5：SKILL.md 相互引用清理

- 5.1 brainstorming 的 `scenarios/feature.md` 显式链接到 coding-orchestrator 的交接契约说明
- 5.2 coding-orchestrator 的 SKILL.md 的 Story Intake 段显式说明"若来自 brainstorming，直接校验；若无，回退到自建骨架"

**验证**：
- 每个 `scenarios/*.md` 至少被新 `SKILL.md` 引用一次
- `coding-orchestrator/SKILL.md` 的 Story Intake 段明确指向 brainstorming S3 交接契约章节（或其文档位置）
- 读一遍两个 SKILL.md + 被引用文档，不存在循环依赖或文档孤岛

#### Task 6：完成核查

- 6.1 逐条对照 Task 1-5 的 bullet，确认全部已做、全部 verify 通过
- 6.2 回读本设计文档的 设计方案、假设与风险登记、行动原则 三节，确认实现与设计无静默偏差
- 6.3 跑一遍 `skills/brainstorming/tests/` + `skills/coding-orchestrator/tests/` 全部测试，确认绿
- 6.4 向用户报告：已完成 task X/6、未完成 step 列表（应为空）、spec 偏差（应为无）、最终结论 ✅/⚠️

#### Task 7：文档更新

- 7.1 更新 `skills/brainstorming/SKILL.md` description 字段，加入 feature/refactoring 触发语
- 7.2 更新 `skills/coding-orchestrator/SKILL.md` 说明"已支持来自 brainstorming 的骨架直接接手"
- 7.3 更新 `CLAUDE.md` 或 `PROJECT.md` 中 brainstorming / coding-orchestrator 相关章节（若有）
- 7.4 更新 README / 中文 README 对应条目（若有）

**验证**：关键入口文档均反映新结构，新 agent 读任一入口都能走到正确 SOP。
