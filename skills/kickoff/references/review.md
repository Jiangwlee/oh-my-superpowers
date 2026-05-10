# Code Review Protocol

派 reviewer 把 task 从 `done` 推进到 `reviewed` 前读本文件。Review 由 task 状态机驱动；何时派遣由 developer 决定（单 task 推进或批量推进），最终在 Phase 3 前所有 task 必须 ∈ {reviewed, dropped}。

## Hard Constraint

Review 必须在**隔离上下文**中执行。Developer 主上下文自评禁止；developer 可以根据 reviewer 输出修复，但不得自任 reviewer。

## Reviewer 派遣

| 选项 | 何时选 | 说明 |
|---|---|---|
| **Sub Agent**（默认） | 多文件 / 跨 spec 的累积 review | 派 `agents/code-reviewer.md`；Claude Code 原生 sub-agent 隔离上下文，无 timeout 风险 |
| **跨 runtime tmux** | 单点深度查询、特殊调用方需要 | claude → codex；codex → claude；按 `commands.md` 派遣；适合"窄而深"的问题 |

Codex / Pi 等跨 runtime 在大 diff 上易 timeout（实测 codex 4 commit / 170 行 review 跑 41 tool use 仍未出 verdict）；多文件 review 默认走 sub-agent。

## Review Granularity

Review 粒度是**累积 done diff**——自上次 reviewed 状态以来落到 done 的全部 task 累积 diff。可单 task 推进，可批量推进；developer 自主决定。

```bash
# BASE = 上次任一 task 进入 reviewed 时该 task 的 commit；
# 本 story 首次 review 时 BASE = story 开始前的 HEAD（git merge-base 或显式记录）
git diff <BASE>..HEAD
```

## Reviewer Input

Reviewer 接收三段串接内容：

1. **Protocol body**：`agents/code-reviewer.md`
2. **Story 上下文**：`<story-dir>/story.md` 的 Goal / Scope / 红线
3. **Diff**：本轮覆盖的累积 diff

可选第四段：

- `## Known False Positives` — 仅当 journal 已有相关 ISSUE-NNN dismissed 条目且本次改动相关时附加

## Reviewer Checklist

Reviewer 检查五件事：

1. **Goal alignment**：diff 是否真的推进 `story.md` 的 Goal
2. **Scope discipline**：diff 是否在 Scope (In) 内、未触碰 Scope (Out)
3. **Tests**：测试覆盖是否匹配改动层级（unit / integration / e2e）
4. **Code quality**：边界条件、错误处理、命名、明显反模式
5. **Cross-PR semantic regression**：当 PR 给 service 接口引入"按调用方语义切换"的可选参数（如 `actor?` / `model?` / `silent?`）时，必须 grep 该函数所有调用栈，验证既存调用方在新语义下不被静默穿透前序 PR 守过的红线

## Severity Levels

| Level | Meaning |
|---|---|
| **CRITICAL** | 阻塞 review，必须修复 |
| **HIGH** | 显著风险或缺少 must-have |
| **MEDIUM** | 质量问题或部分偏离 |
| **LOW** | 次要备注，留给 developer 参考 |

只有在**零 CRITICAL / 零 HIGH** 时，verdict 才能是 `PASS`。

## Developer Triage（L3 验证）

Reviewer finding **不等于**已确认 bug。Reviewer 在隔离上下文里基于 plausible 的代码读法提出问题，可能基于错误的代码假设、过时的 schema 认知、或漏看的现有约束。Developer 必须先 L3 验证再进入修复讨论。

每个 CRITICAL / HIGH / MEDIUM finding 处理顺序：

1. **L3 验证**：grep 实际代码 / cat schema / inspect 类型定义，确认 reviewer 描述的代码状态属实
2. **属实 → 进入修复讨论**：与用户讨论 fix 方案与优先级
3. **不属实 → 直接 dismiss**：在 journal 写一条 `## ISSUE-NNN open` + 紧接 `## ISSUE-NNN update dismissed`（或对单条 finding 直接补一条 NOTE），写明 "L3 verified: <claim> not present, dismissed"，**不**把 plausible-but-wrong finding 转给用户选 fix

未经 L3 验证就把 reviewer claim 当成 fact 提给用户，会污染决策且浪费用户精力。

## Verdict → State Transition

| Verdict | Journal entry | Task 状态迁移 |
|---|---|---|
| `PASS` | `## T<n>[,T<m>...] [reviewed]` | done → reviewed |
| `NEEDS_FIX` | `## T<n> [needs_fix]` | done → needs_fix；developer 修复 commit 后写新 `## T<n> [done]` 进入下一轮 review |
| `BLOCKED` | 不推进状态；写 NOTE entry 描述 blocker | 先解决 blocker（缺 context / spec 不清），再重派 |

NEEDS_FIX 连续 3 次未 PASS → 停下，把 review 报告 + 当前 diff 提给用户决定。

## Recording

Review 历史以 journal entry 形式落盘（`[reviewed]` / `[needs_fix]` + ISSUE）。完整的 reviewer 输出报告**不**整体落盘——只把"对未来有复用价值的发现"提炼为 ISSUE 或在 NOTE entry 中记一两行。
