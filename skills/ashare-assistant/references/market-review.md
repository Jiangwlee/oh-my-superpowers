# 阶段2：数据读取

> 数据通过三层处理：`raw/`(采集) → `filtered/`(格式转换) → `report/`(子代理分析)
> 主 agent 仅读取 `filtered/` 中的 direct 文件和 `report/` 中的分析报告。
> 先读取 `filtered/index.md` 和 `report/index.md` 了解当日可用数据。

## 第一步：读取索引

| # | 文件 | 说明 |
|---|------|------|
| 0.1 | `~/.ashare-assistant/data/{DATE}/filtered/index.md` | filtered 层文件索引，标注每个文件的读取方式（direct/subagent） |
| 0.2 | `~/.ashare-assistant/data/{DATE}/report/index.md` | 子代理分析报告索引 |

## 第二步：读取子代理分析报告（report/）

子代理已对大文件做了语义压缩，主 agent 直接读取报告即可（每份约 3-5 KB）。

| # | 文件 | 用途 |
|---|------|------|
| 1 | `report/news_sentiment.md` | 新闻情绪分析：宏观政策信号、行业催化、市场数据提取、情绪判断、关键新闻 Top10 |
| 2 | `report/social_sentiment.md` | 社交情绪分析：淘股吧整体情绪、热点题材、个股热度、精华观点、一致性预期 |

> 如果 `report/` 下有 `dr_{CODE}_brief.md`，是第 3.5 步个股深研的子代理输出，在第 3.5 步使用。

## 第三步：读取 filtered/ 中的 direct 文件

以下文件体积较小（合计约 15 KB），主 agent 直接读取。

| # | 文件 | 用途 |
|---|------|------|
| 3 | `filtered/run_id.md` | 本次运行标识（`run_id` 用于后续 JSON 输出和 decision_log） |
| 4 | `filtered/market_sectors.md` | 板块资金摘要（涨跌幅、资金净流入排名） |
| 5 | `filtered/funding.md` | 资金面：北向净流入、主力净流入 Top20、趋势候选股资金排名 |
| 6 | `filtered/us_market.md` | 美股行情（若文件不存在或显示"数据不可用"则跳过） |
| 7 | `filtered/news_flash.md` | 7×24 快讯（短消息，体积较小） |
| 8 | `filtered/ths_report.md` | 涨停综合报告（含连板天梯、最强板块、热门板块个股明细） |
| 9 | `filtered/trend_report.md` | 趋势股报告（⚠️ 必须完整读取，不得只读部分） |
| 10 | `filtered/collection_summary.md` | 采集概况 |

## 第四步：读取其他文件

| # | 文件 | 用途 |
|---|------|------|
| 11 | `~/.ashare-assistant/data/{DATE}/broker_account.json` | 账户资金+持仓（如存在） |
| 12 | `strategy/active.yaml` | 当前生效策略（含 `account_mode` 定义） |
| 13 | `evolution/feedback.md` | 诊断反馈（有内容则读） |
| 14 | `evolution/selection_rules.md` | 选股规则修正（有内容则读） |
| 15 | `evolution/known_pitfalls.md` | 已知交易陷阱（有内容则读） |

## 数据量预估

| 层 | 内容 | 预估大小 |
|---|------|---------|
| report/ 子代理报告 | news_sentiment + social_sentiment | ~6-10 KB |
| filtered/ direct 文件 | 市场数据 + 快讯 + 涨停 + 趋势 | ~20 KB |
| 其他文件 | broker + strategy + evolution | ~5 KB |
| **主 agent 总读取量** | | **~30-35 KB (~10K tokens)** |

> 对比旧方案的 ~674 KB (~225K tokens)，压缩至约 5%。

## ⚠️ 不再直读的文件

以下文件已由子代理处理，主 agent **不应直接读取**（读取它们会导致 token 溢出）：

- `filtered/news_headline.md` (240 KB) → 已压缩到 `report/news_sentiment.md`
- `filtered/news_daily.md` (42 KB) → 已压缩到 `report/news_sentiment.md`
- `filtered/news_opportunity.md` (71 KB) → 已压缩到 `report/news_sentiment.md`
- `filtered/news_realtime.md` (49 KB) → 已压缩到 `report/news_sentiment.md`
- `filtered/taoguba_hot.md` (60 KB) → 已压缩到 `report/social_sentiment.md`
- `filtered/taoguba_recommend.md` (18 KB) → 已压缩到 `report/social_sentiment.md`
- `filtered/taoguba_hot_discussion.md` (9 KB) → 已压缩到 `report/social_sentiment.md`
- `raw/trend_scan.json` (138 KB) → 已压缩到 `filtered/trend_report.md`
