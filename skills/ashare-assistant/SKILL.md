---
name: ashare-assistant
description: >
  Full-stack A-share trading assistant with explicit capabilities for market review, stock picking,
  trading plan, trade review, holding insight, and strategy evolution.
  Use when user says "复盘"、"选股"、"交易计划"、"交易复盘"、"持仓建议"、"策略进化"、
  "明天买什么"、"今天行情"、"检查执行"、"加减仓"。
capabilities:
  - data-collect
  - market-review
  - stock-pick
  - trading-plan
  - trade-review
  - holding-insight
  - strategy-evolution
---

# A股交易助手（ashare-assistant）

## Prerequisite Check (Required)

1. `python3 --version` (3.10+)
2. `python3 -c "import yaml"` (依赖缺失时按 `requirements.txt` 安装)

<HARD-GATE>
NO ANALYSIS WITHOUT RUNNING `collect_sentiment.py` FIRST.
NO TRADING PLAN WITHOUT COMPLETING `data-collect -> market-review -> stock-pick` FIRST.
NO COMPLETION WITHOUT WRITING `~/.ashare-assistant/data/{DATE}/report.md` FIRST.
</HARD-GATE>

## 能力矩阵

- `data-collect`: 统一采集多源数据并写入 `~/.ashare-assistant/data/{DATE}/collect/`，同时执行缓存清理。
- `market-review`: 收盘后行情复盘、题材/资金/情绪分析。
- `stock-pick`: 基于趋势扫描与题材筛选候选，触发深度研究批处理。
- `trading-plan`: 结合候选与持仓，生成次日交易计划并落盘 `report.md` / `candidates.json`。
- `trade-review`: 计划 vs 实际执行差异复盘，输出 `trade_review.json`。
- `holding-insight`: 对持仓给出加仓/减仓/持有建议，输出 `holding_insight.json`。
- `strategy-evolution`: 基于复盘反馈调整策略参数与知识沉淀（谨慎、少量变更）。

## 核心约束

- 禁止猜测数据；数据源失败时明确标注并降级。
- 先读落盘文件再总结，不以中间推断替代最终输出。
- 策略修改每次最多 1-2 个参数，必须写明原因与预期影响。
- HTML 解析依赖脚本实现，禁止临时正则解析网页。

## Workflow

### 1. `data-collect`（必需）

按 `references/data-collect.md` 执行。

### 2. `market-review`

按 `references/market-review.md` 执行。
如需详细分析框架，按需读取 `references/analysis-framework.md`。

### 3. `stock-pick`

按 `references/stock-pick.md` 执行。

### 4. `trading-plan`

按 `references/trading-plan.md` 执行。
终态至少包含：
- `~/.ashare-assistant/data/{DATE}/report.md`
- `~/.ashare-assistant/data/{DATE}/candidates.json`
- `~/.ashare-assistant/memory/decision_log.jsonl`（校验通过时）

### 5. `trade-review`（可独立触发）

按 `references/trade-review.md` 执行。
触发词：`交易复盘` / `检查执行` / `review` / `今天交易怎么样`

### 6. `holding-insight`（可独立触发）

按 `references/holding-insight.md` 中“持仓洞察”章节执行。
触发词：`持仓建议` / `持仓分析` / `加减仓` / `该买还是该卖`

### 7. `strategy-evolution`（按需）

优先读取：
- `references/evolution.md`
- `evolution/feedback.md`
- `strategy/active.yaml`

## 目录约定

- 缓存：`~/.ashare-assistant/cache/`
- 数据：`~/.ashare-assistant/data/{DATE}/`
- 记忆：`~/.ashare-assistant/memory/decision_log.jsonl`
- 券商数据：`~/.ashare-assistant/broker_data/`
