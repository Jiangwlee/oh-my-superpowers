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
- 必须包含触发规则、建议价格、建议数量（**100股整数倍，这是A股强制规定**）
- 当无持仓时返回空结果，并明确说明"当前无持仓"

### ⚠️ A股最小交易单位规则（强制，不可违反）

1. 所有买入/卖出建议的数量必须是**100股的整数倍**（1手 = 100股）
2. **持仓 ≤ 100股时**：不建议部分减仓（无法执行），只能建议"全部清仓"或"继续持有"
3. 减仓建议时，先计算减仓金额，再除以当前价格，向下取整至100的整数倍
4. 若取整后减仓数量为0（即计划减仓金额不足一手），改为"小幅减仓意义不大，建议继续持有或全部清仓"
5. 禁止出现"减仓X%"这类百分比建议，必须换算为具体股数（100股整数倍）

## 分析重点（LLM 阅读 JSON 后总结）

- 哪些仓位属于止损/止盈驱动
- 哪些仓位属于趋势弱化（如跌破均线）驱动
- 是否与当前 `regime` 或账户状态冲突（例如弱市重仓）
- 优先执行顺序（先减仓风险项，再处理加仓机会）

## 与交易复盘的关系

- `holding-insight` 是面向“当前持仓动作建议”
- `trade-review` 是面向“计划 vs 实际执行差异诊断”
- 若用户问“今天交易执行得怎么样”，优先用 `references/trade-review.md`
