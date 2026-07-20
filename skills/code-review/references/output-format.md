# Review Output Format
#
# Severity 定义、结构化输出模板、Verdict 语义。
# review 执行者必须严格遵守此格式输出。

## Severity 定义

| 级别 | 含义 | 处理方式 |
|------|------|----------|
| **P0 — Critical** | 可能造成数据丢失或损坏、严重安全突破、不可恢复故障或大范围中断 | 复核确认后优先修复并重新 review |
| **P1 — High** | 对用户或系统有明确重大影响的功能错误、安全问题、性能退化或需求缺失 | 复核确认后修复并重新 review |
| **P2 — Medium** | 影响有限但具体成立、值得修复的正确性、可靠性或维护性问题 | 复核确认后修复并重新 review |
| **P3 — Low** | 当前实现没有错误，仅为替代方案、风格偏好或 nitpick | 仅供参考，不触发修复循环 |

### Severity 判断规则

- Severity 按已证明的实际影响判断，不按问题类别或 reviewer 偏好判断
- 数据丢失或损坏、远程代码执行、认证绕过、不可恢复故障或大范围中断 → P0
- 具有明确重大影响的错误行为、范围受限但可利用的安全问题、严重性能退化或关键需求缺失 → P1
- 影响有限但有具体证据的正确性、可靠性或维护性问题 → P2
- 当前实现没有错误，只是可选替代方案、风格偏好或 nitpick → P3

## 输出模板

```markdown
## Summary

[1-2 句：整体评估，直接说结论。禁止"代码整体不错"式的客套。]

## Issues

- **[P0]** `file/path:line` — 问题描述
  - Evidence: [具体代码或行为、触发条件、实际影响]
  - Suggested fix: [具体可操作的修复建议]

- **[P1]** `file/path:line` — 问题描述
  - Evidence: [具体代码或行为、触发条件、实际影响]
  - Suggested fix: [建议]

- **[P2]** `file/path:line` — 问题描述
  - Evidence: [具体代码或行为、触发条件、实际影响]
  - Suggested fix: [建议]

- **[P3]** `file/path:line` — 问题描述
  - Evidence: [具体代码或行为、触发条件、实际影响]
  - Suggested fix: [建议]

## Verdict

APPROVE | REQUEST_CHANGES
```

### 输出规则

1. Issues 按 severity 从高到低排列（P0 在前）
2. 同级别按文件路径字母序排列
3. 每个 issue 必须包含 `file/path:line` 精确定位
4. 每个 issue 必须有 Evidence 字段，说明具体代码或行为、触发条件和实际影响
5. 无 issue 时 Issues 区域输出 "No issues found."
6. 禁止编造不存在的问题

## Verdict 语义

| Verdict | 条件 | 后续动作 |
|---------|------|----------|
| **APPROVE** | 无 P0、P1、P2 | 调用者复核；若无新的已确认问题，流程结束 |
| **REQUEST_CHANGES** | 存在 P0、P1 或 P2 | 调用者复核并修复已确认问题，然后重新 review |
