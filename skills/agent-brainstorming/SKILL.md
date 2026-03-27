---
name: agent-brainstorming
description: >-
  Agent 设计工作流。在设计新 Agent 之前必须使用。通过项目探索和身份审问识别并拒绝伪 Agent 需求，
  将通过检验的想法转化为种子上下文，然后移交 brainstorming skill 完成完整设计流程。
  Use when: user wants to design a new agent, says "设计一个 agent"、"我需要一个 agent"、
  "新建 agent"、"agent brainstorm"。
  Do NOT use for Skill 设计（使用 skill-brainstorming）或直接的代码实现任务。
---

# Agent Brainstorming

<!--
  用途：agent 设计前置检验，生成种子上下文后移交 brainstorming skill
  流程：探索项目 → 加载知识 → 身份审问 → 构造种子 → 移交 brainstorming
  关键引用：
    - references/agent-fundamentals.md   身份标准和判断规则
-->

agent-specific 前置检验器。只做 brainstorming 无法替代的一件事：**身份审问**。
通过后构造种子，移交 brainstorming skill 完成完整设计流程。

<HARD-GATE>
不得跳过身份审问直接进入设计。身份审问是硬性前置条件，失败则终止流程。
不得在移交 brainstorming 之前生成任何设计文档或代码文件。
</HARD-GATE>

## Checklist

Create a task for each item and complete them in order:

1. **探索项目上下文** — 了解项目现状，为后续提问提供依据
2. **加载基础知识** — 读取 references/agent-fundamentals.md
3. **身份审问** — 基于探索结果，用针对性问题验证 Role × Agency × Ownership
4. **综合判定** — 通过或失败
5. **构造种子并移交 brainstorming**

## Step 1：探索项目上下文

开始对话前，**先做项目探索**，不要直接提问。至少检查：

- 已有 agent 列表（`agents/` 目录）和它们的角色分工
- 已有 skill 列表（`skills/` 目录）和能力覆盖范围
- 项目结构、CLAUDE.md、近期 commits
- 用户描述中提到的相关文件或模块

**探索的目的**：
- 理解项目当前的 agent/skill 生态，找出空白和重叠
- 为身份审问准备具体的上下文，使问题有针对性
- 预判用户需求是 Agent 还是 Skill，准备好论据

## Step 2：加载基础知识

读取 `references/agent-fundamentals.md`，以其中的身份标准和判断规则为依据。

## Step 3：身份审问（Hard Gate）

**核心原则：基于探索结果提问，不问已知信息，不问空洞的开放式问题。**

身份审问验证三个维度：Role（角色）、Agency（语义判断）、Ownership（结果所有权）。
但提问方式必须结合 Step 1 的探索结果，而非固定问题模板。

### 提问策略

**先展示探索发现，再问针对性问题。** 每轮一个问题，收到回答后立即分析。

典型模式（按需选择，不是固定流程）：

**当探索已能预判角色时（推荐）：**
> 我看了项目现状：[简述发现，如已有哪些 agent、缺什么]。
> 你描述的需求听起来像是一个「[预判角色名]」——[一句话说明预判依据]。
> 这个方向对吗？还是你有不同的定位？

**当探索发现工具信号时（主动挑战 → 降级为 Skill）：**
> 我注意到 [具体发现，如"这个需求的核心是调用 X CLI"]。
> 这更像是 Skill 需求而非 Agent——[具体理由]。
> 你认为它需要哪些**无法脚本化的语义判断**？如果举不出，建议走 skill-brainstorming。

**当探索发现已有 agent 角色重叠时（主动挑战 → 避免重复建设）：**
> 我注意到已有 `[agent-name]` 担任 [角色描述]，它的职责包括 [关键职责]。
> 你要设计的 agent 和它的区别在哪？是扩展已有 agent 的职责，还是需要独立的新角色？

这会导向三种结果：
- **完全重叠** → 终止，不需要新 agent，扩展已有的
- **部分重叠** → 用户澄清差异，模型把差异作为新 agent 的核心身份定义
- **看似重叠但本质不同** → 用户解释后，模型在种子中注明边界，避免后续混淆

**当探索信息不足时：**
> 我看了项目结构，但对你要设计的 agent 还缺少关键信息。
> 用一个职业词描述它是谁？（例如：审查官、分析师、编辑）

### 判断维度（模型内部评估，不逐一问用户）

收集到足够信息后，模型**自行评估**三个维度：

- **Role**：能否用一个职业/职能词概括？含「器」「工具」「处理」「转换」→ Skill 信号
- **Agency**：是否存在无法脚本化的语义判断场景？所有判断都可规则化 → Skill 信号
- **Ownership**：是否对最终结果负责？只是中间步骤 → Skill 信号

**只对不确定的维度向用户求证，已从探索中确认的维度不再追问。**

### 判定输出

> **判定：[通过 / 失败]**
> Role：[有/无明确角色] — [简评，引用探索中的具体发现]
> Agency：[有/无语义判断] — [简评，引用具体场景]
> Ownership：[有/无结果所有权] — [简评]
>
> [通过] 继续构造种子。
> [失败] 根据身份审问，这个需求无法映射到明确的 Agent 角色。[具体原因，引用探索发现]
> 建议降级为 Skill，使用 skill-brainstorming 重新设计。

## Step 4：移交 brainstorming

判定通过后，构造种子并启动 brainstorming skill：

```
我已完成 agent-brainstorming 前置检验，结果如下：
- 身份审问：通过。
- Role：[一句话描述角色]
- Agency：[一句话描述核心语义判断]
- Ownership：[一句话描述交付物和使用者]
- 项目上下文：[探索中发现的关键信息，如已有 agent/skill 生态、空白点]
请基于以上上下文继续 brainstorming 流程。
```

**重要：** brainstorming 接手后，澄清问题阶段应充分利用身份审问的结论和探索发现，
直接聚焦 agent 设计的具体细节（所需 Skills、推理循环、输出规格、Pi frontmatter 等），
不重复已确认的信息。

---

## 关键原则

- **先探索再提问** — 不带上下文的问题是废话，探索是提问的前置条件
- **只问不确定的** — 探索已确认的信息不再追问，模型自行评估
- **一次一件事** — 每轮只问一个问题，不堆叠
- **展示发现再提问** — 先告诉用户你看到了什么，再基于此提问
- **身份审问不可跳过** — 任意一维（Role / Agency / Ownership）为零即失败
