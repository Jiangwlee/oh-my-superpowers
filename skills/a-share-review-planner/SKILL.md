---
name: a-share-review-planner
description: Use when user wants to review A-share market after close,
  scan for trend/theme stocks, and generate next-day trading plan.
  Combines data collection scripts with LLM analysis for daily review,
  stock selection, and evolving trading strategies.
---

# A股复盘与交易计划

## Overview

本 Skill 帮助用户完成每日收盘后的A股复盘，包括：
1. 采集多源市场数据（新闻、舆情、资金流向、大盘云图）
2. 分析市场环境、识别题材线索
3. 基于内置趋势扫描结果筛选候选标的
4. 制定明确的交易计划（入场/止盈/止损/仓位）
5. 回顾并微调交易策略

**核心原则**：LLM 做判断（分析推理、策略调整），代码做执行（数据采集、API调用）。

## When to Use

- 用户说"复盘"、"今日回顾"、"明日计划"等
- 每个交易日收盘后运行一次
- 用户要求分析最新市场行情时

## Workflow

完整工作流分为4个阶段，**必须按顺序执行**。

---

### 阶段1: 数据采集

运行数据采集脚本，收集所有数据源。

```bash
cd {SKILL_DIR}
python3 scripts/collect_sentiment.py \
  --output-dir /tmp/a-share-review/{DATE} \
  --news-count 20 \
  --taoguba-count 20
```

其中 `{DATE}` 为当天日期（如 `2026-02-17`），`{SKILL_DIR}` 为本 Skill 所在目录。

脚本会并发采集以下数据源，单个失败不影响其他源：
- **交易日期** → `trade_date.json`
- **金融界新闻** → `news_headline.json` / `news_realtime.json` / `news_opportunity.json` / `news_daily.json` / `news_flash.json`
- **板块资金摘要** → `market_sectors.json`（净流入前5+后5板块）
- **淘股吧精华帖** → `taoguba_hot.json`
- **同花顺涨停快照** → `ths_snapshot.json`（连板天梯 + 最强板块）
- **趋势扫描结果** → `trend_scan.json`（人气榜前200趋势评分）+ `trend_report.md`（人类可读报告）
- 采集结果汇总 → `collection_summary.json`

趋势扫描已集成到采集脚本中，默认自动执行（扫描200只约2-3分钟）。可通过 `--no-scan-trends` 跳过。

**检查 `collection_summary.json`**，确认各数据源状态。如有失败，提示用户但继续分析可用数据。

---

### 阶段2: 数据读取

读取所有采集到的数据文件，整理关键信息。必须读取的文件：

1. `/tmp/a-share-review/{DATE}/collection_summary.json` — 确认采集状态
2. `/tmp/a-share-review/{DATE}/news_headline.json` — A股头条（含指数、成交额等宏观信息）
3. `/tmp/a-share-review/{DATE}/news_daily.json` — 每日财经（政策/宏观）
4. `/tmp/a-share-review/{DATE}/news_opportunity.json` — 机会情报
5. `/tmp/a-share-review/{DATE}/market_sectors.json` — 板块资金摘要（净流入前5+后5）
7. `/tmp/a-share-review/{DATE}/taoguba_hot.json` — 淘股吧精华帖（最重要的舆情源）
8. `/tmp/a-share-review/{DATE}/trend_scan.json` — 趋势扫描完整结果
8b. `/tmp/a-share-review/{DATE}/trend_report.md` — 趋势股筛选报告（人类可读）
8c. `/tmp/a-share-review/{DATE}/ths_snapshot.json` — 同花顺涨停/板块快照

同时读取策略和历史经验文件：

9. `strategy/active.yaml` — 当前生效策略
10. `evolution/feedback.md` — 交易诊断反馈（如有内容）
11. `evolution/selection_rules.md` — 选股规则修正（如有内容）
12. `evolution/known_pitfalls.md` — 已知交易陷阱（如有内容）

---

### 阶段3: 分析

**必须严格按照 `references/analysis-framework.md` 的6步框架执行分析。**

请读取 `references/analysis-framework.md` 获取完整的分析模板，它包含：
- 每个步骤必须读取的数据
- 每个步骤必须回答的问题
- 每个步骤的输出格式
- 判断参考标准

6个步骤概要：
1. **市场环境判断** → 强弱评级、主线风格、仓位建议
2. **题材线索识别** → 主线题材、新兴线索、衰退警示、市场情绪
3. **个股筛选** → 趋势股（来自 trend_scan.json，4星以上）+ 题材股（来自人气榜相关标的）
4. **交易计划制定** → 每只候选股的入场/止盈/止损/仓位，参考 `strategy/active.yaml`
5. **风险检查** → 集中度、与昨日对比、持仓调整建议、特殊风险
6. **策略回顾与微调** → 评估当前策略是否适配，必要时调整 `active.yaml`

**重要**：不要跳过任何步骤，不要遗漏必答问题。

---

### 阶段4: 输出交易计划

将分析结论整理为完整的交易计划报告，格式如下：

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

（重复以上格式，总共5-10只候选股）

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

### 策略文件结构

- `strategy/default.yaml` — **基线策略**，不可修改，作为参照
- `strategy/active.yaml` — **当前生效策略**，LLM 每次复盘时可读取并微调

`active.yaml` 中包含趋势股和题材股的交易策略（入场/止损/止盈/持有周期/仓位），以自然语言描述。

### 修改规则

1. 每次最多修改1-2个参数，避免大幅调整
2. 必须在 `evolution_log` 中记录修改日期和原因
3. 如果 `active.yaml` 与 `default.yaml` 偏差过大，提醒用户审核
4. 修改格式示例：

```yaml
evolution_log:
  - date: "2026-02-18"
    change: "趋势股止损改为'跌破MA10且量能放大2倍以上'"
    reason: "近期MA20止损太慢，导致利润回吐过多"
```

---

## Historical Experience（历史经验注入）

以下文件会被复盘分析读取，影响分析决策：

| 文件 | 来源 | 作用 |
|------|------|------|
| `evolution/feedback.md` | 交易诊断 Skill（未来开发） | 最近一次诊断的改进建议 |
| `evolution/selection_rules.md` | 诊断/人工总结 | 选股规则的增删修正 |
| `evolution/known_pitfalls.md` | 历史交易教训 | 已知陷阱，避免重复犯错 |

当这些文件有内容时，分析过程必须纳入考量。当内容为空（仅有注释头部）时，跳过即可。

---

## Command Reference

### 数据采集

```bash
# 完整采集（推荐，含趋势扫描）
python3 scripts/collect_sentiment.py \
  --output-dir /tmp/a-share-review/{DATE} \
  --news-count 20 \
  --taoguba-count 20

# 精简采集（测试用，跳过趋势扫描）
python3 scripts/collect_sentiment.py \
  --output-dir /tmp/a-share-review/{DATE} \
  --news-count 5 \
  --taoguba-count 5 \
  --no-scan-trends

# 限制扫描范围（仅前50名）
python3 scripts/collect_sentiment.py \
  --output-dir /tmp/a-share-review/{DATE} \
  --news-count 20 \
  --taoguba-count 20 \
  --popularity-max 50
```

### 输出文件

| 文件 | 说明 |
|------|------|
| `trade_date.json` | 最近交易日期 |
| `news_headline.json` | A股头条 |
| `news_realtime.json` | 市况直击 |
| `news_opportunity.json` | 机会情报 |
| `news_daily.json` | 每日财经 |
| `news_flash.json` | 7x24快讯 |
| `market_sectors.json` | 板块资金摘要（净流入前5+后5板块） |
| `taoguba_hot.json` | 淘股吧精华帖（含正文摘要） |
| `ths_snapshot.json` | 同花顺涨停快照（连板天梯 + 最强板块） |
| `trend_scan.json` | 趋势扫描完整结果（含评分/信号/情绪） |
| `trend_report.md` | 趋势股筛选报告（人类可读） |
| `collection_summary.json` | 采集结果汇总 |

---

## Notes

1. **数据时效性**：所有采集数据为即时快照，仅当天有效。不要用过期数据做分析。
2. **趋势股来源**：趋势股评分和筛选已集成在采集脚本中（`trend_scan.json` / `trend_report.md`），无需外部 Skill。
3. **淘股吧重要性**：淘股吧是最重要的舆情源，它反映了活跃交易者的真实观点和情绪，特别是对于题材股和市场情绪的判断。
4. **用户持仓**：如果用户提供了当前持仓，必须在风险检查步骤中评估持仓调整建议。
5. **不要猜测数据**：如果某个数据源采集失败，明确说明数据缺失，不要用臆测代替真实数据。
6. **策略修改谨慎**：策略调整是渐进式的，每次最多改1-2个参数。只有在明确证据支持时才修改。
