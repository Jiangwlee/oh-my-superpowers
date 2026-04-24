# Self-Evaluation Guideline

自评Story执行过程和结果，按照`story-summary.md`模板输出。

## When

只在以下条件同时满足后写：

1. E2E 已通过
2. Acceptance 已通过
3. story 已接近关闭

不要在调试中途写。

## Where

文件位置固定：

`<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story-summary.md`

## Template

```markdown
# Story Summary: <slug>

Total waves: <N>
Total tasks: <N>

## 1. Mode Mix Retrospective

For each wave, count `tasks[*].worker` values: how many tasks ran inline vs sub-agent vs tmux?

| Wave | inline | sub-agent | tmux | Was the mix right? |
|---|---|---|---|---|
| 1 | N | N | N | Y / N — <one-line reason> |

If "N" anywhere: which task should have used a different mode and why? Suggest threshold or rule adjustments.

## 2. Quality Impact

Did kickoff improve coding quality? **[Y / N]**

<理由：与“不用 kickoff 直接写代码”对比，写清具体质量增益或额外开销。
能量化就量化：例如拦截 bug 数、返工次数、上下文切换成本。>

## 3. Positive Mechanisms

哪些条款和机制起到了正面作用？

- **<mechanism name>**: <how it helped, with task-NN reference>

例：JIT Spec — task-03 的 spec 因为读了 task-01/02 的 story-memory，提前规避了 X 问题。

## 4. Negative Mechanisms

哪些条款和机制起到了负面作用？

- **<mechanism name>**: <where it hurt, with task-NN reference, suggested fix>

例：reviewer 强制派遣 — task-05 是 3 行改动，reviewer 往返耗时 > 修复本身，建议增加微小改动豁免门。

## 5. Per-Task Execution Table

| Task ID | Title | Worker | Started | Completed | Duration |
|---|---|---|---|---|---|
| 01 | ... | inline | <iso> | <iso> | <hh:mm:ss> |
| 02 | ... | sub-agent | <iso> | <iso> | <hh:mm:ss> |

数据来源：`tasks.yaml` 中各 task 的 `started` / `completed` / `worker`。
Token 消耗不统计，跨 mode 不可比。

## 6. 矛盾条款

在任务执行过程中，是否遇到了任何矛盾条款？
```

## Promotion

写完后，重新检查 §3 / §4 / §6，并按下面规则处理：

| 来源 | 动作 |
|---|---|
| 跨 story 可复用的正面机制 | 提议加固到 `SKILL.md` 或 `references/` |
| 跨 story 反复出现的负面机制 | 提议调整阈值、删除条款或重构 reference |
| §6 中的矛盾条款 | 必须提给用户决定，不能静默接受 |
| 仅本 story 相关的发现 | 留在 `story-summary.md`，随归档冻结 |

不要静默修改 kickoff 本体。调整建议需要在对话中明确提出。
