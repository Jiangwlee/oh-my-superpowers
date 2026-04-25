# Story Memory Guideline

`story-memory.md` 是每个 story 的显式学习摘要。创建、追加或收尾这个文件时，读取本指南。

## Purpose

`story-memory.md` 记录**跨 commit、但仍局限于当前 story** 的发现。目标有二：

1. 跨 `/compact` 续接：新会话读它就能复原"我在做什么、踩过什么坑"
2. 减少重复：避免在新 commit 里重复推导、重复被 reviewer 误报

## Location

固定路径：

`<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story-memory.md`

该文件在 `omp kickoff story init` 时创建为空壳，随着 story 推进逐步补全。

## Write Authority

只允许 orchestrator 写入。

| 角色 | 权限 |
|---|---|
| orchestrator | 唯一写者；负责筛选、压缩、追加 |
| sub-agent | 只读；可在回报中给候选 |
| reviewer | 只读；可消费 `Known False Positives` |

单写者是为了让它保持摘要，而不是流水账。

## Structure

最多三个 section；没有内容就省略该 section。

```markdown
# Story Memory: <slug>

## Patterns
- <cross-commit reusable discovery>; seen in: <commit-sha-or-description>

## Gotchas
- <subtle trap, with enough context that the next commit avoids it>

## Known False Positives (for reviewers)
- <check that looks wrong but is intentional, with the reasoning>
```

每条 entry 至少包含：

| 字段 | 要求 |
|---|---|
| What | 观察本身，要具体到下一个 commit 可以复用 |
| Where / Why | 建立该结论的 commit / 决策理由 |
| Pointer | 可选；必要时给 commit hash、issue 链接、讨论位置 |

禁止粘贴原始 reviewer 报告、长段引用或无结构 dump。

## Lifecycle

| 阶段 | 动作 |
|---|---|
| **Creation** | `omp kickoff story init` 写入空占位（标题 + 三个空 section） |
| **Accumulation** | 每次 commit PASS 后，用自己的话提炼跨 commit 可复用发现，再追加到对应 section |
| **Consumption** | 续 session 时（`/compact` 后）必须先读；派 sub-agent reviewer 时把相关 `Known False Positives` 注入 prompt |
| **Promotion at close** | Phase 3 写 `story-summary.md` 时重新审视每条 entry：跨 story 可复用的提议晋升；仅本 story 相关的留在归档里 |

任何 promotion 都必须是显式动作，不能静默发生。

## Anti-Patterns

| 不要这样做 | 原因 |
|---|---|
| 逐字粘贴 reviewer 报告 | `story-memory.md` 是摘要，不是日志 |
| 写"适用于所有 story"的规则 | 那些应进入 `CLAUDE.md` 或全局 insight |
| 让 sub-agent 直接编辑 | 多写者必然带来漂移与重复 |
| 依赖归档 story 反查跨 story 经验 | 归档后内容冻结；复用应通过 promotion 完成 |

## Relationship to Other Files

| File | Role | Writer |
|---|---|---|
| `story.md` | Story 叙事：Goal / Context / Scope | orchestrator |
| `story-memory.md` | 跨 commit / 跨 `/compact` 学习摘要 | orchestrator |
| `story-summary.md` | Phase 3 收尾的四段式短总结 | orchestrator |

文件边界必须清晰，不要混写。
