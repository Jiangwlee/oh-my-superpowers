---
name: a-share-review-planner
description: Use when user says "复盘"、"今日回顾"、"明日计划"、"选股" or wants to
  review A-share market after close and generate next-day trading plan.
  Do NOT use on non-trading days or intraday.
---

# A股复盘与交易计划

<IMPORTANT>
在开始任何分析之前，必须遵守以下约束：

- **禁止猜测数据**：某数据源失败时，明确告知用户并跳过，不得用臆测填充
- **策略修改要谨慎**：每次最多调整 active.yaml 中 1-2 个参数，必须写明原因
- **数据时效性**：采集数据为当日快照，不得使用过期数据分析
</IMPORTANT>

## Overview

帮助用户完成每日收盘后的A股复盘：采集多源市场数据 → 分析市场环境与题材线索 → 筛选候选标的 → 制定含入场/止盈/止损/仓位的交易计划 → 微调交易策略。

**核心原则**：LLM 做判断（分析推理、策略调整），代码做执行（数据采集、API调用）。

## When to Use

- 用户说"复盘"、"今日回顾"、"明日计划"、"帮我选股"
- 每个交易日收盘后（15:00后）

## When NOT to Use

- 非交易日（节假日、周末）
- 盘中（数据不完整）

---

## Workflow

完整工作流分为 4 个阶段，**必须按顺序执行，不得跳过**。

### 阶段1：数据采集

运行数据采集脚本，收集所有数据源：

```bash
python3 {SKILL_DIR}/scripts/collect_sentiment.py \
  --output-dir /tmp/a-share-review/{DATE} \
  --news-count 20 \
  --taoguba-count 20
```

> 脚本参数详情及输出文件说明，参见 `references/commands.md`。

采集完成后读取 `/tmp/a-share-review/{DATE}/collection_summary.json`，确认各数据源状态。如有失败，告知用户并继续分析可用数据。

---

### 阶段2：数据读取

读取以下文件，整理关键信息：

| # | 文件 | 用途 |
|---|------|------|
| 1 | `/tmp/a-share-review/{DATE}/news_headline.json` | A股头条（指数、成交额） |
| 2 | `/tmp/a-share-review/{DATE}/news_daily.json` | 每日财经（政策/宏观） |
| 3 | `/tmp/a-share-review/{DATE}/news_opportunity.json` | 机会情报 |
| 4 | `/tmp/a-share-review/{DATE}/market_sectors.json` | 板块资金摘要 |
| 5 | `/tmp/a-share-review/{DATE}/taoguba_hot.json` | 淘股吧精华帖 ⭐ |
| 6 | `/tmp/a-share-review/{DATE}/ths_snapshot.json` | 涨停快照（连板天梯+最强板块） |
| 7 | `/tmp/a-share-review/{DATE}/trend_scan.json` | 趋势扫描结果 |
| 8 | `/tmp/a-share-review/{DATE}/trend_report.md` | 趋势股报告（人类可读） |
| 9 | `{SKILL_DIR}/strategy/active.yaml` | 当前生效策略 |
| 10 | `{SKILL_DIR}/evolution/feedback.md` | 诊断反馈（有内容则读） |
| 11 | `{SKILL_DIR}/evolution/selection_rules.md` | 选股规则修正（有内容则读） |
| 12 | `{SKILL_DIR}/evolution/known_pitfalls.md` | 已知交易陷阱（有内容则读） |

---

### 阶段3：分析

**必须严格按照 `{SKILL_DIR}/references/analysis-framework.md` 的 6 步框架执行**，不得跳过任何步骤或遗漏必答问题：

1. 市场环境判断 → 强弱评级、主线风格、仓位建议
2. 题材线索识别 → 主线题材、新兴线索、衰退警示、市场情绪
3. 个股筛选 → 趋势股（4星以上）+ 题材股（仅题材驱动市时）
4. 交易计划制定 → 每只候选股入场/止盈/止损/仓位，参考 active.yaml
5. 风险检查 → 集中度、与昨日对比、持仓调整建议、特殊风险
6. 策略回顾与微调 → 评估当前策略是否适配，必要时调整 active.yaml

---

### 阶段4：输出交易计划

按以下格式输出完整报告：

```markdown
# A股复盘报告 - {DATE}

## 一、市场环境
- 强弱评级：[强/中/弱]
- 主线风格：[题材驱动/趋势主导/混沌轮动]
- 仓位建议：[激进/标准/防守]
- 判断依据：...

## 二、题材线索
### 主线题材
- [题材名] | 阶段：[启动/加速/分歧/衰退] | 龙头：[个股]
### 新兴线索
- [题材名] | 催化：[事件] | 评估：[高/中/低]
### 衰退警示
- [题材名] | 信号：[具体信号]
### 市场情绪
[乐观/谨慎/恐慌] - [依据]

## 三、交易计划

### [代码] [名称] [类型：趋势/题材]
- **选股理由**：...
- **趋势评分**：[星级] [总分] [情绪颜色]（趋势股）
- **所属题材**：[题材名] | 阶段：[X]（题材股）
- **入场条件**：...
- **目标仓位**：...
- **止盈条件**：...
- **止损条件**：...
- **持有周期**：...
- **风险点**：...

（共 5-10 只候选股）

## 四、风险提示
- 集中度：[正常/偏高]
- 计划变更：[新增/移除/调整]
- 特殊风险：[如有]

## 五、策略调整
- 当前策略评估：[适用/需微调]
- 调整内容：[无/具体修改]
```

---

## Strategy Evolution（策略进化）

- `{SKILL_DIR}/strategy/default.yaml` — 基线策略，**不可修改**，仅作参照
- `{SKILL_DIR}/strategy/active.yaml` — 当前生效策略，每次复盘可微调

修改规则：每次最多改 1-2 个参数，必须在 `evolution_log` 中记录日期和原因：

```yaml
evolution_log:
  - date: "2026-02-18"
    change: "趋势股止损改为'跌破MA10且量能放大2倍以上'"
    reason: "近期MA20止损太慢，导致利润回吐过多"
```

若 active.yaml 与 default.yaml 偏差过大，需提醒用户审核。
