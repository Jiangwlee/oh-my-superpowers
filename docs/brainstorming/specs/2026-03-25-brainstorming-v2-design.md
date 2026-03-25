# Brainstorming Skill v2

> 将 brainstorming skill 的职责从"设计方案"延伸至"设计方案 + 行动方案"，引入 Normal/Fast 双模式，统一输出文档结构，并以交互式开发模式推荐收尾。

## 目录

- [背景与目标](#背景与目标)
- [设计方案](#设计方案)
  - [定位变更](#定位变更)
  - [双模式设计](#双模式设计)
  - [输出文档结构](#输出文档结构)
  - [流程 Checklist](#流程-checklist)
  - [开发模式推荐（第 10 步）](#开发模式推荐第-10-步)
  - [Skill 目录结构变更](#skill-目录结构变更)
- [行动原则](#行动原则)
- [行动计划](#行动计划)
  - [文件变更清单](#文件变更清单)
  - [任务步骤](#任务步骤)

---

## 背景与目标

当前 brainstorming skill 止步于"将头脑风暴转化为设计方案"，输出 spec 文档后调用 writing-plans skill 继续。这造成两个问题：

1. 行动层（怎么做、遵守什么原则）在 brainstorming 之外，上下文割裂
2. writing-plans 在本项目中不再使用，调用链成为空转

**目标：** brainstorming 成为从想法到可执行行动方案的完整闭环，输出"设计方案 + 行动原则 + 行动计划"三位一体的统一文档，以交互式开发模式推荐收尾。

---

## 设计方案

### 定位变更

```
旧：将头脑风暴转化为设计方案（spec）
新：将头脑风暴转化为完整的设计方案 + 行动方案
```

行动方案 = 行动原则（遵守什么）+ 行动计划（怎么做）。

SKILL.md 的 `description` 字段同步更新，触发条件不变。

### 双模式设计

Claude 在澄清问题结束后判断任务复杂度，自动选择模式并主动告知用户，用户无需指定。

| 维度 | Normal 模式 | Fast 模式 |
|------|-------------|-----------|
| 触发条件 | 默认；涉及架构/多模块/跨文件改动 | Claude 判断为简单改动后自动进入 |
| 判断时机 | 澄清问题结束后 | 澄清问题结束后 |
| 方案对比 | 提 2-3 个方案，说明权衡 | 直接给推荐方案，无对比 |
| Spec review loop | ✅ 执行（最多 3 次迭代） | ❌ 跳过 |
| 行动计划粒度 | 精确文件路径 + checkbox 步骤 | 粗粒度步骤列表，无代码示例 |
| 行动原则数量 | 全部适用原则 | 最相关的 2-3 条，不展开说明 |
| 使用模板 | `assets/design-doc-template-normal.md` | `assets/design-doc-template-fast.md` |

**Fast 模式告知语（固定格式）：**
> *"这是一个相对简单的改动，我将使用 Fast 模式——方案直接给出，不做多方案对比，输出轻量文档。"*

### 输出文档结构

所有输出保存至 `docs/brainstorming/specs/YYYY-MM-DD-<topic>-design.md`。

文档固定三段结构，**必须包含目录**（供 Agent 快速定位章节，无需全文扫描）：

```
# [Feature Name]
> 一句话描述

## 目录
## 设计方案
## 行动原则
## 行动计划
   ### 文件变更清单
   ### 任务步骤
```

具体模板见 `assets/design-doc-template-normal.md` 和 `assets/design-doc-template-fast.md`。

**Fast 模式差异：** 文件变更清单保留，任务步骤只写粗粒度列表（无代码示例、无精确行号）。

### 流程 Checklist

Normal 模式（10步）：

1. **Explore project context** — 检查文件、文档、近期 commits
2. **Offer visual companion**（如涉及视觉问题）— 独立消息，不与其他内容合并
3. **Ask clarifying questions** — 一次一个问题，理解目的/约束/成功标准
4. **Judge mode** — 澄清结束后判断 Normal/Fast，Fast 模式时主动告知用户
5. **Propose approaches** — Normal: 2-3 个方案 + 权衡 + 推荐；Fast: 直接给推荐方案
6. **Present design** — 分节呈现，每节获得用户确认
7. **Write unified doc** — 按模板输出三段结构文档并 commit
8. **Spec review loop**（仅 Normal）— dispatch spec-document-reviewer subagent，最多 3 次迭代
9. **User reviews doc** — 用户确认文档内容
10. **Recommend development mode** — 交互式推荐，用户确认后直接执行

Fast 模式跳过步骤 8，步骤 9（用户确认文档）保留，其余相同。

**终态：** 用户在第 10 步选择开发模式并确认 → 流程完成（移除原有的 writing-plans 调用）。

### 开发模式推荐（第 10 步）

Claude 在文档确认后，根据任务特点给出明确推荐，等待用户响应。用户输入 `同意` / `yes` / `ok` / `A` 即直接执行。

**推荐模板：**

> *"建议使用 **[模式名]**：[一句话说明理由]。*
>
> **选项：**
> - **A) Subagent 模式（推荐）** — 每个模块独立 subagent，主会话负责 review
> - **B) 内联执行** — 在当前会话中逐步执行
>
> *输入 A/B，或直接说「同意」采用推荐方案，我立即开始。*"

**推荐判断规则：**
- 涉及多个独立模块/文件 → 推荐 Subagent 并行
- 任务步骤超过 5 个 → 推荐 Subagent 分段执行
- 单一文件的简单改动 → 推荐内联执行
- Fast 模式：通常推荐内联执行

**响应处理：**
- `同意` / `yes` / `ok` / `A` → 直接启动推荐方案
- `B` → 切换为内联执行
- "之后再说" / 无响应 → 流程正常结束，不阻塞

### Skill 目录结构变更

```
skills/brainstorming/
├── SKILL.md                          # 更新：新定位、Checklist、模式规则
├── assets/
│   ├── design-doc-template-normal.md # 新增：Normal 模式完整三段文档模板
│   └── design-doc-template-fast.md   # 新增：Fast 模式轻量文档模板
├── references/
│   └── principles-library.md         # 新增：7 条固定原则完整说明
├── spec-document-reviewer-prompt.md  # 保留不变
├── visual-companion.md               # 保留不变
└── scripts/                          # 保留不变
```

SKILL.md 只引用原则库入口，不内联原则全文（渐进式披露）。

---

## 行动原则

以下为本次任务适用的原则（完整原则库见 `references/principles-library.md`）：

- **TDD: Red → Green → Refactor**：先写一个会失败的测试（Red），再写最小实现让它通过（Green），最后重构（Refactor）。禁止在没有失败测试的情况下写实现代码。

- **Break, Don't Bend（断裂优于弯曲）**：接口设计错误时，直接修正，不建兼容层。禁止在代码和文档中出现 `deprecated`、`legacy`、`v1/v2` 等兼容性标记，除非用户明确要求。

- **Zero-Context Entry（零上下文入口）**：每个文件前 20 行必须让读者无需任何外部知识即可理解其职责、边界和关键接口。代码用注释列出关键函数，文档用目录和单句摘要。

- **Minimum Blast Radius（最小影响半径）**：每次提交只解决一个明确定义的问题。不捆绑重构、不预留扩展点、不顺手修改无关代码。

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 修改 | `skills/brainstorming/SKILL.md` | 更新定位、Checklist、模式规则、输出路径、原则库引用 |
| 新增 | `skills/brainstorming/assets/design-doc-template-normal.md` | Normal 模式完整文档模板 |
| 新增 | `skills/brainstorming/assets/design-doc-template-fast.md` | Fast 模式轻量文档模板 |
| 新增 | `skills/brainstorming/references/principles-library.md` | 7 条固定原则完整说明 |

### 任务步骤

#### Task 1: 新增 references/principles-library.md

- [ ] Step 1: 创建 `skills/brainstorming/references/` 目录
- [ ] Step 2: 写入 7 条原则完整版（名称、说明、禁止项），文件前 20 行含目录和摘要
- [ ] Step 3: 写入原则选取规则（默认包含哪些、按任务类型补充哪些、Fast 模式选 2-3 条）

#### Task 2: 新增 assets/design-doc-template-normal.md

- [ ] Step 1: 创建 `skills/brainstorming/assets/` 目录
- [ ] Step 2: 写入 Normal 模式完整三段模板（含目录、设计方案、行动原则、行动计划）
- [ ] Step 3: 在模板中为每个占位符写清填写说明

#### Task 3: 新增 assets/design-doc-template-fast.md

- [ ] Step 1: 写入 Fast 模式轻量模板（同结构，行动计划为粗粒度步骤列表）
- [ ] Step 2: 在模板顶部注明与 Normal 模式的差异

#### Task 4: 更新 SKILL.md

- [ ] Step 1: 更新 `description` 字段，反映新定位（设计方案 + 行动方案）
- [ ] Step 2: 更新 Checklist 为 10 步，加入 `Judge mode` 和 `Recommend development mode`，移除 `writing-plans`
- [ ] Step 3: 更新 `dot` 流程图，加入 Normal/Fast 分支节点和新终态
- [ ] Step 4: 新增 `**Judging the mode:**` 小节，写入判断规则和告知语
- [ ] Step 5: 新增 `## Principles Library` 章节入口，引用 `references/principles-library.md`
- [ ] Step 6: 新增 `## Development Mode Recommendation` 章节，写入推荐模板和响应处理
- [ ] Step 7: 更新输出路径为 `docs/brainstorming/specs/`，引用对应模板文件
- [ ] Step 8: 移除所有 `writing-plans` 调用引用

#### Task 5: 验证与提交

- [ ] Step 1: 通读 SKILL.md，确认无相对路径脚本调用
- [ ] Step 2: 确认所有新增文件前 20 行符合 Zero-Context Entry 原则
- [ ] Step 3: `git add` 全部变更文件并提交
