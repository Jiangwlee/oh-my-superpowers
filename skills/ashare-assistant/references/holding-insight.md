# 持仓洞察（holding-insight）

> 本文档用于阶段 6 / 独立触发 `holding-insight` 能力。仅关注持仓规则引擎，不包含完整复盘流程。

## 触发场景

- 用户询问：`持仓建议` / `持仓分析` / `加减仓` / `该买还是该卖`
- 已完成 `market-review` / `trading-plan` 后，希望对当前持仓做动作建议

## 输入依赖

- `~/.ashare-assistant/data/{DATE}/broker_account.json`（若存在）
- `strategy/active.yaml`
- 市场状态 `regime`（`strong` / `neutral` / `weak`）

如不确定数据目录路径，先阅读 `references/data-collect.md`。

## 执行命令

```bash
# 输出结构化 JSON
python3 scripts/holding_insight.py \
  --strategy strategy/active.yaml \
  --regime neutral \
  --output ~/.ashare-assistant/data/{DATE}/holding_insight.json

# 输出可读文本（便于终端快速查看）
python3 scripts/holding_insight.py \
  --strategy strategy/active.yaml \
  --regime neutral \
  --text
```

## 输出要求

- 每只持仓必须给出动作建议：`add` / `hold` / `sell`
- 必须包含触发规则、建议价格、建议数量（100 股整数倍）
- 当无持仓时返回空结果，并明确说明“当前无持仓”

## 分析重点（LLM 阅读 JSON 后总结）

- 哪些仓位属于止损/止盈驱动
- 哪些仓位属于趋势弱化（如跌破均线）驱动
- 是否与当前 `regime` 或账户状态冲突（例如弱市重仓）
- 优先执行顺序（先减仓风险项，再处理加仓机会）

## 与交易复盘的关系

- `holding-insight` 是面向“当前持仓动作建议”
- `trade-review` 是面向“计划 vs 实际执行差异诊断”
- 若用户问“今天交易执行得怎么样”，优先用 `references/trade-review.md`
