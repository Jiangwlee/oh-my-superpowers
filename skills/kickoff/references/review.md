# Code Review Protocol

发起一个 review 单元前读取本文件。Review 是 Phase 3 前的硬门槛。

## Hard Constraint

Review 必须在**隔离上下文**中运行。

| 优先级 | 方式 | 说明 |
|---|---|---|
| 1 | **跨工具 Tmux** | 默认。claude → openai，codex → claude，按 `commands.md` 派遣 Codex / Pi / Claude |
| 2 | **Sub Agent** | 跨工具派遣失败时降级使用，派 `agents/code-reviewer.md` |

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

## Verdict Loop

| Verdict | 动作 |
|---|---|
| `PASS` | 把本轮可复用经验追加到 `story-memory.md`（按 `story-memory-guideline.md` 判断） |
| `NEEDS_FIX` | 用新 commit 修复 CRITICAL / HIGH，重新 review；连续 3 次仍未 PASS 时停下，把 review 报告 + 当前 diff 提给用户决定 |
| `BLOCKED` | reviewer 缺上下文 / spec 矛盾 / 信息不足；先解决 blocker，再重新 dispatch |

Reviewer 不能改代码；所有修复都回到 orchestrator 主上下文完成。

## Recording

Review 历史只保留在对话记录里，不落盘。`story-memory.md` 只记录跨 review 单元可复用的发现，不记录完整 review 报告。
