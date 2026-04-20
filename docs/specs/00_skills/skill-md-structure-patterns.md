# SKILL.md 结构模式：来自优秀案例的实际经验

目的：总结优秀 `SKILL.md` 在结构、叙事、标题层级上的共性规律。
范围：只讨论 `SKILL.md` 的组织方式，不讨论 frontmatter、脚本实现、评测方法。
来源：观察 `~/Github/anthropic-skills/skills/*/SKILL.md` 的代表性案例后提炼。

---

## SKILL.md 结构

### 1. 明确主叙事方式

一个好的 `SKILL.md` 首页，通常只选择一种主叙事方式，并坚持到底。

常见主叙事方式：

- **流程型**：按阶段/步骤推进，适合 Pipeline 类 skill
- **决策型**：先判断分支，再进入对应路径
- **概念型**：先建立审美/方法论，再给出执行要求
- **极简块状型**：只保留 1-3 个大区块，适合边界清晰、负担轻的 skill

不要把多种叙事方式并列放在同一层级，例如：

- 前半段按 `Phase 0 / Phase 1`
- 中间突然切成 `Key principles`
- 后面再插入 `Failure handling`
- 再单独插入某个单场景特例

这会让读者不知道当前是在“跟流程走”，还是在“读附加说明”。

**示例 1：`mcp-builder`**

文件：`~/Github/anthropic-skills/skills/mcp-builder/SKILL.md`

结构：

```markdown
# MCP Server Development Guide
## Overview
# Process
## High-Level Workflow
### Phase 1: Deep Research and Planning
#### 1.1 Understand Modern MCP Design
#### 1.2 Study MCP Protocol Documentation
#### 1.3 Study Framework Documentation
#### 1.4 Plan Your Implementation
### Phase 2: Implementation
#### 2.1 Set Up Project Structure
#### 2.2 Implement Core Infrastructure
#### 2.3 Implement Tools
### Phase 3: Review and Test
#### 3.1 Code Quality
#### 3.2 Build and Test
### Phase 4: Create Evaluations
#### 4.1 Understand Evaluation Purpose
#### 4.2 Create 10 Evaluation Questions
#### 4.3 Evaluation Requirements
#### 4.4 Output Format
# Reference Files
## Documentation Library
### Core MCP Documentation (Load First)
### SDK Documentation (Load During Phase 1/2)
### Language-Specific Implementation Guides (Load During Phase 2)
```

说明：

- 这是典型的**流程型主叙事**
- 所有标题都服务于同一条主链：研究 → 实现 → 测试 → 评测
- 参考资料放在最后，不打断流程主线

**示例 2：`webapp-testing`**

文件：`~/Github/anthropic-skills/skills/webapp-testing/SKILL.md`

结构：

```markdown
# Web Application Testing
## Decision Tree: Choosing Your Approach
## Example: Using with_server.py
## Reconnaissance-Then-Action Pattern
## Common Pitfall
## Best Practices
## Reference Files
```

说明：

- 这是典型的**决策型主叙事**
- 文档不是先讲抽象原则，而是先给“怎么选路径”
- 后面的内容都在支持这个选择器

---

### 2. 首页只保留一条主线

优秀案例往往有很强的“首页意识”。

所谓首页意识，就是：

- 只放第一次触发 skill 时必须知道的东西
- 只保留能推进当前任务的主链
- 其他细节延后、折叠、下沉

常见反模式：

- 在首页同时放方法论、原则库、失败处理、术语定义、单场景特例
- 每一块都正确，但没有一条是主线

好的 `SKILL.md` 不追求“内容齐全”，而追求“第一遍读就知道怎么开始”。

**示例：`frontend-design`**

文件：`~/Github/anthropic-skills/skills/frontend-design/SKILL.md`

结构：

```markdown
## Design Thinking
## Frontend Aesthetics Guidelines
```

说明：

- 结构非常少，但不空
- 只保留两个第一次执行时最关键的认知块
- 没有再额外拆出“Failure handling / Extra notes / References”
- 这是典型的**极简块状型**

---

### 3. 同一层级只放同一维度的信息

标题层级应该表达清楚“这些 section 为什么是同级”。

好的同级关系通常是：

- 都是流程步骤
- 都是决策分支
- 都是执行阶段
- 都是附加资源入口

不好的同级关系通常是：

- 一个是步骤，一个是原则，一个是失败处理，一个是单场景特例

这类写法最大的问题不是“看起来乱”，而是**认知切换频繁**。读者读每个标题时，都要重新判断“这是让我做事，还是让我记规则，还是告诉我例外”。

**示例：`algorithmic-art`**

文件：`~/Github/anthropic-skills/skills/algorithmic-art/SKILL.md`

结构：

```markdown
## ALGORITHMIC PHILOSOPHY CREATION
### THE CRITICAL UNDERSTANDING
### HOW TO GENERATE AN ALGORITHMIC PHILOSOPHY
### PHILOSOPHY EXAMPLES
### ESSENTIAL PRINCIPLES
## DEDUCING THE CONCEPTUAL SEED
## P5.JS IMPLEMENTATION
### STEP 0: READ THE TEMPLATE FIRST
### TECHNICAL REQUIREMENTS
### CRAFTSMANSHIP REQUIREMENTS
### OUTPUT FORMAT
```

说明：

- 文档虽然长，但层级并不混乱
- 因为每个标题都仍然服务于同一个创作链条
- `ESSENTIAL PRINCIPLES` 和 `TECHNICAL REQUIREMENTS` 没有变成与主任务无关的漂浮栏目，而是附着在创作过程里

---

### 4. 标题应该推动任务，而不是给作者的脑内分类命名

很多结构混乱的 `SKILL.md`，问题不在内容，而在标题只是作者给自己做的分类标签。

例如这类标题通常比较弱：

- `Key principles`
- `Additional notes`
- `Failure handling`
- `Special cases`

这些标题不是绝对不能用，但它们往往暴露出一个问题：作者在分类内容，而不是在推动执行。

更强的标题会让读者立刻知道：

- 现在该判断什么
- 现在该做哪一步
- 现在该加载哪份材料
- 现在的输出要长什么样

**示例：`webapp-testing`**

文件：`~/Github/anthropic-skills/skills/webapp-testing/SKILL.md`

结构：

```markdown
## Decision Tree: Choosing Your Approach
## Example: Using with_server.py
## Reconnaissance-Then-Action Pattern
## Common Pitfall
## Best Practices
## Reference Files
```

说明：

- 标题几乎都在回答“下一步怎么做”
- 即使有 `Common Pitfall`、`Best Practices`，也仍然是任务执行导向
- 不是抽象分类，而是操作导向

---

### 5. 如果采用流程叙事，就把流程编号到底

如果一个 `SKILL.md` 开头已经选择了 `Phase` / `Step` / `Stage` 叙事，那就应该坚持到底。

不要出现这种切换：

```markdown
## Phase 0
## Phase 1
## Key principles
## Producer contract
## Failure handling
```

这会破坏读者的时间顺序预期。

更好的做法有两种：

1. **全程流程化**

```markdown
## Phase 0
## Phase 1
## Phase 2
## Phase 3
```

2. **完全不用流程编号，改成块状结构**

```markdown
## Overview
## Workflow
## Outputs
## References
```

中途切换叙事方式，通常是结构开始失控的信号。

**示例：`mcp-builder`**

文件：`~/Github/anthropic-skills/skills/mcp-builder/SKILL.md`

结构：

```markdown
## High-Level Workflow
### Phase 1: Deep Research and Planning
#### 1.1 Understand Modern MCP Design
#### 1.2 Study MCP Protocol Documentation
#### 1.3 Study Framework Documentation
#### 1.4 Plan Your Implementation
### Phase 2: Implementation
#### 2.1 Set Up Project Structure
#### 2.2 Implement Core Infrastructure
#### 2.3 Implement Tools
### Phase 3: Review and Test
#### 3.1 Code Quality
#### 3.2 Build and Test
### Phase 4: Create Evaluations
#### 4.1 Understand Evaluation Purpose
#### 4.2 Create 10 Evaluation Questions
#### 4.3 Evaluation Requirements
#### 4.4 Output Format
```

说明：

- 典型优点是**编号系统自洽**
- 读者从任意位置都能知道自己处于哪一个阶段

---

### 6. 原则应优先附着在流程上，而不是漂浮成独立中心

优秀 skill 当然也讲原则，但原则的摆放方式很重要。

通常更好的写法是：

- 把原则写进开头几段
- 写成某一步下面的 bullet
- 写成 `Best Practices`，放在流程之后

而不是让“原则”单独成为首页最显眼的结构中心。

因为对执行者来说，原则不是目的，原则是约束执行的方式。

**示例：`frontend-design`**

文件：`~/Github/anthropic-skills/skills/frontend-design/SKILL.md`

结构：

```markdown
## Design Thinking
## Frontend Aesthetics Guidelines
```

说明：

- 它当然有强烈的方法论
- 但这些方法论被吸附在设计任务上，而不是抽成零散附录
- 原则是为“做设计”服务，不是作为与任务平行的另一条文档主线

**示例：`algorithmic-art`**

文件：`~/Github/anthropic-skills/skills/algorithmic-art/SKILL.md`

结构：

```markdown
## ALGORITHMIC PHILOSOPHY CREATION
### THE CRITICAL UNDERSTANDING
### HOW TO GENERATE AN ALGORITHMIC PHILOSOPHY
### PHILOSOPHY EXAMPLES
### ESSENTIAL PRINCIPLES
```

说明：

- `ESSENTIAL PRINCIPLES` 被放在“生成哲学”这一大步骤下面
- 它没有脱离主流程，成为额外的结构中心

---

### 7. 参考资料应该在后面，作为延迟加载入口

优秀案例普遍把 references 的入口放在文档后部，作为“需要深入时再读”的区域。

这背后的结构原则是：

- 首页先回答“你现在怎么开始”
- 深入材料再回答“如果你要继续展开，去哪里读”

不要一开始就把大量“文献导航”放在首页主叙事中间。

**示例 1：`webapp-testing`**

文件：`~/Github/anthropic-skills/skills/webapp-testing/SKILL.md`

结构：

```markdown
# Web Application Testing
## Decision Tree: Choosing Your Approach
## Example: Using with_server.py
## Reconnaissance-Then-Action Pattern
## Common Pitfall
## Best Practices
## Reference Files
```

说明：

- `Reference Files` 位于最后
- 主链走完之后，才进入补充资源区

**示例 2：`mcp-builder`**

文件：`~/Github/anthropic-skills/skills/mcp-builder/SKILL.md`

结构：

```markdown
# MCP Server Development Guide
## Overview
# Process
## High-Level Workflow
### Phase 1: Deep Research and Planning
### Phase 2: Implementation
### Phase 3: Review and Test
### Phase 4: Create Evaluations
# Reference Files
## Documentation Library
### Core MCP Documentation (Load First)
### SDK Documentation (Load During Phase 1/2)
### Language-Specific Implementation Guides (Load During Phase 2)
```

说明：

- references 是流程的支撑层，不是首页正文中心
- 这符合“先主链，后资源”的结构规律

---

### 8. 轻 skill 要敢于短，小 skill 不必伪装成完整手册

很多结构混乱的问题，源头不是不会写，而是“想把文档写得很完整”。

优秀案例给出的经验恰恰相反：

- 若任务边界清楚，就不要硬拆很多 section
- 若首页已经足以指导行动，就不要再补一堆“看起来正规”的栏目
- 标题数量越多，结构负担越大

短 skill 的关键不是信息少，而是密度高、主线强。

**示例：`frontend-design`**

文件：`~/Github/anthropic-skills/skills/frontend-design/SKILL.md`

结构：

```markdown
## Design Thinking
## Frontend Aesthetics Guidelines
```

说明：

- 它没有强行补 `Failure handling`、`Output format`、`References`
- 结构极短，但叙事完整
- 说明“短”本身可以是一种高质量结构选择

---

### 9. 长 skill 允许复杂，但必须保持单线推进

长 skill 不是问题，问题是长而分叉、长而漂浮、长而切频道。

优秀长 skill 的共同点：

- 虽然 section 多，但仍然像一条链
- 读者一直知道自己处于哪个阶段
- 细节变多，不等于结构维度变多

**示例：`algorithmic-art`**

文件：`~/Github/anthropic-skills/skills/algorithmic-art/SKILL.md`

结构：

```markdown
## ALGORITHMIC PHILOSOPHY CREATION
### THE CRITICAL UNDERSTANDING
### HOW TO GENERATE AN ALGORITHMIC PHILOSOPHY
### PHILOSOPHY EXAMPLES
### ESSENTIAL PRINCIPLES
## DEDUCING THE CONCEPTUAL SEED
## P5.JS IMPLEMENTATION
### STEP 0: READ THE TEMPLATE FIRST
### TECHNICAL REQUIREMENTS
### CRAFTSMANSHIP REQUIREMENTS
### OUTPUT FORMAT
```

说明：

- 这份文档并不短
- 但结构始终围绕“哲学生成 → 概念提炼 → 代码实现”推进
- 因此读起来不像杂项堆积

---

### 10. 有分支或回路的流程，优先用 Mermaid + 步骤说明

对流程型 `SKILL.md`，一旦出现以下任一情况，优先用 `mermaid` 画导航图，再写步骤说明：

- 条件分支
- 循环回退
- 模式切换
- 升级 / 降级
- 多场景路由

原因很简单：

- `mermaid` 负责表达“流程怎么走”
- 步骤说明负责表达“这一步具体做什么”

如果只用语言描述，常见问题是：

- 顺序和条件混在一起
- 回退到哪一步不清楚
- 分支和例外像备注，不像正式路径

推荐写法：

1. 先给一张高层流程图，只表达主链、分支、回退、终止条件
2. 再在图下按步骤写目标、判断条件、产出和下一步

`mermaid` 不能替代步骤说明，但能显著减少流程拓扑上的歧义。

**示例：`timesfm-forecasting`**

文件：`~/Github/claude-scientific-skills/scientific-skills/timesfm-forecasting/SKILL.md`

结构：

```markdown
## [Preflight / system check section]
[Mermaid flowchart block]
### Hardware Requirements by Model Version
## Installation
```

说明：

- 流程图先把“检查路径”讲清楚
- 文字部分再补资源要求和执行细节
- 这种写法比纯 prose 更适合表达阻断、降级、继续三种路径

---

### 11. 优先使用高表达力结构，而不是平铺 prose

`SKILL.md` 不是普通说明文。它是给模型执行的操作文档，表达形式本身会影响理解和执行质量。

当信息存在明确结构时，优先使用高表达力结构，而不是把一切写成平淡段落：

- `mermaid`：表达流程拓扑、分支、回路、升级 / 降级
- `table`：表达离散规则、决策映射、参数矩阵、能力对照
- `ordered list`：表达严格顺序、必须按次执行的步骤
- `unordered list`：表达并列要点、检查项、触发条件、禁忌项
- `heading level`：表达文档主链和层级归属
- `xml tags` / `markdown tags`：表达硬门禁、模板边界、特殊协议块

核心原则：

- **用最能表达该信息结构的形式来写**
- 不要把本来是流程图、决策表、检查单、模板块的内容，硬写成 prose

常见收益：

- 减少歧义
- 降低跨段推理负担
- 让模型更快识别“这是步骤 / 这是规则 / 这是模板 / 这是硬约束”

简化判断：

- 有路径关系 → 用 `mermaid`
- 有有限映射关系 → 用 `table`
- 有强顺序 → 用 `ordered list`
- 有并列要点 → 用 `unordered list`
- 有主从归属 → 用 `heading`
- 有强边界或协议块 → 用标签块

**示例 1：`systematic-literature-review` 中的决策表**

文件：`~/Github/deer-flow/skills/public/systematic-literature-review/SKILL.md`

结构：

```markdown
### Phase 3: Extract metadata in parallel
| Paper count | Batches of ~5 papers | Rounds | Per-round subagent count |
|---|---|---|---|
| 1–5 | 1 batch | 1 round | 1 subagent |
| 6–10 | 2 batches | 1 round | 2 subagents |
| 11–15 | 3 batches | 1 round | 3 subagents |
...
```

说明：

- 这是典型的有限离散映射
- 用表格比 prose 更适合表达“输入区间 → 执行方案”

**示例 2：`timesfm-forecasting` 中的 Mermaid 导航**

文件：`~/Github/claude-scientific-skills/scientific-skills/timesfm-forecasting/SKILL.md`

结构：

```markdown
## [Preflight / system check section]
[Mermaid flowchart block]
### Hardware Requirements by Model Version
## Installation
```

说明：

- 流程图负责表达阻断、降级、继续路径
- 后续文字只补细节，不再承担流程拓扑表达

**示例 3：`bootstrap` 中的 phase table + tracker table**

文件：`~/Github/deer-flow/skills/public/bootstrap/SKILL.md`

结构：

```markdown
## Conversation Phases
| Phase | Goal | Key Extractions |
|---|---|---|
| 1. Hello | ... | ... |
| 2. You | ... | ... |
...

## Extraction Tracker
| Field | Required | Source Phase |
|---|---|---|
| Preferred language | ✅ | 1 |
| User's name | ✅ | 2 |
...
```

说明：

- 第一张表表达对话主线
- 第二张表表达信息完备条件
- 这比大段 prose 更适合对话型 / inversion 型 skill

---

## 结构检查清单

审视一个 `SKILL.md` 的标题层次时，可以先问：

1. 我能一眼看出它的主叙事方式吗？
2. 一级标题是否都属于同一维度？
3. 这些标题是在推动执行，还是在给内容分类？
4. 如果已经开始 `Phase / Step` 叙事，是否坚持到了结尾？
5. 原则、失败处理、特殊约束，是否被妥善挂靠在主链上？
6. 参考资料是否位于后部，作为延迟加载入口？
7. 这份 skill 是不是为了“看起来完整”而多拆了很多无效标题？

如果以上问题有多个回答为“否”，通常说明结构需要重写，而不是微调标题字面。
