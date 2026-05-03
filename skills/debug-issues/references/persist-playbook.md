# Persist Playbook

Phase 9 SOP. Save the debug session as a project-level playbook so the next investigator does not start from zero.

## Trigger

Persist when ANY:

- Total debug time > 30 min
- Symptom likely to recur (env / config / integration / network class)
- Spanned ≥ 2 layers (frontend + backend, or our code + 3rd-party)
- Root cause was hidden behind a misleading symptom

Otherwise, skip.

## Output

File path: `docs/debug/<symptom-slug>.md` at the project root.

Create `docs/debug/` if missing.

## Template

```markdown
# <Symptom name> 排查清单

## 适用症状

按出现顺序列出可观察的症状（错误信息、UI 现象、日志关键词）。

- <symptom 1>
- <symptom 2>

## 排查顺序

按"层"分小节，从外层到内层。每层：
1. 关键观察点（命令 / 工具 / 文件路径）
2. 异常判定 → 修复
3. 无异常则下钻到下一层

### 1. <层名>（如：浏览器层 / chrome-devtools）

- [ ] <检查点 1：具体命令或选择器>
- [ ] <检查点 2>

### 2. <层名>（如：服务端日志）

- [ ] <检查点 1>

### N. 端到端验收

- [ ] <一行可执行验收命令>

## 历史教训

| 日期 | 现象 | 根因 | 修复 |
|---|---|---|---|
| YYYY-MM-DD | <一行症状> | <一行根因，含 file:line 引用> | <一行修复> |
```

## Quality Gate

Before marking the playbook done:

- [ ] 症状段列出可复制粘贴的字符串（错误信息、日志关键词）
- [ ] 每一层至少含一个具体命令、文件路径或日志关键词
- [ ] 末尾含一行可执行的端到端验收命令
- [ ] 历史教训表每行引用 file:line 或 commit

## Anti-patterns

- Do NOT write a playbook for a one-off bug with no recurrence risk.
- Do NOT pad with generic debugging advice — this file is symptom-specific.
- Do NOT defer history rows — write them in the same session.
- Do NOT replace 历史教训 with a free-form changelog; the table format makes scanning fast.
