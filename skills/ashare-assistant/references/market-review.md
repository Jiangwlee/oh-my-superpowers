# 阶段2：数据读取

读取以下文件并整理关键信息：

| # | 文件 | 用途 |
|---|------|------|
| 0 | `~/.ashare-assistant/data/{DATE}/run_id.json` | **本次运行标识**（必读，后续 JSON 输出和 decision_log 均使用其中的 `run_id` 值） |
| 1 | `~/.ashare-assistant/data/{DATE}/news_headline.json` | A股头条（指数、成交额） |
| 2 | `~/.ashare-assistant/data/{DATE}/news_daily.json` | 每日财经（政策/宏观） |
| 3 | `~/.ashare-assistant/data/{DATE}/news_opportunity.json` | 机会情报 |
| 4 | `~/.ashare-assistant/data/{DATE}/market_sectors.json` | 板块资金摘要 |
| 4.1 | `~/.ashare-assistant/data/{DATE}/funding.json` | 资金面：`northbound_net`（北向净流入亿元）、`main_force_top20`（全市场主力净流入前20）、`trend_candidates_funding`（趋势候选股净流入排名，第三步选股直接使用） |
| 5 | `~/.ashare-assistant/data/{DATE}/taoguba_recommend.json` | 淘股吧今日推荐（含帖子正文 `content`，用于潜在/新题材挖掘） |
| 6 | `~/.ashare-assistant/data/{DATE}/taoguba_hot_discussion.json` | 淘股吧热门讨论（含 `subject/body/quotecontent`，用于潜在/新题材挖掘） |
| 7 | `~/.ashare-assistant/data/{DATE}/taoguba_hot.json` | 淘股吧精华帖（用于识别已发酵热点题材 + 精华言论提炼） |
| 8 | `~/.ashare-assistant/data/{DATE}/ths_report.md` | 涨停综合报告（含5日趋势表、连板天梯、最强板块、热门板块个股明细） |
| 9 | `~/.ashare-assistant/data/{DATE}/trend_scan.json` | 趋势扫描结果 |
| 10 | `~/.ashare-assistant/data/{DATE}/trend_report.md` | 趋势股报告（人类可读） |
| 10.5 | `~/.ashare-assistant/data/{DATE}/us_market.json` | 美股行情（若文件不存在或 `market_status == "unavailable"` 则跳过，不影响分析流程） |
| 11 | `~/.ashare-assistant/data/{DATE}/broker_account.json` | 账户资金+持仓（如存在） |
| 12 | `strategy/active.yaml` | 当前生效策略（含 `account_mode` 定义） |
| 13 | `evolution/feedback.md` | 诊断反馈（有内容则读） |
| 14 | `evolution/selection_rules.md` | 选股规则修正（有内容则读） |
| 15 | `evolution/known_pitfalls.md` | 已知交易陷阱（有内容则读） |
