# Code Review Protocol

当**本 wave 所有 task 的代码都写完并 `completed`**、即将进入 wave-scope review 时，读取本文件。

## Hard Constraint

review 必须在**隔离上下文**中运行，绝不能 inline。

可选方式：

| 方式 | 何时使用 |
|---|---|
| **Sub Agent** | 默认。派 `agents/code-reviewer.md` |
| **Tmux** | 当前环境没有 sub-agent，或用户明确要求其他 runtime / 模型 |

Self-review 禁止。你可以修复 reviewer 的反馈，但不能自己充当 reviewer。

## Review Granularity

kickoff skill 的 review 粒度是 **wave**，不是 task：

- 每个 wave 只做**一次** review
- review 的 diff 覆盖本 wave 内**全部 task** 的改动
- 通过后**一次** git commit，commit message 概括 wave 目标
- `reviewer` 和 `commit` 写在 `waves[]` 末项，不写在 task 上

## Reviewer Input

reviewer 接收三段串接内容：

1. **Protocol body**：`agents/code-reviewer.md`
2. **本 wave 所有 task 的 spec**：按 wave 内顺序把各 `<story-dir>/tasks/task-NN.md` 串接，每段前加 `# Task NN` 分隔
3. **Diff context**：本 wave 的聚合 git diff，新文件也要包含

diff 必须聚合本 wave 所有 task 的 `files_modified`，不要拿某个 task 的 diff 单独 review：

```bash
# WAVE_FILES = 本 wave 全部 task 的 files_modified 并集
git diff <wave-base>..HEAD -- $WAVE_FILES
```

`<wave-base>` 是上一 wave 的 commit（即 `waves[N-1].commit`；wave 1 用 story 开始前的 HEAD）。

可选第四段：

- `## Known False Positives`
- 仅当 `story-memory.md` 中存在与本 wave 相关的同名条目时附加

## Reviewer Checklist

reviewer 检查四件事：

1. **Must-Haves**：本 wave 每个 task 的 Acceptance Checklist 都被验证
2. **File Scope**：diff 不越出本 wave 所有 task `files_modified` 的并集
3. **Deviations**：diff 未偏离各 task 的 Objective，无未批准的 scope creep
4. **Tests**：各 task 的验证层级匹配其 `test_layer`，且覆盖 acceptance

## Severity Levels

| Level | Meaning |
|---|---|
| **CRITICAL** | 阻塞验收，必须修复 |
| **HIGH** | 显著风险或缺少 must-have |
| **MEDIUM** | 质量问题或部分偏离 |
| **LOW** | 次要备注，留给 orchestrator（编写方）参考 |

只有在 **零个 CRITICAL / HIGH** 时，verdict 才能是 `PASS`。

## Verdict Loop

| Verdict | 动作 |
|---|---|
| `PASS` | 做一次 git commit 覆盖本 wave 全部改动，然后 `omp kickoff task wave-update --reviewer <id> --commit <sha> ...` 记录到 `waves[]` |
| `NEEDS_FIX` | 留在本 wave，inline 修复 CRITICAL / HIGH（可跨 task 改），然后重新 review |
| `BLOCKED` | reviewer 缺上下文、spec 矛盾或信息不足；先解决 blocker，再重新 dispatch |

reviewer 不能改代码；所有修复都回到 orchestrator 主上下文完成。

## Recording

review 通过后一次性写入：

```bash
omp kickoff task wave-update --story-dir <root> --story <slug> --number <N> \
  --reviewer "<agent-id-or-tmux-runtime>" \
  --commit "<sha>" \
  --key-decision "..." --open-question "..." --next-focus "..."
```

说明：
- `--reviewer` / `--commit` 是本 wave 唯一一次记录；重跑 `wave-update` 会整体覆盖该 wave 的 snapshot
- 多轮 review 是正常现象，但只有最终通过的那次需要写入 `waves[]`
- 完整 review 历史在对话记录里，不落盘
