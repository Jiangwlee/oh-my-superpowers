---
name: skill-brainstorming
description: >-
  Skill 设计工作流。在设计新 Skill 之前必须使用。通过真实能力检验和模式选择，
  将模糊的 Skill 想法转化为种子上下文，然后移交 brainstorming skill 完成完整设计流程。
  Use when: user wants to design a new skill, says "设计一个 skill"、"我需要一个 skill"、
  "新建 skill"、"skill brainstorming"。
  Do NOT use for Agent 设计（使用 agent-brainstorming）、直接的代码实现任务、
  或没有明确 Skill 目标的通用功能头脑风暴（使用 brainstorming）。
---

# Skill Brainstorming

<!--
  用途：skill 设计前置检验，生成种子上下文后移交 brainstorming skill
  流程：加载知识 → Phase 0 能力检验 → 模式选择 → 构造种子 → 移交 brainstorming
  关键引用：
    - references/skill-fundamentals.md   自治原则和判断标准
    - references/design-patterns.md      5 种模式定义和目录结构
-->

skill-specific 前置检验器。只做 brainstorming 无法替代的两件事：**真实能力检验** 和 **模式选择**。通过后构造种子，移交 brainstorming skill 完成完整设计流程。

<HARD-GATE>
不得跳过 Phase 0 真实能力检验和模式选择。
不得在移交 brainstorming 之前生成任何设计文档或代码文件。
</HARD-GATE>

## 准备：加载基础知识

开始前读取 `references/skill-fundamentals.md`，以其中的自治原则和判断标准为依据。

## Phase 0：真实能力检验（Hard Gate）

向用户提一个问题：

> 你想封装的具体能力是什么？它依赖哪些工具、规范、脚本或私有知识？
> （例如："用 X CLI 工具做 Y"、"按内部编码规范审查 Z"）

收到回答后，**模型独立完成以下三项判断**，然后一次性给出结论：

1. **能力真实性**：是"封装模型无法直接完成的能力"，还是只是"让模型做 X"？
2. **必要性**：去掉这个 Skill，模型用通用知识能做到一样好吗？
3. **自治性**：这个 Skill 需要的所有知识，能否打包进自身的 `references/` 或 `assets/`？

结论格式：
> 我的判断：[通过 / 失败]
> 原因：[一句话说明]
> [通过] 继续模式选择。
> [失败] [告知具体失败原因，终止或建议调整方向]

**失败情形：**
- 只是"让模型做 X"，没有具体工具/规范依赖 → 终止，建议直接用模型
- 模型用通用知识已能完成 → 终止，不需要 Skill
- 存在无法内化的外部依赖（依赖其他 Skill、项目文件、Agent）→ 终止，需先将依赖内化到 `references/`

## 模式选择

加载 `references/design-patterns.md`，**模型主动推荐**最适合的模式，请用户确认：

> 根据你描述的能力，我推荐 **[模式名]** 模式。
> 理由：[1-2 句说明为何匹配]
> [如有竞争方案] 另一个候选是 [模式名]，但 [排除理由]。
>
> 你认同这个模式选择吗？

5 种模式速查：

```
Tool Wrapper  — 让模型成为特定技术/库的专家，动态加载规范
Generator     — 从模板生成结构化文档/代码，模板驱动输出
Reviewer      — 按标准检查内容，按严重程度分类
Inversion     — 先多轮收集需求再行动，有门控机制
Pipeline      — 严格的多步骤工作流，带检查点和用户确认
```

模式可以组合。模型应主动判断，不应让用户自己选。

## 移交 brainstorming

用户确认模式后，构造种子并启动 brainstorming skill：

```
我已完成 skill-brainstorming 前置检验，结果如下：
- 能力检验：通过。[一句话说明封装了什么真实能力]
- 选定模式：[模式名]。[一句话说明理由]
请基于以上上下文继续 brainstorming 流程。
```

**重要：** brainstorming 接手后，澄清问题阶段应充分利用已知的模式信息，
直接聚焦 skill 设计的具体细节（目录结构、触发边界、CLI 接口等），不重复能力检验。
