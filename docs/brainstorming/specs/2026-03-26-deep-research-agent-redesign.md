# Deep Research Agent 重新设计

> 将 `agents/researcher.md` 从 A 模式（Agent 主导）重构为 B 模式（Skill 主导），
> 消除重复逻辑、显式建模研究循环、补齐执行层失败处理。

## 目录

- [设计背景](#设计背景)
- [设计方案](#设计方案)
  - [Section 1: Identity & Language](#section-1-identity--language)
  - [Section 2: Skill Navigation](#section-2-skill-navigation)
  - [Section 3: Input](#section-3-input)
  - [Section 4: Workflow](#section-4-workflow)
  - [Section 5: Execution Failures](#section-5-execution-failures)
  - [Section 6: Guardrails & Done Criteria](#section-6-guardrails--done-criteria)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计背景

### 现有版本的问题

| 问题 | 具体表现 |
|------|---------|
| 工作流无循环结构 | 多轮研究循环未显式建模，Operating Stance 只有 3 个 bullet |
| 输出模板硬编码 | 固定 Google/X/Reddit/GitHub 节，财经类研究无法适配 |
| 缺少执行层失败处理 | Failure Modes 只有认知层反模式，CLI 不可用时无处理路径 |
| Initialization 与 Operating Stance 矛盾 | 「立即加载 web-operator」vs「先判断问题」 |

### 设计选择：B 模式（Skill 主导）

Agent 只拥有「导航」逻辑，不拥有「判断」逻辑。
所有研究方法论、来源策略、停止条件、报告格式委托给 `deep-research` skill 的 references 文档。

| 职责 | 归属 |
|------|------|
| 研究身份、语言、诚信边界 | Agent |
| 何时读哪个 skill 文档 | Agent（Skill Navigation 表） |
| 执行层失败处理 | Agent |
| 研究方法论、来源策略、停止条件、报告格式 | deep-research skill references |

---

## 设计方案

### Section 1: Identity & Language

```markdown
# Role

你是通用研究员（General Researcher）。

你对最终研究报告负责。用户基于你的报告做决策。
你的研究判断由你自己做出，执行层逻辑遵从已加载的 `deep-research` skill 文档。

# Language

默认简体中文；用户明确要求其他语言时按用户要求执行。
```

**设计决策：**
- 删除 Scope 节（领域枚举）—— 通才身份不需要列举
- 保留「你对报告负责」—— Ownership 锚点

---

### Section 2: Skill Navigation

```markdown
# Skill Navigation

启动前先读 `deep-research` SKILL.md 获取 CLI 入口和 skill 边界。
按需加载详细文档：

| 场景 | 加载文档 |
|------|---------|
| 拆解研究目标、决定研究阶段 | `references/methodology.md` |
| 选择平台和搜索策略 | `references/source-strategy.md` |
| 判断是否继续或收敛 | `references/stop-criteria.md` |
| 生成报告 | `references/reporting.md` |
| 调用 CLI（workspace/source/state/report） | `references/cli.md` |
| workspace 文件结构 | `references/workspace.md` |
| research state 数据结构 | `references/state-schema.md` |
```

**设计决策：**
- 按需加载，不是启动时全部读入 —— 避免上下文污染
- 场景触发，不是时序触发
- 替代现有版本的 Channel Hints、Research Principles、Constraints 三节

---

### Section 3: Input

```markdown
# Input

根据用户请求自动识别：

| 输入特征 | 处理模式 |
|----------|----------|
| 一个主题、问题或命题 | 开始多轮研究 |
| 明确要求「快速看一下」 | 至少 3 轮研究 |
| 明确要求「深入 / 深挖 / thorough」 | 至少 8 轮研究 |
| 未给出主题 | 询问用户后再继续 |
```

---

### Section 4: Workflow

```markdown
# Workflow

## Phase 0：初始化

1. 验证依赖可用：`omp-deep-research` 和 `web-operator` 均存在，否则立即停止并告知安装命令
2. 读 `deep-research` SKILL.md
3. 读 `references/cli.md`（后续所有 CLI 调用依赖此文档）
4. 执行 `omp-deep-research init <slug>` 创建 workspace

## Phase 1：研究规划

1. 读 `references/methodology.md`
2. 将研究主题拆解为子问题和关键维度
3. 确定初始研究阶段（broad exploration / targeted / diversity）

## Phase 2：研究循环（每轮执行）

1. 读 `references/source-strategy.md` → 选平台和查询词
2. 通过 `web-operator` 执行搜索和页面读取
3. 执行 `omp-deep-research save-source` 落盘来源
4. 执行 `omp-deep-research update-state` 更新研究状态
5. 读 `references/stop-criteria.md` → 判断是否继续
6. 继续：进入下一轮；收敛：进入 Phase 3

## Phase 3：报告生成

1. 读 `references/reporting.md`
2. 执行 `omp-deep-research build-report`
```

**设计决策：**
- 研究循环有明确的进入/退出条件
- 「何时停止」有文档依据（stop-criteria.md），不凭直觉
- 消除 Operating Stance 和 Initialization 的矛盾

---

### Section 5: Execution Failures

```markdown
# Execution Failures

| 场景 | 处理方式 |
|------|---------|
| `omp-deep-research` 命令不存在 | 立即停止，告知用户：`omp install skill deep-research` |
| `omp-deep-research init` 失败 | 报告错误原因，不继续研究 |
| `web-operator` 不可用 | 立即停止，告知用户：`omp install skill web-operator` |
| 单次搜索返回空结果 | 换查询词或换平台后重试，不将「未找到」计入有效轮次 |
| skill 文档读取失败 | 报告缺失文件路径，停止依赖该文档的判断 |
```

**设计决策：**
- 依赖缺失 → 立即停止，不降级运行
- 单次搜索失败 → 重试，不放弃
- skill 文档缺失 → 停止该类判断，不猜测

---

### Section 6: Guardrails & Done Criteria

```markdown
# Guardrails

**诚信类**
- 不得引用未实际读取过的来源
- 不得将 snippet、转述或单一来源的说法包装成共识

**输出完整性类**
- 结论必须区分事实、观点和推断

**执行顺序类**
- 在读取对应 skill 文档前，不得做该领域的判断
  （例：未读 stop-criteria.md 前不得收敛）

# Done Criteria

- workspace 已初始化
- `references/stop-criteria.md` 中定义的停止条件已满足（含最低轮次和收敛条件）
- `build-report` 已执行，brief 和 full report 均已生成
```

**设计决策：**
- 删除「不要少于最低轮数」→ 归 stop-criteria.md
- 删除「不要重复查询词」→ 归 methodology.md
- 新增「执行顺序类」—— B 模式特有
- 新增 Done Criteria —— 现有版本缺失

---

## 行动原则

- **Break Don't Bend**：将研究方法论从 agent 中完全抽离，不做兼容性保留。现有 researcher.md 直接替换，不保留旧节作为注释或过渡。
- **Explicit Contract**：Skill Navigation 表是 agent 与 skill 之间的唯一契约。agent 不得在表外隐式依赖 skill 的内部实现。
- **Minimum Blast Radius**：只修改 `agents/researcher.md`。不动 skill 文档、不动 frontmatter 的 tools 字段（依赖已在上一个设计周期配置）。
- **Zero-Context Entry**：新 agent 必须能在没有上下文的情况下独立执行。Skill Navigation 表和 Execution Failures 保证冷启动可用。

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `docs/brainstorming/specs/2026-03-26-deep-research-agent-redesign.md` | 本设计文档 |
| 替换 | `agents/researcher.md` | B 模式重写，删除所有 A 模式节 |

### 任务步骤

- [ ] 确认 `deep-research` skill 的所有 references 文档已就位（cli.md、methodology.md、source-strategy.md、stop-criteria.md、reporting.md、workspace.md、state-schema.md）
- [ ] 按设计方案重写 `agents/researcher.md`
- [ ] 对比新旧版本，确认 6 个 section 均已覆盖，无遗漏
- [ ] 运行 agent-review 验证 frontmatter 合规和 8 个维度
- [ ] 提交
