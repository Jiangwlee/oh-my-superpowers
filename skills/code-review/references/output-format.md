# Review Output Format
#
# Severity、Disposition、结构化输出模板与 Verdict 语义。
# review 执行者必须严格遵守此格式输出。

## Severity 定义

| 级别 | 含义 |
|------|------|
| **P0 — Critical** | 可能造成数据丢失或损坏、严重安全突破、不可恢复故障或大范围中断 |
| **P1 — High** | 对用户或系统有明确重大影响的功能错误、安全问题、性能退化或需求缺失 |
| **P2 — Medium** | 影响有限但具体成立的当前缺陷，或有证据支持的维护性改进 |
| **P3 — Low** | 当前实现没有错误，仅为表达打磨、替代方案、风格偏好或 nitpick |

### Severity 判断规则

- Severity 按已证明的实际影响判断，不按问题类别或 reviewer 偏好判断
- 数据丢失或损坏、远程代码执行、认证绕过、不可恢复故障或大范围中断 → P0
- 具有明确重大影响的错误行为、范围受限但可利用的安全问题、严重性能退化或关键需求缺失 → P1
- 影响有限但有具体证据的当前正确性或可靠性问题 → P2
- 当前行为正确，但存在具体维护成本 → P2
- 仅要求表达“更严谨”、更换命名、采用另一种实现或满足风格偏好，且不能证明当前影响 → P3

## Disposition 定义

Disposition 决定 finding 是否阻断完成，与 Severity 分开判断。

| Disposition | 条件 | 处理方式 |
|-------------|------|----------|
| **BLOCKING** | 当前变更造成可证明的错误行为、违反需求或契约，或者相关验证失败 | 修复后重新 review |
| **FOLLOW_UP** | 问题具体成立，但当前行为仍然正确，不需要在本轮自动修复 | 保留到最终报告，由用户决定 |
| **ADVISORY** | 替代方案、表达打磨、风格偏好或 nitpick | 仅供参考 |

默认映射：P0/P1 → `BLOCKING`；没有当前错误行为的 P2 → `FOLLOW_UP`；P3 → `ADVISORY`。

只有同时提供以下阻断证据，才能把 P2 标记为 `BLOCKING`：

- **Contract**：被违反的需求、接口、项目规则或行为契约
- **Trigger**：能够触发问题的输入、状态或操作
- **Impact**：当前可观察的错误结果
- **Verification**：能够证明修复有效的测试或检查

缺少任一项时，将 P2 标记为 `FOLLOW_UP`。措辞可以更精确但没有两种会导致不同执行结果的合理解释时，标记为 P3 / `ADVISORY`。

## 输出模板

```markdown
## Summary

[1-2 句：整体评估，直接说结论。禁止"代码整体不错"式的客套。]

## Issues

- **[P0]** `file/path:line` — 问题描述
  - Disposition: BLOCKING
  - Evidence: [具体代码或行为、触发条件、实际影响]
  - Contract: [违反的需求、接口、规则或契约]
  - Trigger: [触发输入、状态或操作]
  - Impact: [当前可观察的错误结果]
  - Verification: [修复后运行的测试或检查]
  - Suggested fix: [具体可操作的修复建议]

- **[P1]** `file/path:line` — 问题描述
  - Disposition: BLOCKING
  - Evidence: [具体代码或行为、触发条件、实际影响]
  - Contract: [违反的需求、接口、规则或契约]
  - Trigger: [触发输入、状态或操作]
  - Impact: [当前可观察的错误结果]
  - Verification: [修复后运行的测试或检查]
  - Suggested fix: [建议]

- **[P2]** `file/path:line` — 问题描述
  - Disposition: BLOCKING | FOLLOW_UP
  - Evidence: [具体代码或行为、触发条件、实际影响]
  - Contract: [仅 BLOCKING 必填]
  - Trigger: [仅 BLOCKING 必填]
  - Impact: [仅 BLOCKING 必填]
  - Verification: [仅 BLOCKING 必填]
  - Suggested fix: [建议]

- **[P3]** `file/path:line` — 问题描述
  - Disposition: ADVISORY
  - Evidence: [具体代码或行为、触发条件、实际影响]
  - Suggested fix: [建议]

## Verdict

APPROVE | APPROVE_WITH_FOLLOWUPS | REQUEST_CHANGES
```

### 输出规则

1. Issues 先列 `BLOCKING`，再列 `FOLLOW_UP` 和 `ADVISORY`；同一 Disposition 内按 severity 从高到低排列
2. 同级别按文件路径字母序排列
3. 每个 issue 必须包含 `file/path:line` 精确定位
4. 每个 issue 必须有 Disposition 和 Evidence 字段
5. 无 issue 时 Issues 区域输出 "No issues found."
6. 禁止编造不存在的问题
7. `BLOCKING` finding 必须包含 Contract、Trigger、Impact 和 Verification；缺少任一字段时不得阻断

## Verdict 语义

| Verdict | 条件 | 后续动作 |
|---------|------|----------|
| **APPROVE** | 无 finding | 调用者复核并结束流程 |
| **APPROVE_WITH_FOLLOWUPS** | 无 `BLOCKING`，但存在 `FOLLOW_UP` 或 `ADVISORY` | 结束自动循环，在最终报告中保留非阻断项 |
| **REQUEST_CHANGES** | 存在 `BLOCKING` | 调用者复核并修复已确认的 blocker，然后重新 review |
