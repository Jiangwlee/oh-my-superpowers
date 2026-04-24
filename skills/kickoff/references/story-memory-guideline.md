# Story Memory Guideline

`story-memory.md` 是每个 story 的显式学习摘要。创建、追加或收尾这个文件时，读取本指南。

## Purpose

`story-memory.md` 记录**跨 task、但仍局限于当前 story** 的发现，避免在新 wave 里重复踩坑、重复推导、重复被 reviewer 误报。

## Location

固定路径：

`<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story-memory.md`

该文件在 `story init` 时创建为空壳，随着 story 推进逐步补全。

## Write Authority

只允许 orchestrator 写入。

| 角色 | 权限 |
|---|---|
| orchestrator | 唯一写者；负责筛选、压缩、追加 |
| sub-agent | 只读；可在 completion report 中给候选 |
| reviewer | 只读；可消费 `Known False Positives` |

单写者是为了让它保持 **digest**，而不是流水账。

## Structure

最多三个 section；没有内容就省略该 section。

```markdown
# Story Memory: <slug>

## Patterns
- <cross-task reusable discovery>; seen in: task-NN, task-MM

## Gotchas
- <subtle trap, with enough context that the next task avoids it>

## Known False Positives (for reviewers)
- <check that looks wrong but is intentional, with link to the deciding task>
```

每条 entry 至少包含：

| 字段 | 要求 |
|---|---|
| What | 观察本身，要具体到别的 task 可以复用 |
| Where / Why | 建立该结论的 task 或理由 |
| Pointer | 可选；必要时给 commit、讨论或 PR 注释 |

禁止粘贴原始 worker 报告、长段引用或无结构 dump。

## Lifecycle

| 阶段 | 动作 |
|---|---|
| **Creation** | `omp kickoff story init` 写入空占位（标题 + 三个空 section） |
| **Accumulation** | 每个 task 完成后，用自己的话提炼跨 task 可复用发现，再追加到对应 section |
| **Consumption** | 每个 wave 开始前必须先读；派 sub-agent 时把相关内容注入 prompt |
| **Promotion at close** | 在 Phase 5 重新审视每条 entry：跨 story 可复用的提议晋升；仅本 story 相关的留在归档里 |

任何 promotion 都必须是显式动作，不能静默发生。

## Anti-Patterns

| 不要这样做 | 原因 |
|---|---|
| 逐字粘贴 worker 报告 | `story-memory.md` 是摘要，不是日志 |
| 写“适用于所有 story”的规则 | 那些应进入 `CLAUDE.md` 或 `insight` |
| 让 worker 直接编辑 | 多写者必然带来漂移与重复 |
| 依赖归档 story 反查跨 story 经验 | 归档后内容冻结；复用应通过 promotion 完成 |

## Relationship to Other Files

| File | Role | Writer |
|---|---|---|
| `story.md` | Story 叙事：Goal / Context / Scope / Explore Result | orchestrator |
| `tasks.yaml` | 任务状态与 `waves[]` 快照的 SSOT | orchestrator + sub-agents（经 CLI） |
| `tasks/task-NN.md` | 单 task 的 JIT spec | orchestrator |
| `story-memory.md` | 跨 task 学习摘要 | orchestrator |
| `story-summary.md` | Phase 5 自评报告 | orchestrator |

文件边界必须清晰，不要混写。
