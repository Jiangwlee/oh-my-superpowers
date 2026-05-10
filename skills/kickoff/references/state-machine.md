# Task State Machine

进入或推进 task 状态前读本文件。状态机是 kickoff 的核心 invariant——任何绕行（如 in_progress 直接到 reviewed、planned 直接到 done）都构成 Hard Gate 阻断。

## Six States

| 状态 | 语义 | 进入条件 |
|---|---|---|
| `planned` | story.md `## Task 计划` 中列出，尚未动 | story init 时 task 默认状态 |
| `in_progress` | 正在实现 | journal 写入 4 段证据（assumption/verify/fact/edit target），且每段非空 |
| `done` | 代码已 commit，等待 review | 至少一次 commit 已写入；journal 写 decision/diff |
| `needs_fix` | review 不通过，需返工 | reviewer verdict = NEEDS_FIX |
| `reviewed` | review 通过（终态） | reviewer verdict = PASS（可由单 task 或批量 reviewed entry 推进） |
| `dropped` | 不做了（终态） | scope 调整 / 决定废弃；journal 写 reason |

## Legal Transitions

仅以下 7 种迁移合法：

```
planned ──→ in_progress       （developer 进入实现）
planned ──→ dropped           （scope 调整）
in_progress ──→ done          （commit + journal 出口）
in_progress ──→ dropped       （决定不做）
done ──→ reviewed             （reviewer PASS）
done ──→ needs_fix            （reviewer NEEDS_FIX）
needs_fix ──→ done            （修复 commit）
```

**禁止迁移（任一发生即 Hard Gate 阻断）**：

- `planned → done`：必须先 in_progress 写证据
- `planned → reviewed`：同上 + 必须有真实 commit
- `in_progress → reviewed`：必须先 done
- `needs_fix → reviewed`：fix 必须重新 commit 进入 done，再次 review
- `reviewed → 任何状态`：reviewed 是终态
- `dropped → 任何状态`：dropped 是终态

## Current-State Query Rule

每个 task 的当前状态 = **journal 中最后一条同 task ID entry 的 `[<state>]` 标记**。

- 单个 task：`grep '^## T2 ' journal.md | tail -1`
- 批量 reviewed entry（如 `## T2,T3 [reviewed]`）同时推进多个 task；解析时把每个 ID 都当作"最后状态 = reviewed"。

## Evidence Check（in_progress 进入门槛）

`in_progress` entry 必须包含全部 4 个非空字段：

- `assumption:` 我以为是什么
- `verify:` 我跑了什么命令（可重跑：rg / sed / cat / git 等）
- `fact:` 命令输出告诉我代码实际是什么
- `edit target:` 准备改哪些文件 / 哪些函数

任一字段缺失或值为空 → `omp kickoff status` 输出 `Evidence: ✗`，禁止动手 edit；developer 必须补齐。这是反"凭记忆"机制的物证要求。

## Boundary with ISSUE

ISSUE 与 task 状态机**互不重叠**：

| 场景 | 用谁 |
|---|---|
| review 不通过，task 需返工 | `needs_fix` 状态 + 在 done→needs_fix 迁移时引用 reviewer 报告 |
| 旁路问题（不绑定具体 task / 跨多 task / 暂不修） | `ISSUE-NNN` 条目 |
| review 提出"建议但非必修"（LOW） | `ISSUE-NNN` 或忽略，由 developer 判断 |

简单返工走 `done → needs_fix → done` 闭环；只有当问题需要拆为新 task 或跨 story 跟踪时才升级为 ISSUE。

## Phase 3 Ready Predicate

`omp kickoff status` 输出 `Phase 3 ready: YES` 当且仅当：

- 所有出现在 story.md `## Task 计划` 中的 task ID 都在 journal 出现过（无未启动 task）
- 所有 task 当前状态 ∈ {reviewed, dropped}
- 无 open ISSUE

任一条件不满足 → `Phase 3 ready: NO — <具体原因>`。
