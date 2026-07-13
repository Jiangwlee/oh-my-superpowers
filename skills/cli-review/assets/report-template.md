# AXI CLI Review — <cli-name>

**Target:** `<path reviewed>`
**Scope:** static source review against 10 AXI principles
**Reviewed files:** `<file1>`, `<file2>`, …

## 合规汇总

| # | 原则 | 裁定 | 严重度 |
|---|------|------|--------|
| 1 | Token-efficient output | violation / compliant / unverified | blocking / advisory / — |
| 2 | Minimal default schemas | … | … |
| 3 | Content truncation | … | … |
| 4 | Pre-computed aggregates | … | … |
| 5 | Definitive empty states | … | … |
| 6 | Structured errors & exit codes | … | … |
| 7 | Ambient context | … | … |
| 8 | Content first | … | … |
| 9 | Contextual disclosure | … | … |
| 10 | Consistent help | … | … |

**Blocking: N ｜ Advisory: N ｜ Unverified: N**

## Findings

按严重度排序，blocking 在前。每条按此结构（字段全部据实填，不要照抄示例值）：

### [<severity>] 原则 <n><sub> — <一句话标题>

- **位置**：`<file:line>`
- **证据**：
  ```
  <从源码引用的实际片段>
  ```
- **问题**：<该片段为何产生歧义 / agent 会如何误读>
- **修复**：<改哪里、改成什么>

（对每个 finding 重复上述块。unverified 的原则单列一节说明「源码未覆盖，无法判定」，不计入违规。）

## 总评

一句话结论：该 CLI 在 <agent-facing> 维度的主要风险是 <…>；优先修 blocking N 项，advisory 按 token 收益排期。
