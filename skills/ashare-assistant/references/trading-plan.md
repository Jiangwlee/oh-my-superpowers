# 交易计划执行说明

## 目标

生成：`~/.ashare-assistant/data/{DATE}/trading_plan.md`

## 必要输入

1. `~/.ashare-assistant/data/{DATE}/market_review.md`
2. `~/.ashare-assistant/data/{DATE}/analysis/candidates.json`
3. `~/.ashare-assistant/data/{DATE}/analysis/trade_review.json`
4. `~/.ashare-assistant/data/{DATE}/analysis/holding_insight.json`
5. `~/.ashare-assistant/data/{DATE}/report/dr_*_brief.md`（可为空）
6. `skills/ashare-assistant/strategy/active.yaml`

## 前置脚本

```bash
DATE=$(date +%Y-%m-%d)

python scripts/trade_review.py \
  --output ~/.ashare-assistant/data/${DATE}/analysis/trade_review.json \
  --strategy strategy/active.yaml

python scripts/holding_insight.py \
  --output ~/.ashare-assistant/data/${DATE}/analysis/holding_insight.json \
  --strategy strategy/active.yaml
```

## 步骤

1. 结合复盘与候选股，形成每只股票的交易动作。
2. 若存在深研文件，用于校准仓位乘数；不存在则乘数视为 `x1.0`。
3. 结合 `trade_review.json` 与 `holding_insight.json` 完成账户层约束。
4. 逐股给出：入场条件、止盈、止损、持有周期、目标股数。
5. 所有股数向下取整到 100 股整数倍。
6. 汇总总仓位并与市场强弱建议对齐。

## 输出骨架

```markdown
# 交易计划 - {DATE}

## 一、账户状态
## 二、交易复盘（当日执行情况）
## 三、持仓洞察
## 四、明日交易计划
## 五、执行优先级
## 六、仓位分配汇总
## 七、策略回顾
## 八、知识库积累
```

## 后置脚本

```bash
DATE=$(date +%Y-%m-%d)

python scripts/risk_check.py \
  --input ~/.ashare-assistant/data/${DATE}/analysis/candidates.json

python scripts/decision_logger.py \
  --input ~/.ashare-assistant/data/${DATE}/analysis/candidates.json
```

## 约束

1. 不能新增输入之外的股票与价格。
2. 股数必须是 100 的整数倍。
3. `risk_check.py` 失败必须回滚修订计划后重试。
