---
name: ashare-assistant
description: >
  A-share trading workflow for market review, stock picking, and trading plan.
  Use when user asks for "复盘", "选股", "交易计划", "明天买什么", or "review".
---

# A股交易助手

## 目标产物

1. `~/.ashare-assistant/data/{DATE}/market_review.md`
2. `~/.ashare-assistant/data/{DATE}/analysis/candidates.json`
3. `~/.ashare-assistant/data/{DATE}/trading_plan.md`

## Iron Laws

<HARD-GATE>
1. NO step N+1 WITHOUT finishing step N.
2. NO fabrication. 只允许使用输入文件中的事实和数字。
3. A股交易规则：T+1，最小交易单位 100 股，涨跌停规则必须遵守。
4. 风控失败时必须修订计划，不能直接结束流程。
</HARD-GATE>

## 执行环境

脚本位于 skill 安装目录下的 `scripts/` 子目录。**必须在 skill 安装目录下**以 `-m scripts.<module>` 方式调用，否则相对导入会失败：

```bash
# 正确
cd <skill_install_dir>
python -m scripts.trade_review --output ...

# 错误（会报 ModuleNotFoundError）
python scripts/trade_review.py --output ...
```

**python 命令降级策略**：部分系统只有 `python3`，没有 `python`。若 `python -m scripts.xxx` 报 `command not found`，改用 `python3 -m scripts.xxx`。

## Workflow

### Step 1. 准备数据

```bash
DATE=$(date +%Y-%m-%d)
DATA_DIR=~/.ashare-assistant/data/${DATE}

if [ -d "${DATA_DIR}/filtered" ] && [ "$(ls -A "${DATA_DIR}/filtered")" ]; then
  echo "数据已就绪: ${DATA_DIR}"
else
  ashare-collect --date ${DATE} --verbose
fi
```

### Step 2. 复盘

读取并执行复盘说明：`references/market-review.md`  
产出：`{DATA_DIR}/market_review.md`

### Step 3. 选股

读取并执行选股说明：`references/stock-pick.md`  
产出：`{DATA_DIR}/analysis/candidates.json`

### Step 4. 交易计划

读取并执行交易计划说明：`references/trading-plan.md`  
产出：`{DATA_DIR}/trading_plan.md`

### Step 5. 风控与日志

```bash
python -m scripts.risk_check \
  --input ${DATA_DIR}/analysis/candidates.json

python -m scripts.validate_output \
  --input ${DATA_DIR}/analysis/candidates.json || true

python -m scripts.decision_logger \
  --input ${DATA_DIR}/analysis/candidates.json
```

## Done 判定

以下三项全部满足才算完成：

1. 三个目标产物文件都存在且非空。
2. `risk_check.py` 通过。
3. `decision_logger.py` 成功写入日志。

## References

1. `references/market-review.md`
2. `references/stock-pick.md`
3. `references/trading-plan.md`
