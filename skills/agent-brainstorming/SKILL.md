---
name: agent-brainstorming
description: >-
  Agent 设计工作流。在设计新 Agent 之前必须使用。通过身份审问识别并拒绝伪 Agent 需求，
  将通过检验的想法转化为种子上下文，然后移交 brainstorming skill 完成完整设计流程。
  Use when: user wants to design a new agent, says "设计一个 agent"、"我需要一个 agent"、
  "新建 agent"、"agent brainstorm"。
  Do NOT use for Skill 设计（使用 skill-brainstorming）或直接的代码实现任务。
---

# Agent Brainstorming

<!--
  用途：agent 设计前置检验，生成种子上下文后移交 brainstorming skill
  流程：加载知识 → Phase 0 身份审问 → 构造种子 → 移交 brainstorming
  关键引用：
    - references/agent-fundamentals.md   身份标准和判断规则
-->

agent-specific 前置检验器。只做 brainstorming 无法替代的一件事：**身份审问**。
通过后构造种子，移交 brainstorming skill 完成完整设计流程。

<HARD-GATE>
不得跳过身份审问（Phase 0）直接进入设计。身份审问是硬性前置条件，失败则终止流程。
不得在移交 brainstorming 之前生成任何设计文档或代码文件。
</HARD-GATE>

## 准备：加载基础知识

开始前读取 `references/agent-fundamentals.md`，以其中的身份标准和判断规则为依据。

## Phase 0：身份审问（Hard Gate）

逐一提问，每问一道，**收到回答后立即分析**，再问下一道：

> Q1：用一个职业或职能词语描述这个 Agent 是谁？

收到 Q1 答案后，立即判断：
- 答案含「器」「工具」「处理」「转换」「封装」→ 当场指出：「这听起来像工具需求，可能更适合 Skill。我们继续确认，但请注意这个信号。」
- 答案是明确职业/职能 → 继续 Q2

> Q2：它需要做哪些「无法脚本化」的判断？请描述至少一个具体场景。

收到 Q2 答案后，立即判断：
- 所有判断都可以用规则/正则/脚本完成 → 当场指出缺陷
- 有真实语义判断场景 → 继续 Q3

> Q3：任务结束后，这个 Agent 对什么结果负责？谁会用这个输出做决策？

> Q4：如果这是一个人类专家，他需要什么专业背景？

收到全部 4 道答案后，**给出综合判定**：

> **判定：[通过 / 失败]**
> Role：[有/无明确角色] — [简评]
> Agency：[有/无语义判断] — [简评]
> Ownership：[有/无结果所有权] — [简评]
>
> [通过] 继续构造种子。
> [失败] 根据身份审问，这个需求无法映射到明确的 Agent 角色。[具体原因]
> 建议降级为 Skill，使用 skill-brainstorming 重新设计。

## 移交 brainstorming

判定通过后，构造种子并启动 brainstorming skill：

```
我已完成 agent-brainstorming 前置检验，结果如下：
- 身份审问：通过。
- Role：[一句话描述角色]
- Agency：[一句话描述核心语义判断]
- Ownership：[一句话描述交付物和使用者]
- 专业背景：[Q4 答案摘要]
请基于以上上下文继续 brainstorming 流程。
```

**重要：** brainstorming 接手后，澄清问题阶段应充分利用身份审问的结论，
直接聚焦 agent 设计的具体细节（所需 Skills、推理循环、输出规格、Pi frontmatter 等），
不重复身份审问的 4 个问题。

---

## 关键原则

- **Phase 0 必须逐题收集** — Agent 身份信息只有用户知道，无法推断；但收到答案后立即分析
- **一次一件事** — 每轮只问一个问题，不堆叠
- **身份审问不可跳过** — 任意一维（Role / Agency / Ownership）为零即失败
