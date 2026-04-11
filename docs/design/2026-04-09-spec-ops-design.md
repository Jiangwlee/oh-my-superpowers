# Coding Orchestrator Skill

> Spec-driven sub-agent orchestration skill，面向复杂/长任务，通过 spec 驱动 + 角色分离，确保 Opus 主会话保持架构级全局视角。

## 目录

- [背景与痛点](#背景与痛点)
- [设计方案](#设计方案)
  - [核心理念](#核心理念)
  - [角色分工](#角色分工)
  - [Pipeline](#pipeline)
  - [Task Spec 设计](#task-spec-设计)
  - [Handoff 机制](#handoff-机制)
  - [失败策略](#失败策略)
  - [存储结构](#存储结构)
- [调试方法论](#调试方法论)
- [Skill 实现设计](#skill-实现设计)
  - [目录布局](#目录布局)
  - [SKILL.md 设计](#skillmd-设计)
  - [References 设计](#references-设计)
  - [Hooks 设计](#hooks-设计)
  - [安装方式](#安装方式)
- [与现有 Skill 的关系](#与现有-skill-的关系)
- [竞品分析](#竞品分析)
- [开放问题](#开放问题)

---

## 背景与痛点

**场景**：复杂任务（多文件、多步骤、长会话）

**核心痛点**：Claude 上下文压缩（compaction）时损失信息精度。当 Opus 既做架构又写代码，上下文被代码细节填满，压缩后全局视角丢失。

**Karpathy 观察的延伸**：LLM 不仅在单次交互中过度工程、隐藏假设，在长会话中还会因上下文压缩丢失关键决策和约束，导致后半程行为漂移。

---

## 设计方案

### 核心理念

1. **Spec-Driven**：Spec 是质量的关键。每个 task 有完整 spec，包含充足上下文、IRON LAW 和验收标准。Spec 不是给 sub agent 戴手铐，而是把任务边界、规则和交付标准讲清楚。
2. **角色分离**：Opus 做 architect/orchestrator，不碰代码；编码、设计、测试、调试全部委托。
3. **外部化记忆**：Spec 文件 + progress 追踪是对抗 compaction 的核心手段。

### 角色分工

| 角色 | 执行者 | 职责 | 不做什么 |
|------|--------|------|----------|
| **Orchestrator** | Opus（主会话） | 需求理解、任务拆分、spec 编写、编排派遣、二次判断 review 结果、验收 | 不写代码、不做 design、不做 review |
| **Worker** | Sub Agent (Sonnet) | Explore → Design → Coding（连续执行）、测试、调试 | 不做架构决策 |
| **Reviewer** | Codex（优先）/ Sonnet Sub Agent（fallback） | 多维度 Code Review | 不做修复 |

**关键约束**：
- Worker 的 explore/design/coding 是一个 sub agent 连续完成，不分三次派遣（保持上下文连续）
- Review 结果由 Orchestrator 二次判断，只有 Opus 确认是问题的才需要修复
- 修复动作由 Orchestrator 直接完成（不再委托）
- 验收由 Orchestrator 亲自执行
- **Sub agent iteration limit**：单个 task 的编码尝试不超过 3 轮，超过则升级

### Pipeline

```
[用户发起 story（通常来自 brainstorming）]
    │
    ▼
Phase 0: Story Intake
    Orchestrator 理解需求，关联 brainstorming 设计文档
    产出：./stories/<story-name>/story.md
    │
    ▼
Phase 1: Task Breakdown
    Orchestrator 拆分 task，为每个 task 创建 spec
    spec 引用 brainstorming 阶段的设计文档
    产出：./stories/<story-name>/tasks/task-01.md, task-02.md ...
    │
    ▼
Phase 2: Execute（per task，Opus 按依赖顺序分发，无依赖可 worktree 并行）
    Sub Agent (Sonnet) 自己读 spec 文件 + coding-guideline.md，连续执行：
    ├─ Explore：阅读相关代码和文档
    ├─ Design：数据结构、接口设计
    └─ Coding：实现代码
    │
    ▼
Phase 3: Review（per task）
    Codex（优先）或 Sonnet Sub Agent（Codex 不可用时）执行 Code Review
    Sub agent 自己读 spec 文件获取 review 上下文
    → Orchestrator 二次判断 review 结果
    → 确认是问题的，由 Orchestrator 直接修复
    │
    ▼
Phase 4: Test & Debug（per task）
    Sub Agent 执行测试
    失败 → 日志驱动调试（引用 debugging reference）
    │
    ▼
Phase 5: Acceptance
    Orchestrator 逐条验收 spec 中的 acceptance criteria
    全部通过 → 标记 task 完成
    │
    ▼
[所有 task 完成] → Story 收尾
```

### Task Spec 设计

**粒度**：类比敏捷开发，Story → Task。一个 Task Spec 对应一个可独立验收的功能切片。

**Spec 重点不在于 how to implement，而在于**：
- 提供充足上下文（让 sub agent 理解全貌）
- 明确验收标准（让 sub agent 知道"做到什么程度算完"）

**模板结构**：

```markdown
# Task: <名称>

## Context
<!-- 为什么要做这件事，story 背景 -->
<!-- 链接到 brainstorming 设计文档 -->

## Objective
<!-- 做什么，不做什么 -->

## Read First
<!-- 强制 sub agent 在修改前先读这些文件，防止盲改 -->
<!-- 精确到文件+行号，不给整个目录 -->
- `src/auth/login.ts:1-50` — 理解现有登录流程
- `src/auth/types.ts` — 了解已有类型定义
- `docs/design/xxx.md` — 相关设计文档

## File Scope
<!-- 明确 sub agent 可以修改的文件范围 -->
<!-- 未列出的文件禁止修改 -->
- `src/auth/login.ts` — 主要修改目标
- `src/auth/types.ts` — 可能需要新增类型
- `tests/auth/login.test.ts` — 测试文件

## Workflow
<!-- explore → design → coding 的引导 -->
<!-- 精确到文件+行号的 references，不给"整个目录" -->

## References
<!-- 相关文件路径（精确到文件+行号）、文档链接、参考实现 -->

## Deviation Rules
<!-- 四级自治权控制（借鉴 GSD executor） -->
🟢 Auto-fix: 
- Bug 修复（不改接口签名）
- 补充缺失的 import/export

🟡 Auto-add:
- 关键功能缺失（如缺少错误处理导致崩溃）
- 测试用例补充

🟠 Auto-fix blocking:
- 依赖冲突导致编译失败
- 类型不匹配

🔴 Ask orchestrator:
- 修改公共 API 接口签名
- 添加新依赖
- 修改 File Scope 之外的文件

## IRON LAW
<!-- 引用路径 + 当前任务的针对性约束，不全文复制 -->
遵循编码准则（参考 references/coding-guideline.md）：
- Think Before Coding → Simplicity First → Surgical Changes → Goal-Driven

分析瘫痪检测：连续 5+ 次读文件不做任何修改 = 卡住。卡住时必须：
1. 写下当前理解和困惑
2. 选择最小可行的改动开始执行
3. 如果仍无法推进，向 Orchestrator 报告阻塞原因

本任务额外约束：
- <任务特定的硬性约束>

## Acceptance Criteria
<!-- 可验证的验收条件列表 -->

### Must-Haves（goal-backward 验收，借鉴 GSD）
<!-- truths: 必须为真的行为断言 -->
<!-- artifacts: 必须存在的产物 + 校验条件 -->
<!-- key_links: 关键依赖关系 + regex 验证 -->
truths:
- "<从用户视角描述的行为，如：用户可以登录>"

artifacts:
- path: "src/auth/login.ts"
  provides: "<这个文件提供什么>"
  contains: "<必须包含的关键代码模式>"

key_links:
- from: "src/auth/login.ts"
  to: "src/auth/types.ts"
  pattern: "import.*from.*types"

## Test Plan
<!-- 测试策略和关键用例 -->

## Progress
<!-- Pipeline 各阶段状态，由 Orchestrator 更新 -->
- [ ] Execute
- [ ] Review
- [ ] Test
- [ ] Acceptance
```

**Sub agent 上下文管理约束**：
- **Spec 读取方式**：sub agent 自己读 spec 文件（`./stories/<story>/tasks/task-XX.md`），Opus 不把 spec 全文塞进 prompt。prompt 只包含 spec 文件路径 + 必读的 `references/coding-guideline.md` 路径
- **无 spec 场景**：仅当没有 spec 文件时（如临时修复），才通过 prompt 注入任务描述
- References 精确到文件+行号，不给整个目录
- 编码任务最好是单文件或少量文件的改动
- 如果一个 task 涉及太多文件，说明拆分不够细

### Handoff 机制

**问题**：Opus 上下文压缩（compaction）后如何恢复全局视角？

**双模式 Handoff**：

**模式 1：自动（PreCompact + PostCompact hook）**

利用 Claude Code 的 hooks，在 compaction 前后自动保存和恢复状态。不依赖 transcript 解析（复杂且脆弱），而是直接从 story 文件中提取当前状态。

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run $OMP_HOME/skills/coding-orchestrator/scripts/handoff.py --auto --story-dir ./stories",
            "timeout": 10000
          }
        ]
      }
    ],
    "PostCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run $OMP_HOME/skills/coding-orchestrator/scripts/restore.py --story-dir ./stories",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

- PreCompact → `handoff.py` 从 story 文件提取状态写入 `./stories/<story>/handoff.md`
- PostCompact → `restore.py` 读 `handoff.md` 写入 `./stories/.handoff-context`

**恢复方式（方案 A）**：PostCompact 的 stdout 不会注入 Claude 上下文，因此 `restore.py` 把 handoff 内容写入固定文件 `./stories/.handoff-context`。SKILL.md 指示 Opus 在 compaction 后主动读此文件恢复状态。

**模式 2：手动（slash command）**

用户主动调用 `/<skill>:handoff`，保存更详细的状态（包含当前推理上下文和决策理由）。

**建议时机**：在上下文使用率达到 60-85% 时主动触发，不要等到自动 compaction（~92%）。

**Handoff 文件内容**：
- 当前 story 进度（哪些 task 完成，哪些进行中）
- 未完成 task 的当前状态和阻塞原因
- 关键决策和上下文（压缩后会丢失的部分）
- 下一步行动计划

### 失败策略

编码/测试/调试任务的逐级升级：

```
Sub Agent (Sonnet) 失败（或 3 轮未解决）
    → Fallback: Codex（如可用）或另一个 Sonnet Sub Agent
        → Fallback: Opus 亲自接手（仅限当前失败任务）
```

每次升级都携带前一级的失败信息和错误日志。

### 存储结构

```
./stories/                          # 加入 .gitignore
├── .handoff-context                # PostCompact 恢复文件（Opus compaction 后主动读取）
└── <story-name>/
    ├── story.md                    # Story 概述 + 全局进度
    ├── handoff.md                  # Handoff 状态（自动/手动生成）
    └── tasks/
        ├── task-01.md              # Task Spec（含 progress）
        ├── task-02.md
        └── ...
```

---

## 调试方法论

作为独立 reference（`references/debugging-guideline.md`），在测试失败时由 Opus 指示 sub agent 加载。

**核心流程**（日志驱动，禁止猜测）：

1. **先列可能原因**：列出 5-7 个可能原因和对应的诊断方法，不写代码
2. **在关键路径插入诊断日志**：输出到日志文件，覆盖可疑路径
3. **运行并读日志**：通过日志输出缩小问题范围至文件/函数级别
4. **缩小范围后读代码**：定位根因
5. **修复并验证**
6. **清理临时日志**：移除所有诊断日志，恢复代码卫生

**chrome-devtools 使用规则**（仅限前端问题）：
- 先用 devtools 观察问题页面现象
- 然后通过日志缩小范围
- 修复后再用 devtools 验证

**禁止行为**：
- 纯靠硬读代码猜测问题（YOLO fixing）
- 使用 chrome-devtools 反复试验代替系统排查
- 同时修改多个文件不逐步验证

---

## Skill 实现设计

### 目录布局

```
skills/coding-orchestrator/
├── SKILL.md                        # Pipeline 模式：主流程骨架 + 触发条件
├── hooks.json                      # omp install 自动合并到 settings.json
├── references/
│   ├── spec-template.md            # Task Spec 模板（含 Read First/Deviation Rules/Must-Haves）
│   ├── coding-guideline.md         # 全局编码准则（karpathy 完整内容），所有 sub agent 必读
│   ├── debugging-guideline.md      # 日志驱动调试方法论
│   ├── worker-guideline.md         # Sub agent 行为协议（分析瘫痪检测、iteration limit、输出规范）
│   └── handoff-guideline.md        # Handoff 文件格式 + 手动触发时机 + 恢复流程
├── scripts/
│   ├── handoff.py                  # PreCompact hook：从 story 文件提取状态 → handoff.md
│   └── restore.py                  # PostCompact hook：读 handoff.md → ./stories/.handoff-context
└── tests/
    └── t1_static.py                # SKILL.md 合规 + 引用文件存在性检查
```

**设计决策**：
- **无 assets/ 目录**：spec-template 放 references/（给 Opus 按需读取写 spec，不是机械填充模板）
- **无 cli/ 模块**：本 skill 核心是 Opus 编排行为，不需要独立 CLI 入口。scripts 只服务 hooks，不对外暴露
- **references 命名规范**：`*-guideline.md` 为行为规范类，`*-template.md` 为模板类
- **coding-guideline.md**：完整拷贝 karpathy skill 内容（不做提取精华），是所有 sub agent 的全局行为约束

### SKILL.md 设计

**设计模式**：**Pipeline**（严格多步骤工作流，带检查点）

**frontmatter**：

```yaml
---
name: coding-orchestrator
description: >-
  Use when tackling complex, multi-file features or long-running tasks that
  risk context degradation. Orchestrates Opus as architect (no coding) with
  Sonnet sub-agents as workers and Codex/Sonnet as reviewer. Each task gets
  a detailed spec with context, boundaries, and acceptance criteria.
  Sub agents read spec files directly — no prompt injection needed.
  Do NOT use for simple single-file changes or quick bug fixes.
---
```

**body 骨架**（渐进式披露）：

```markdown
# Coding Orchestrator: Spec-Driven Sub-Agent Orchestration

<HARD-GATE>
Opus 不写代码。所有编码、设计、测试、调试通过 sub agent 完成。
违反此规则 = 流程失败。
</HARD-GATE>

## Pipeline

1. **Story Intake** — 理解需求，创建 `./stories/<name>/story.md`
2. **Task Breakdown** — 拆分 task，每个 task 创建 spec；read `references/spec-template.md`
3. **Execute** — 派遣 Sonnet sub agent（worktree 隔离）；read `references/worker-guideline.md`
   - Sub agent 必须先读 `references/coding-guideline.md`
4. **Review** — Codex（优先）或 Sonnet review + Opus 二次判断
5. **Test & Debug** — 失败时 read `references/debugging-guideline.md`
6. **Acceptance** — 逐条验收 must_haves

## Sub Agent Spec 读取
Sub agent 自己读 spec 文件，Opus 不注入 spec 全文到 prompt。
prompt 只给：spec 文件路径 + `references/coding-guideline.md` 路径。

## Compaction Recovery
context 压缩后，读 `./stories/.handoff-context` 恢复状态。
详见 `references/handoff-guideline.md`。

## Failure Escalation
Sub Agent (Sonnet) → Codex/Sonnet → Opus 亲自接手（仅限当前失败任务）
```

**关键点**：SKILL.md 只放 pipeline 骨架（每步一句话 brief）+ HARD-GATE。详细规则全部下沉到 references，按需加载。

### References 设计

| 文件 | 内容 | 加载时机 | 读取者 |
|------|------|----------|--------|
| `spec-template.md` | Task Spec 完整模板（Read First / Deviation Rules / Must-Haves） | Phase 1 拆 task 时 | Opus |
| `coding-guideline.md` | Karpathy 四原则完整内容 + 代码示例（❌/✅ 对比） | 每个 sub agent 启动时 | Sub Agent |
| `debugging-guideline.md` | 日志驱动调试 6 步 + chrome-devtools 使用规则 + 禁止行为 | Phase 4 测试失败时 | Sub Agent |
| `worker-guideline.md` | 分析瘫痪检测（5+ 读不动）、iteration limit（3 轮）、File Scope 硬边界、输出格式 | Phase 2 写 sub agent prompt 时 | Opus → 注入 Sub Agent |
| `handoff-guideline.md` | handoff.md 文件格式、手动触发时机（60-85%）、.handoff-context 恢复流程 | 主动 handoff 或 compaction 后 | Opus |

**总共 5 个 references**，符合渐进式披露——Opus 在不同 phase 按需加载，不一次全读。

### Hooks 设计

通过 `hooks.json` 声明，`omp install skill coding-orchestrator` 时由 `lib/omp_hooks.py` 自动合并到 `settings.json`，卸载时通过 `_omp_skill` 标记精准移除。

| Hook | 脚本 | 作用 |
|------|------|------|
| PreCompact | `scripts/handoff.py --auto` | 从 story 文件提取当前进度 → `./stories/<story>/handoff.md` |
| PostCompact | `scripts/restore.py` | 读 `handoff.md` → 写入 `./stories/.handoff-context` 供 Opus 主动读取 |

**PostCompact 的 stdout 不会注入 Claude 上下文**（hooks.md 文档明确），因此采用**方案 A**：restore.py 写文件，SKILL.md 指示 Opus compaction 后主动读 `./stories/.handoff-context`。

脚本规范：
- PEP 723 inline dependencies（`uv run` 执行）
- `--help` 支持
- 结构化错误输出
- 无交互式 prompt

### 安装方式

标准 omp 安装，无特殊处理：

```bash
# 局部安装（当前项目）
omp install skill coding-orchestrator

# 全局安装
omp install skill coding-orchestrator --global
```

安装时 `omp` 自动（`bin/omp:641-681`）：
1. Symlink `skills/coding-orchestrator/` → 目标位置
2. 合并 `hooks.json` → 对应 `settings.json`（局部 → `.claude/settings.json`，全局 → `~/.claude/settings.json`）
3. 附带 `_omp_skill: "coding-orchestrator"` 标记

卸载时自动按标记清理 hooks。无额外依赖。

---

## 与现有 Skill 的关系

| Skill | 关系 |
|-------|------|
| **brainstorming** | 上游：brainstorming 产出设计文档，本 skill 引用 |
| **code-review** | 独立并存：code-review 服务日常小任务，本 skill 服务大任务中的 review 阶段 |
| **team** | 底层工具：作为 codex 派遣的 fallback 机制 |
| **insight** | 下游：调试经验可沉淀到 insight |

本 skill 不替代任何现有 skill。

---

## 竞品分析

基于 deep-research 调研（2026-04-09，17 个来源）+ 竞品源码阅读。完整报告见 `~/.local/share/oh-my-superpowers/deep-research/2026-04-09T07-20-coding-orchestrator-research/reports/`。

### 最接近竞品：GSD (Get Shit Done, 48K stars)

**GSD 概况**：独立 npm 包（`npx get-shit-done-cc@latest`），24 个 specialized agents + 68 个 slash commands + 9 个 hooks，自称 "spec-driven development system"。支持 Claude Code、Copilot、Gemini CLI 等多 runtime。

**源码阅读的关键发现**：

| GSD 能力 | 实现方式 | 评价 |
|----------|----------|------|
| Wave-based 并行 | frontmatter 预计算 `wave` 字段，execute-phase 按 wave 分组并行派遣 subagent | 成熟，值得借鉴 |
| `must_haves` 验收 | goal-backward：`truths`（行为断言）+ `artifacts`（产物+校验）+ `key_links`（regex 验证依赖） | 比 checklist 更可靠 |
| `read_first` 字段 | task 模板强制声明执行前必读的文件列表 | 简单有效，防止盲改 |
| Deviation Rules | 4 级自治权：auto-fix bugs → auto-add critical → auto-fix blocking → ask architectural | 比 Always/Ask/Never 更细致 |
| 分析瘫痪检测 | 连续 5+ 次读文件不做修改 = 卡住信号 | 实用防护 |
| Fix attempt limit | 每 task 最多 3 次修复，超过 checkpoint + 上报 | 与我们设计一致 |
| checkpoint 模式 | `checkpoint:human-verify`、`checkpoint:decision`、`checkpoint:human-action` | 优雅的人机协作 |
| 认知偏见框架 | debugger agent 列出 Confirmation/Anchoring/Availability/Sunk Cost bias 自检 | 有趣但 prompt 膨胀 |

**为什么不能直接用 GSD**：

| 差距 | 说明 |
|------|------|
| **没有模型路由** | GSD 用同一个模型做所有事。我们的核心是 Opus 编排 + Sonnet 执行 + Codex Review——成本/质量分离。GSD 完全没有这个概念 |
| **不是 Skill，不能组合** | GSD 是独立 npm 包，自成体系。装进来会接管整个工作流，不能作为 omp 生态中的可组合能力单元（无法与 brainstorming、round-table 等协作） |
| **不支持 Pi runtime** | GSD 深度绑定 Claude Code slash command 系统，68 个 `/gsd-*` 命令在 Pi 里跑不了。我们要求 skill runtime 无关 |
| **太重** | 24 agents + 68 commands + workflows + templates。我们要的是单 skill，Opus 读完 SKILL.md 就能编排 |
| **无 compaction 对抗** | GSD 有 context monitor 但没有 PreCompact hook 自动外化状态。GSD 策略是"在 context 爆之前做完"，我们是"爆了也能无损恢复" |

**从 GSD 源码借鉴的设计改进**：

| # | 改进 | 来源文件 | 融入方式 |
|---|------|----------|----------|
| 1 | Spec 增加 `read_first` 字段 | `templates/phase-prompt.md` | Task Spec 模板新增 Read First section |
| 2 | 分析瘫痪检测（5+ 读不动） | `agents/gsd-executor.md` | Worker 行为约束加入 IRON LAW |
| 3 | Deviation Rules 4 级自治权 | `agents/gsd-executor.md` | 替换 Boundaries 三层为四级 Deviation Rules |
| 4 | `must_haves` goal-backward 验收 | `templates/phase-prompt.md` | Task Spec 的 Acceptance Criteria 增加 must_haves 结构 |

### 其他竞品源码分析

| 项目 | 源码发现 | 借鉴价值 |
|------|----------|----------|
| **claude-code-workflow-orchestration** | Orchestrator Stub 模式：主 agent 完全禁止工具调用，只 delegate。`compact_run.py` 包裹命令输出压缩为一行 | Stub 太激进（Opus 需要读文件做 2nd judgment），但输出压缩有价值 |
| **claude-code-spec-workflow** | `.claude/specs/` 存 design.md + requirements.md + tasks.md，4 个 validator agents 分别验证 | 偏"文档管理"，执行编排弱。validator 分维度思路可参考 |
| **claude-sub-agent/spec-orchestrator** | 3 阶段质量门（95%/85%/95%），模板化流程 | 理论性强，实际执行逻辑少，参考价值有限 |
| **andrej-karpathy-skills** | 单 skill 结构（SKILL.md frontmatter + body），EXAMPLES.md 用 ❌/✅ 对比展示 | 作为 IRON LAW reference 已纳入设计 |

### 调研验证的设计决策

| 设计点 | 验证状态 |
|--------|----------|
| Opus 不碰代码，只做 orchestrator | ✅ 业界 orchestrator 模式共识 |
| Spec-driven（每个 task 有完整 spec） | ✅ GSD/SDD/spec-workflow 都采用 |
| explore/design/coding 一个 sub agent 连续做 | ✅ 上下文连续性最佳实践 |
| Review 后 Opus 二次判断 | ✅ "验证是瓶颈"的业界共识，GSD 无此能力 |
| worktree 隔离并行任务 | ✅ Claude Code 原生支持 |
| Spec 加 File Scope + Boundaries | ✅ 来自 GitHub 2500+ 配置分析 |
| IRON LAW 引用而非全文 | ✅ 避免"指令诅咒"反模式 |
| 日志驱动调试 + 先列可能原因 | ✅ Microsoft AgentRx + Agentic Coding Handbook 共识 |
| `read_first` 强制先读后改 | ✅ GSD 源码验证，防止盲改 |
| 分析瘫痪检测 | ✅ GSD executor 实战验证 |
| `must_haves` goal-backward 验收 | ✅ GSD 最有价值的创新之一 |

---

## 开放问题

1. **多 story 并发**：能否同时进行多个 story？如果可以，handoff.py 需要识别当前活跃 story。

## 已解决问题

| 问题 | 决策 | 日期 |
|------|------|------|
| 命名 | `coding-orchestrator` | 2026-04-09 |
| Handoff 恢复方式 | 方案 A：PostCompact hook 写 `.handoff-context` 文件，Opus 主动读取 | 2026-04-09 |
| IRON LAW 引用语法 | `coding-guideline.md` 完整拷贝 karpathy 内容，所有 sub agent 必读 | 2026-04-09 |
| Hooks 安装机制 | 已有完整机制（`lib/omp_hooks.py` + `bin/omp` 集成），无需新建 | 2026-04-09 |
| 是否需要独立 CLI | 不需要，scripts 只服务 hooks | 2026-04-09 |
| Reference 命名规范 | `*-guideline.md`（行为规范类）、`*-template.md`（模板类） | 2026-04-09 |
| 能否直接用 GSD | 不能：无模型路由、不可组合、不支持 Pi、太重、无 compaction 对抗 | 2026-04-09 |
| Codex 调用方式 | 通过 `Agent(subagent_type="codex")` 调用，sub agent 自己读 spec 文件 | 2026-04-09 |
| Codex 不可用 fallback | 用 Sonnet sub agent 做 review | 2026-04-09 |
| Sub agent prompt 组装 | Sub agent 自己读 spec 文件，prompt 只给文件路径；无 spec 时才 prompt 注入 | 2026-04-09 |
| Wave 并行机制 | 不需要，Opus 按依赖顺序分发任务即可 | 2026-04-09 |
| Story 生命周期 | 留着，用户手动清理 | 2026-04-09 |
| Worker 输出压缩 | 移除，不是 skill 层面的职责 | 2026-04-09 |
