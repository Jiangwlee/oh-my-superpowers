# 策略进化（strategy-evolution）

> 本文档用于 `strategy-evolution` 能力：基于交易复盘、诊断结果和反馈沉淀，微调策略参数与知识库。

## 目标

- 小步调整 `strategy/active.yaml`（每次 1-2 项）
- 更新知识沉淀文件：
  - `evolution/feedback.md`
  - `evolution/selection_rules.md`
  - `evolution/known_pitfalls.md`

## 输入材料（按需读取）

1. `~/.ashare-assistant/data/{DATE}/trade_review.json`（若本次有交易复盘）
2. `~/.ashare-assistant/memory/decision_log.jsonl`
3. `evolution/feedback.md`
4. `strategy/active.yaml`
5. `evolution/selection_rules.md`
6. `evolution/known_pitfalls.md`

## 工作流

### 1. 先诊断，不要先改参数

- 找出最近一段时间的主要错误模式（择时、仓位、纪律、执行偏差）
- 判断问题来源：
  - 规则过松 / 过严
  - 数据质量问题
  - 用户执行问题（策略本身未必需要改）

### 2. 形成改动提案（最多 1-2 项）

每项提案必须包含：

- 改什么（字段路径）
- 为什么（依据哪类复盘证据）
- 预期改善什么
- 潜在副作用

### 3. 更新知识沉淀（优先于改参数）

- 可复用经验写入 `selection_rules.md`
- 明显错误模式写入 `known_pitfalls.md`
- 周度/月度统计结论写入 `feedback.md`

### 4. 修改 `strategy/active.yaml`（仅在证据充分时）

- 不修改 `strategy/default.yaml`
- 避免一次性多参数联动，降低归因难度

## 输出模板（建议）

```text
策略进化建议：
- 结论：本次 [仅更新知识库 / 更新知识库+微调参数]
- 主要问题：...
- 提案1：...
- 提案2（可选）：...
- 风险提示：...
```

## Guardrails

- 不要基于单日结果做大幅度调整
- 不要用“感觉”替代复盘证据
- 不要在 `critical` 账户状态下通过加大仓位来“挽回”
