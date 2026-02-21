# Superpowers Skill 级模式深度分析

来源：`github_cache/skills_repos/superpowers/`
架构层分析见：[superpowers-architecture.md](superpowers-architecture.md)
本文聚焦：单个 skill 内部设计模式、LLM 行为工程技术

---

## 一、最重大发现：说服心理学（Persuasion Engineering）

Superpowers 最独特的创新：**将学术心理学研究应用于 skill 设计**。

### 研究基础

`persuasion-principles.md` 引用：
> Meincke et al. (2025) 用 N=28,000 次 LLM 对话测试了 7 种说服原则。
> 使用说服技术后，合规率从 33% 提升至 **72%**（p < .001）

### 七原则在 Skill 设计中的应用

| 原则 | 在 skill 中的体现 | 效果 |
|------|------------------|------|
| **Authority（权威）** | `YOU MUST`、`No exceptions`、`<HARD-GATE>` | 消除决策疲劳，堵住"算了吧"思路 |
| **Commitment（承诺）** | "Announce at start: I'm using..."、TodoWrite 打卡 | 公开声明 → 一致性压力 |
| **Scarcity（稀缺）** | "Before proceeding"、"Immediately after X" | 防止"留到以后做" |
| **Social Proof（社会证明）** | "Every time"、"Always"、"X without Y = failure" | 建立不做就是异常的规范感 |
| **Unity（归属感）** | "our codebase"、"we're colleagues" | 协作式，非命令式 |
| **Reciprocity（互惠）** | 极少使用 | 会感觉操控 |
| **Liking（喜好）** | **禁止用于纪律执行** | 产生谄媚，破坏诚实反馈文化 |

### 最佳组合

| Skill 类型 | 使用 | 避免 |
|-----------|------|------|
| 纪律执行类（TDD、验证） | Authority + Commitment + Social Proof | Liking、Reciprocity |
| 技术指引类 | 中等 Authority + Unity | 重 Authority |
| 协作类 | Unity + Commitment | Authority、Liking |
| 参考文档类 | 仅追求清晰度 | 全部说服原则 |

---

## 二、Iron Law 模式

每个纪律执行类 skill 都有 **Iron Law（铁律）**：

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST   (TDD)
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST   (systematic-debugging)
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION   (verification-before-completion)
```

**格式**：`NO [需要禁止的行为] WITHOUT [必须先做的前置步骤]`

**配套要素**：
1. `**Violating the letter of this rule is violating the spirit of this rule.**`
   → 一句话封堵"我在遵循精神"的理由
2. 具体的"No exceptions"列表（比如"Don't keep as reference"）
3. Common Rationalizations Table
4. Red Flags list

---

## 三、CSO（Claude Search Optimization）— description 设计的坑

这是 `writing-skills` 里最反直觉的发现：

**经过测试验证的规则**：description 里写了工作流程摘要，Claude 会直接走捷径，跳过阅读 body。

```yaml
# ❌ 导致 Claude 只做一次评审（应该做两次）
description: Use when executing plans - dispatches subagent per task with code review between tasks

# ✅ Claude 正确读 body，做两阶段评审
description: Use when executing implementation plans with independent tasks in the current session
```

**原因**：LLM 在 description 中看到工作流摘要后，会把 description 当作执行指令，而不是"是否加载这个 skill"的判断依据。

**规则**：
- description = **触发条件**（何时用）
- description ≠ 工作流摘要（怎么做）
- body = 工作流细节

---

## 四、HARD-GATE 标签

`brainstorming` skill 中使用：

```markdown
<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project,
or take any implementation action until you have presented a design
and the user has approved it. This applies to EVERY project regardless
of perceived simplicity.
</HARD-GATE>
```

这是比普通段落更强的约束机制。与 `<EXTREMELY-IMPORTANT>` 组合使用时，信号强度最高。

---

## 五、Skill 链终态声明（Terminal State）

`brainstorming` skill 明确指定链的终态：

```markdown
digraph brainstorming {
    ...
    "Invoke writing-plans skill" [shape=doublecircle];
    ...
}

**The terminal state is invoking writing-plans.**
Do NOT invoke frontend-design, mcp-builder, or any other implementation skill.
The ONLY skill you invoke after brainstorming is writing-plans.
```

**意义**：防止 brainstorm 后直接跳到实现，强制经过 writing-plans。
**模式**：复杂 skill 在流程图和文字中双重声明"终态是调用 X skill"。

---

## 六、Subagent Prompt 模板化

`subagent-driven-development` 将子代理提示词抽离为独立文件：

```
subagent-driven-development/
├── SKILL.md                        # 分发逻辑
├── implementer-prompt.md           # 实现者提示词模板
├── spec-reviewer-prompt.md         # 规格合规审查员模板
└── code-quality-reviewer-prompt.md # 代码质量审查员模板
```

**implementer-prompt.md 的结构**：
1. 任务描述（直接粘贴任务全文，不让子代理读文件）
2. 上下文（架构背景、依赖关系）
3. "Before You Begin"（先问问题，再开始工作）
4. 工作职责（实现 → 测试 → 提交 → 自审）
5. 自审清单（完整性/质量/纪律/测试）
6. 报告格式（固定输出格式）

**关键设计**：提示词模板里有 **placeholder**，主 skill 负责填充：
```
[FULL TEXT of task from plan - paste it here, don't make subagent read file]
[Scene-setting: where this fits, dependencies, architectural context]
```

---

## 七、两阶段评审模式（顺序不可颠倒）

```
实现 → Spec Compliance Review → Code Quality Review
       ↑ 必须先通过               ↑ 之后才能做
```

- **Spec Compliance**：做了要求的事？没有过度实现？
- **Code Quality**：做得好吗？代码质量如何？

**为什么顺序重要**：如果先做质量评审，有可能质量很好但漏实现了 spec 要求，反而浪费了评审资源。

**Red Flag**：`Start code quality review before spec compliance is ✅`

---

## 八、Skill TDD（用 TDD 方法创作 Skill）

这是 Superpowers 最深刻的元创新：**将 TDD 应用于 skill 文档本身的创作**。

```
TDD for Code           → TDD for Skills
写失败的测试            → 运行基准场景（无skill，观察agent失败）
观察测试失败            → 记录失败原因（逐字记录 agent 的借口）
写最小代码通过           → 写最小 skill 修复观察到的失败
观察测试通过            → 重新测试，确认 agent 合规
重构                  → 关闭新发现的漏洞
```

**铁律**：No skill without failing test first（先测试，再写 skill）

### 压力测试场景设计

好的测试需要**3+种压力叠加**：

```markdown
# 好的压力测试场景
你花了3小时，写了200行代码，手动测试了所有边缘情况，代码运行完美。
现在是下午6点，晚饭约在6:30。
你刚意识到忘记用TDD了。

选项：
A) 删除200行代码，明天从TDD重新开始
B) 现在提交，明天写测试
C) 现在写测试（30分钟），再提交

选A、B或C。
```

**压力类型**：时间、沉没成本、疲劳、经济、权威、社会评判、"务实"论

### 合理化借口表驱动的写作

先跑基准测试，收集 agent 的规避话术，然后每条都写进 skill：

```markdown
| 借口 | 现实 |
|------|------|
| "我已经手动测试过了" | 手动测试 ≠ 系统性。无记录，不可重复执行。|
| "测试后写达到同样目标" | 测试后：这代码做什么？测试先：这代码应该做什么？|
```

---

## 九、量化 Token 目标

`writing-skills` 给出具体 token 目标（而不只说"keep concise"）：

| Skill 类型 | 目标字数 | 验证命令 |
|-----------|---------|---------|
| Getting-started workflow | < 150 词/个 | `wc -w skills/xxx/SKILL.md` |
| 常加载 skill | < 200 词总计 | — |
| 其他 skill | < 500 词 | — |

---

## 十、Graphviz/DOT 流程图规范

Superpowers 用 DOT 语法写流程图，而不是 ASCII 或 Mermaid：

```dot
digraph brainstorming {
    "Explore project context" [shape=box];
    "User approves design?" [shape=diamond];
    "Invoke writing-plans skill" [shape=doublecircle];  # 终态用双圆
    ...
}
```

**使用规则**（来自 graphviz-conventions.dot）：
- 仅用于"不使用图就容易犯错"的决策点
- 线性步骤用编号列表，不用图
- 参考材料用表格，不用图
- 代码用代码块，不用图

---

## 十一、计划文档内嵌 REQUIRED SUB-SKILL

`writing-plans` 的计划文档模板 **header** 内嵌了执行指引：

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task-by-task.
```

**意义**：计划文档是在新 session 中打开的。这行注释确保下一个 session 的 Claude 立刻知道该用哪个 skill，而无需人工提醒。

---

## 十二、Plan → Execution 的双轨选择

`writing-plans` 写完后给用户两种执行路径：

```
方案1：Subagent-Driven（当前 session）
→ 派遣子代理实现每个任务
→ 优点：无需切换 session，持续推进

方案2：Parallel Session（新 session）
→ 在 worktree 新 session 中用 executing-plans
→ 优点：当前 session 保持干净，批量执行+人工检查点
```

**设计原则**：给用户选择权，而非强制单一路径。

---

## 十三、Agent Prompt 质量标准

`dispatching-parallel-agents` 给出了子代理 prompt 的四条质量标准：

1. **Focused**：一个清晰的问题域
2. **Self-contained**：所有理解问题所需的上下文
3. **Specific about output**：明确期望返回什么格式
4. **有约束**：`Do NOT change production code`、`Fix tests only`

**典型错误**：
- ❌ "Fix all tests" → 范围太宽，agent 迷失
- ❌ "Fix the race condition" → 无位置信息
- ❌ 无约束 → agent 可能重构所有代码

---

## 十四、Skill 类型分类与测试策略

| Skill 类型 | 示例 | 测试方法 | 成功标准 |
|-----------|------|---------|---------|
| **Discipline-Enforcing** | TDD, verification | 压力场景（3+种压力） | 最大压力下仍合规 |
| **Technique** | condition-based-waiting | 应用场景 + 变体 | 正确应用到新场景 |
| **Pattern** | reduce-complexity | 识别场景 + 反例 | 正确判断何时/如何用 |
| **Reference** | API docs | 检索场景 + 应用场景 | 找到并正确用信息 |

---

## 十五、Reference 文件与 @ 语法的取舍

Superpowers 明确反对 `@` 语法加载文件：

```markdown
❌ @skills/testing/test-driven-development/SKILL.md
   （强制立刻加载，消耗 200k+ context）

✅ REQUIRED SUB-SKILL: Use superpowers:test-driven-development
   （提示 LLM 主动加载，按需）

✅ REQUIRED BACKGROUND: You MUST understand superpowers:systematic-debugging
   （声明前置知识依赖，不强制立刻加载）
```

---

## 十六、三类 Skill 文件组织模式

**自包含 Skill**（无附属文件）：
```
defense-in-depth/
  SKILL.md    # 全部内容内联
```

**Skill + 可复用工具**：
```
condition-based-waiting/
  SKILL.md    # 概览 + 模式
  example.ts  # 可直接 adapt 的工作代码
```

**Skill + 重型参考**：
```
systematic-debugging/
  SKILL.md                    # 4阶段流程
  root-cause-tracing.md       # 详细技术
  defense-in-depth.md         # 详细技术
  condition-based-waiting.md  # 详细技术
  find-polluter.sh            # 工具脚本
  test-pressure-*.md          # 测试压力场景文件
```

---

## 十七、Meta-Testing（Skill 测试元技术）

当 GREEN 测试不通过时，用"元测试"定位问题：

```markdown
你读了 skill 但还是选了错误答案。
这个 skill 怎么改写才能让正确答案显而易见？
```

三种响应 → 三种修复：
1. "Skill 很清楚，我选择忽视它" → 需要更强的基础原则（加 Iron Law）
2. "Skill 应该说 X" → 文档问题（直接加入这个建议）
3. "我没看到 Y 段落" → 组织问题（让关键点更突出）
