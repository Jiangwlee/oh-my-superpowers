# Code Review Protocol

发起一个 review 单元前读取本文件。Review 是 Phase 3 前的硬门槛。

## Hard Constraint

Review 必须在**隔离上下文**中运行。

| 形态 | 选 | 说明 |
|---|---|---|
| **全 diff review**（多文件 + 跨 spec / story） | **Sub Agent** | 默认。派 `agents/code-reviewer.md`。跨工具 dispatch 在多文件 review 上易 timeout（实测 codex 4 commit / 170 行 review 跑 41 tool use 仍未出 verdict） |
| **单点深度查询**（具体函数 / 单文件代码问题） | **跨工具 Tmux** | claude → openai，codex → claude，按 `commands.md` 派遣 Codex / Pi / Claude；适合"窄而深"的问题 |

主上下文自评禁止。Orchestrator 可以修复 reviewer 反馈，但不得自任 reviewer。

## Review Granularity

Review 粒度是**review 单元**——自上次 review pass 以来的全部 commit。

- 单次 review 范围 ≤ 10 个 commit / 500 行 diff
- review 不通过的改动用新 commit 修复后再次 review；不要 revert 已 commit
- 进入 Phase 3 前所有 commit 必须 review pass

## Reviewer Input

Reviewer 接收三段串接内容。

1. **Protocol body**：`agents/code-reviewer.md`
2. **Story 上下文**：`<story-dir>/story.md` 的 Goal / Context / Scope 三段
3. **Diff**：本 review 单元覆盖的全部 commit 的累计 diff

```bash
# BASE = 上次 review pass 时的 commit；本 story 首次 review 时 BASE = story 开始前的 HEAD
git diff <BASE>..HEAD
```

可选第四段：

- `## Known False Positives`
- 仅当 `story-memory.md` 中存在与本次改动相关的同名条目时附加

## Reviewer Checklist

Reviewer 检查四件事：

1. **Goal alignment**：diff 是否真的推进 `story.md` 的 Goal
2. **Scope discipline**：diff 是否在 Scope 内，无未批准的 scope creep
3. **Tests**：测试覆盖是否匹配改动层级（unit / integration / e2e）
4. **Code quality**：边界条件、错误处理、命名、明显的反模式

## Severity Levels

| Level | Meaning |
|---|---|
| **CRITICAL** | 阻塞 commit，必须修复 |
| **HIGH** | 显著风险或缺少 must-have |
| **MEDIUM** | 质量问题或部分偏离 |
| **LOW** | 次要备注，留给 orchestrator 参考 |

只有在**零 CRITICAL / 零 HIGH** 时，verdict 才能是 `PASS`。

## Orchestrator Triage

Reviewer finding **不等于**已确认 bug。Reviewer 在隔离上下文里基于 plausible 的代码读法提出问题，可能基于错误的代码假设、过时的 schema 认知、或漏看的现有约束。Orchestrator 必须先 L3 验证再进入修复讨论。

每个 CRITICAL / HIGH / MEDIUM finding 处理顺序：

1. **L3 验证**：grep 实际代码 / cat schema 文件 / inspect 类型定义，确认 reviewer 描述的代码状态属实
2. **属实 → 进入修复讨论**：与用户讨论 fix 方案与优先级
3. **不属实 → 直接 dismiss**：在 review 报告里记一句 "L3 verified: <claim> not present, dismissed"，**不**把 plausible-but-wrong 的 finding 转给用户选 fix

未经 L3 验证就把 reviewer claim 当成 fact 提给用户，会污染决策且浪费用户精力。

## Verdict Loop

| Verdict | 动作 |
|---|---|
| `PASS` | 把本轮可复用经验追加到 `story-memory.md`（按 `story-memory-guideline.md` 判断） |
| `NEEDS_FIX` | 用新 commit 修复 CRITICAL / HIGH，重新 review；连续 3 次仍未 PASS 时停下，把 review 报告 + 当前 diff 提给用户决定 |
| `BLOCKED` | reviewer 缺上下文 / spec 矛盾 / 信息不足；先解决 blocker，再重新 dispatch |

Reviewer 不能改代码；所有修复都回到 orchestrator 主上下文完成。

## Recording

Review 历史只保留在对话记录里，不落盘。`story-memory.md` 只记录跨 review 单元可复用的发现，不记录完整 review 报告。
