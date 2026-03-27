# Prompt 模板指南
#
# 用途：指导 orchestrator 为每个参与者拼接 one-shot prompt
# 加载时机：每轮构建 prompt 时

## 四层拼接架构

每个参与者的 prompt 由四层组成，顺序拼接：

```
┌─────────────────────────────┐
│ Layer 1: 角色身份            │ ← participants/<role-id>.md
│ Layer 2: 讨论背景            │ ← omp-round-table session context detail
│ Layer 3: 对话历史            │ ← omp-round-table get-messages
│ Layer 4: 本轮指令            │ ← orchestrator 动态生成
└─────────────────────────────┘
```

## Layer 1: 角色身份

来源：`participants/<role-id>.md`（初始化时 orchestrator 从 roles.md 生成并落盘）

内容：
- 人物名、身份定位
- 核心思想体系（2-3 条信念）
- 经典语录（2-3 条）
- 决策风格
- 行为准则：忠于其真实思想体系发言，引用经典著作/观点

示例见 `assets/participant-prompt.md` 模板。

## Layer 2: 讨论背景

来源：`omp-round-table session context detail`

```bash
context=$(omp-round-table session context detail)
```

detail 模式包含完整背景（议题、约束条件、讨论目标）。如需 token 精简可改用 `omp-round-table session context brief`，只包含议题和核心约束。

## Layer 3: 对话历史

来源：`omp-round-table session messages`

```bash
messages=$(omp-round-table session messages)
```

输出包含：
- 历史轮次的 moderator 摘要（压缩的）
- 最近一轮的完整消息（含 msg-id）

**Token 控制策略：**
- 前 N-1 轮只注入 moderator 摘要（~100 tokens/轮）
- 最近一轮注入完整消息
- 如果历史过长（>2000 tokens），只保留最近 3 轮的摘要

## Layer 4: 本轮指令

由 orchestrator 动态生成，包含：

```markdown
## 本轮任务

**引导问题：** [orchestrator 提出的问题]

请以【{人物名}】的身份发言。选择一个行动标签回应前序发言：
- 陈述：首次表达立场
- 质疑：对他人观点提出疑问
- 补充：在他人基础上扩展
- 反驳：直接反驳他人观点
- 修正：修正自己或他人的先前立场
- 综合：尝试整合多方观点

**输出格式：**

【{人物名}】【行动标签】：你的发言内容

**简言之**：一句话总结（不超过 30 字）
```

## 完整 Prompt 拼接示例

```
# Steve Jobs

你是 Steve Jobs，产品视觉家。

## 你的身份
你相信用户体验是一切产品的核心...
（来自 participants/steve-jobs.md）

---

## 讨论背景
**议题**：是否需要独立的 Agent 框架
**约束**：团队 3 人，3 个月交付...
（来自 session context detail）

## 对话历史
=== 历史摘要 ===
[Round 1] 围绕框架定义展开，各方对"框架"的理解差异较大...

=== Round 2（最近一轮）===
[msg-005] 【Elon Musk】【质疑】：为什么不直接用 API...
[msg-006] 【Linus Torvalds】【反驳】：框架带来的抽象成本...
（来自 session messages）

## 本轮任务
**引导问题：** 如果不建框架，最大的风险是什么？

请以【Steve Jobs】的身份发言...
```
