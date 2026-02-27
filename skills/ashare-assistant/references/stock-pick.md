# 选股执行说明

## 目标

生成：`~/.ashare-assistant/data/{DATE}/analysis/candidates.json`

## 必要输入

1. `~/.ashare-assistant/data/{DATE}/market_review.md`
2. `~/.ashare-assistant/data/{DATE}/filtered/run_id.md`

## 步骤

1. 从复盘报告提取 `market.regime`。
2. 提取候选股清单：代码、名称、行业/题材、核心逻辑、风险点。
3. 为每只股票给 `action`：
   - 买入/建仓 -> `buy`
   - 持有 -> `hold`
   - 卖出/清仓 -> `sell`
   - 其他 -> `watch`
4. 输出固定 JSON 结构。
5. 运行结构校验（仅告警）：

```bash
python -m scripts.validate_output \
  --input ~/.ashare-assistant/data/{DATE}/analysis/candidates.json || true
```

## 输出结构

```json
{
  "run_id": "YYYYMMDD-xxx-HHMMSS",
  "as_of_date": "YYYY-MM-DD",
  "market": { "regime": "strong" },
  "candidates": [
    {
      "code": "000001",
      "name": "示例",
      "score": 4.0,
      "type": "trend",
      "action": "watch",
      "sector": "示例板块",
      "position": 0,
      "thesis_short": "30字以内",
      "risk_note": "30字以内"
    }
  ],
  "risk_flags": {
    "data_degraded": false,
    "output_schema_invalid": false,
    "strategy_version_fallback": false
  }
}
```

## 约束

1. 顶层字段不增不减。
2. `action` 只允许 `buy/hold/sell/watch`。
3. `position` 固定为 `0`。
4. `thesis_short` 和 `risk_note` 各不超过 30 字。
