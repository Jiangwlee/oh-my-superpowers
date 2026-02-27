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

## 日内行情工具

以下工具输出 JSON 到 stdout，**按需调用**，不需要全部运行。

### 1. 日内行情摘要
```bash
python scripts/intraday_summary.py --code {CODE} --date {YYYYMMDD}
```
输出：30分钟聚合 K 线、开盘跳空幅度、全天统计。用于了解某只股票当天整体走势。

### 2. 操作时刻现场还原
```bash
python scripts/trade_context.py --code {CODE} --date {YYYYMMDD} \
  --time {HHMMSS} --price {PRICE} --window 30
```
`--time` 和 `--price` 来自 `broker_account.json` 的 `order_list` 字段。
输出：操作前后各 30 分钟的分钟级行情。用于判断买入/卖出时刻的市场背景。

### 3. 开盘背景（反事实基线）
```bash
python scripts/opening_context.py --code {CODE} --date {YYYYMMDD}
```
输出：前收盘价、MA5/MA10/MA20、跳空幅度、开盘30分钟表现。
用于判断：**如果在开盘前看到这些信息，你会怎么做？** 与实际操作对比。

### 4. 相对强弱
```bash
python scripts/relative_strength.py --code {CODE} --date {YYYYMMDD} \
  --benchmark 000001
```
输出：5 个时间节点（10:00/11:00/13:30/14:30/15:00）个股 vs 大盘对比。
用于判断个股是否在强于/弱于大盘的情况下被操作。

## 步骤

1. 读取 `trade_review.json`，了解账户快照与合规情况（仅事实，不含质量评分）。
2. 针对每笔当日成交（来自 `broker_account` `order_list`），**自主判断操作质量**：
   - 调用工具 2（操作时刻还原）看清入场/离场背景
   - 调用工具 3（开盘背景）建立反事实基线
   - 调用工具 4（相对强弱）判断操作时个股是强是弱
   - 自行决定这笔交易是否有价值，不受预设规则约束
3. 结合复盘与候选股，形成每只股票的交易动作。
4. 若存在深研文件，用于校准仓位乘数；不存在则乘数视为 `x1.0`。
5. 结合 `holding_insight.json` 完成账户层约束。
6. 逐股给出：入场条件、止盈、止损、持有周期、目标股数。
7. 所有股数向下取整到 100 股整数倍。
8. 汇总总仓位并与市场强弱建议对齐。

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
4. `trade_review.json` 中只有 `position_flaw`/`discipline_flaw` 是硬约束，其余 `info` 级别仅供参考。
