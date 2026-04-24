# Self-Evaluation Guideline

Phase 5: write `story-summary.md` to retrospect this story and feed back into kickoff itself. Self-evaluation is **knowingly biased** (you grading yourself), but it is the only retrospective signal available — treat it as input, not verdict.

---

## File location

`<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story-summary.md`

## When to write

Only after E2E + Acceptance has passed (Phase 5 part 1). Don't write while debugging — wait until the story is closeable.

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

<理由：与"不用 kickoff 直接写代码"对比，列出具体的质量增益（如 bug 拦截、测试覆盖完备、接口清晰）或额外开销（过度 ceremony、上下文切换成本）。
量化能量化的（避免/产生 bug 数、返工次数），定性的写具体场景。>

## 3. Positive Mechanisms

哪些条款和机制起到了正面作用？

- **<mechanism name>**: <how it helped, with task-NN reference>
- ...

例：JIT Spec — task-03 的 spec 因为读了 task-01/02 的 story-memory，提前规避了 X 问题。

## 4. Negative Mechanisms

哪些条款和机制起到了负面作用？

- **<mechanism name>**: <where it hurt, with task-NN reference, suggested fix>
- ...

例：reviewer 强制派遣 — task-05 是 3 行改动，reviewer 往返耗时 > 修复本身，建议增加微小改动豁免门。

## 5. Per-Task Execution Table

| Task ID | Title | Worker | Started | Completed | Duration |
|---|---|---|---|---|---|
| 01 | ... | inline | <iso> | <iso> | <hh:mm:ss> |
| 02 | ... | sub-agent | <iso> | <iso> | <hh:mm:ss> |

数据来源：`tasks.yaml` 中各 task 的 `started` / `completed` / `worker`（CLI 自动维护）。
Token 消耗不统计 —— 跨 mode 不可比，统一放弃。

## 6. 矛盾条款

在任务执行过程中，是否遇到了任何矛盾条款？
```

## Promotion

写完后，回看 §3 / §4 / §6：

- **跨 story 可复用**的正面机制 → 加固到 SKILL.md 主流程或 references/。
- **跨 story 反复出现**的负面信号 → 调整阈值、删除条款、或重构对应 reference。
- §6 的矛盾条款 → 必须当场提给用户，决定是修订还是接受冲突。
- 仅本 story 相关的发现留在 story-summary.md，随归档一起冻结。

调整建议直接在对话中提给用户决定，不要静默修改 skill 本体。
