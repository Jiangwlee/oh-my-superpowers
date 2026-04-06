# Review Output Format
#
# Severity 定义、结构化输出模板、Verdict 语义。
# review 执行者必须严格遵守此格式输出。

## Severity 定义

| 级别 | 含义 | 用户响应 |
|------|------|----------|
| **P0 — Critical** | 必须修复：bug、安全漏洞、数据丢失风险 | 不修不能提交 |
| **P1 — High** | 应当修复：性能问题、缺失错误处理、需求未满足 | 强烈建议修复 |
| **P2 — Medium** | 建议修复：代码风格、可读性、轻微改进 | 用户决定 |
| **P3 — Low** | 可选：替代方案建议、nitpick | 仅供参考 |

### Severity 判断规则

- 导致运行时崩溃或数据损坏 → P0
- 安全漏洞（可被利用） → P0
- 逻辑错误但不会崩溃 → P1
- 性能退化（可量化） → P1
- 需求未完全满足 → P1
- 命名不清晰、可读性差 → P2
- 可以更优但当前实现不算错 → P3

## 输出模板

```markdown
## Summary

[1-2 句：整体评估，直接说结论。禁止"代码整体不错"式的客套。]

## Issues

- **[P0]** `file/path:line` — 问题描述
  - Evidence: [代码中观察到的具体证据，引用关键代码片段]
  - Suggested fix: [具体可操作的修复建议]

- **[P1]** `file/path:line` — 问题描述
  - Evidence: [证据]
  - Suggested fix: [建议]

- **[P2]** `file/path:line` — 问题描述
  - Suggested fix: [建议]

- **[P3]** `file/path:line` — 问题描述
  - Suggested fix: [建议]

## Verdict

APPROVE | REQUEST_CHANGES
[如果 REQUEST_CHANGES，列出需要修复的 issue 编号]
```

### 输出规则

1. Issues 按 severity 从高到低排列（P0 在前）
2. 同级别按文件路径字母序排列
3. 每个 issue 必须包含 `file/path:line` 精确定位
4. P0/P1 必须有 Evidence 字段；P2/P3 可省略
5. 无 issue 时 Issues 区域输出 "No issues found."
6. 禁止编造不存在的问题

## Verdict 语义

| Verdict | 条件 | 后续动作 |
|---------|------|----------|
| **APPROVE** | 无 P0 且无 P1 | 呈现给用户，流程结束 |
| **REQUEST_CHANGES** | 存在 P0 或 P1 | 呈现给用户，用户决定是否修复 |
