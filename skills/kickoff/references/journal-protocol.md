# Journal Protocol

写 journal entry 或查询当前状态前读本文件。journal 是 story 的过程事件流，所有 task 状态、ISSUE 状态、关键 NOTE 都按时间序列追加。

## File Role

- **journal.md = 过程 SoT**：task 状态、ISSUE 状态、决策、坑点
- **story.md = 契约 SoT**：Goal / Scope / 必读 / 红线 / Task 计划

冲突时以 journal 为准（task 状态尤其如此）。`story.md` 末尾的 `## Summary` 在 init 时已预置占位骨架，Phase 3 收尾时填写各子节——它是给外部读者的归档产物，不是 journal 的副本。

## Append Rules

1. **所有 entry 按时间顺序追加**——不重排已有 entry。
2. **旧 entry 不允许修改**——状态变化用新 entry 表达，绝不回头改原条目（含改标题状态、改 body 字段）。
3. **当前状态 = 最后一条同 ID entry 的状态标记**。

违反任一条 → `omp kickoff status` 可能给出错误的当前状态判断，且破坏审计可追溯性。

## Entry Types（5 类）

### TASK Entry（in_progress / done / needs_fix / dropped）

入口（in_progress）— **4 段证据全部必填且非空**：

```markdown
## T2 implement [in_progress] 14:22
assumption:  ingest.py 入口按 mimetype 分发
verify:      rg -n "def dispatch" scripts/ingest.py
fact:        dispatch() 只处理 url，本地路径无既有分支
edit target: scripts/ingest.py:dispatch(), scripts/ingest_pdf.py(new)
```

出口（done）— 必填 `decision` / `diff`，`gotcha` 可空：

```markdown
## T2 implement [done] 14:55
decision: defuddle parse --markdown，与 read-url 同链路
gotcha:   扫描版 PDF defuddle 输出空 md，需在 ingest 层加非空校验
diff:     scripts/ingest_pdf.py (+62), scripts/ingest.py (+18)
```

needs_fix（reviewer 输出 NEEDS_FIX 后）：

```markdown
## T2 implement [needs_fix] 16:10
verdict:  NEEDS_FIX
reviewer: codex sub-agent
batch:    T2
issues:   CRITICAL: ingest_pdf 缺 timeout；HIGH: 异常未捕获
```

修复后回到 done：发起新 entry `## T2 implement [done] 16:35`，描述修复结果；再次 review 走批量或单 task reviewed entry。

dropped（任何时刻）：

```markdown
## T7 add-cli-flag [dropped] 17:20
reason: scope 调整 — 该 flag 挪到下个 story 处理
```

### REVIEWED Entry（可批量推进）

```markdown
## T2,T3 [reviewed] 16:10
verdict:  PASS
reviewer: codex sub-agent
batch:    T2 + T3
```

支持单 task 或批量。`batch:` 字段是冗余但便于人读，不影响解析（解析靠 header `T2,T3`）。

### ISSUE Entry（append-only）

open（首次发现）：

```markdown
## ISSUE-001 open 14:50
source: T2 review
fact:   ingest.py 缺 path 长度校验
plan:   T5 决定是否升 task
```

update（状态迁移）：

```markdown
## ISSUE-001 update fixed 16:30
by:     T5 commit abc1234

## ISSUE-002 update dismissed 17:15
by:     L3 verified — claim not present in current code
```

ISSUE 状态可流转：`open` ↔ `fixed` / `dismissed`。当前状态由最后一条同 ID entry 决定。**不允许改原 ISSUE-001 open 条目**——状态变化必须用 update。

## Grep 模式（常用查询）

| 目的 | 命令 |
|---|---|
| 某 task 的全部 entry | `grep '^## T2 ' journal.md` |
| 某 task 当前状态 | `grep '^## T2 ' journal.md \| tail -1` |
| 所有 done 待 review 的 task | `grep -E '^## T[0-9]+ .*\[done\]' journal.md` |
| 所有 in_progress task | `grep -E '^## T[0-9]+ .*\[in_progress\]' journal.md` |
| 所有 ISSUE 当前状态 | `grep '^## ISSUE-' journal.md` |
| 跨 task 找决策 | `grep '^decision:' journal.md` |
| 跨 task 找坑点 | `grep '^gotcha:' journal.md` |

`omp kickoff status` 自动做这些查询并按状态机规则汇总输出。

## HTML Comment 处理

journal.md 模板顶部用 `<!-- ... -->` 包裹的字段说明区块**不会**被 status 解析当作 entry。真实 entry 必须写在注释块外部。模板中的 `## T<n>` 字面例子放在注释里，不会污染 status 输出。
