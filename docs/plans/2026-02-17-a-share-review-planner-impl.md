# A-Share Review Planner 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现一个 Agent Skill，完成 A 股每日复盘、选股、交易计划制定。

**Architecture:** scripts 负责数据采集（纯标准库 HTTP 客户端 + 淘股吧用 html.parser），LLM 负责分析推理。趋势评分复用已有 a-share-trend-scanner 的输出。所有配置和策略使用 YAML/Markdown 文件。

**Tech Stack:** Python 3.13（纯标准库，无第三方依赖），Agent Skills 规范（SKILL.md + scripts/ + references/）

---

## Task 1: 创建目录结构和基础文件

**Files:**
- Create: `skills/a-share-review-planner/scripts/__init__.py`
- Create: `skills/a-share-review-planner/scripts/fetchers/__init__.py`
- Create: `skills/a-share-review-planner/scripts/utils/__init__.py`
- Create: `skills/a-share-review-planner/strategy/default.yaml`
- Create: `skills/a-share-review-planner/strategy/active.yaml`
- Create: `skills/a-share-review-planner/evolution/feedback.md`
- Create: `skills/a-share-review-planner/evolution/selection_rules.md`
- Create: `skills/a-share-review-planner/evolution/known_pitfalls.md`

**Step 1: 创建目录结构**

```bash
mkdir -p skills/a-share-review-planner/{scripts/{fetchers,utils},references,strategy,evolution}
touch skills/a-share-review-planner/scripts/__init__.py
touch skills/a-share-review-planner/scripts/fetchers/__init__.py
touch skills/a-share-review-planner/scripts/utils/__init__.py
```

**Step 2: 创建策略模板文件**

`strategy/default.yaml` 和 `strategy/active.yaml`（内容相同，default 为基线不可修改）。
参考设计文档第7节。

**Step 3: 创建 evolution 占位文件**

每个文件写入简短的格式说明头部，内容为空。参考设计文档第8节。

**Step 4: 验证目录结构**

```bash
find skills/a-share-review-planner -type f | sort
```

**Step 5: Commit**

```bash
git add skills/a-share-review-planner/
git commit -m "feat: scaffold a-share-review-planner skill directory structure"
```

---

## Task 2: 实现 HTTP 客户端工具

**Files:**
- Create: `skills/a-share-review-planner/scripts/utils/http_client.py`

**Step 1: 实现 http_client.py**

纯标准库实现，包含：
- `http_json(url, method, payload, headers, timeout, retries)` → dict
- 自动重试（指数退避）
- 统一的 User-Agent
- JSON 请求/响应处理
- 超时和错误处理

参考 `a-share-trend-scanner/scripts/scan_a_share_trends.py` 中的 `_http_json` 函数，但独立为模块。

**Step 2: 手动测试**

```bash
cd skills/a-share-review-planner
python3 -c "
from scripts.utils.http_client import http_json
r = http_json('https://gateway.jrj.com/quot-feed/tradedate', method='POST',
              headers={'Origin':'https://summary.jrj.com.cn','Referer':'https://summary.jrj.com.cn/'})
print(r)
"
```

Expected: 返回包含交易日期的 JSON。

**Step 3: Commit**

```bash
git add skills/a-share-review-planner/scripts/utils/http_client.py
git commit -m "feat: add HTTP client utility with retry support"
```

---

## Task 3: 实现交易日期 fetcher

**Files:**
- Create: `skills/a-share-review-planner/scripts/fetchers/trade_date.py`

**Step 1: 实现 trade_date.py**

- `fetch_trade_date()` → str（YYYYMMDD 格式）
- 调用 `https://gateway.jrj.com/quot-feed/tradedate`

**Step 2: 手动测试**

```bash
cd skills/a-share-review-planner
python3 -c "
from scripts.fetchers.trade_date import fetch_trade_date
print(fetch_trade_date())
"
```

**Step 3: Commit**

```bash
git add skills/a-share-review-planner/scripts/fetchers/trade_date.py
git commit -m "feat: add trade date fetcher"
```

---

## Task 4: 实现新闻 fetcher

**Files:**
- Create: `skills/a-share-review-planner/scripts/fetchers/news.py`

**Step 1: 实现 news.py**

包含以下函数：
- `fetch_news_list(channel_num, info_cls, page_size=20)` → list[dict]
  - 统一调用 `gateway.jrj.com/jrj-news/news/queryNewsList`
- `fetch_news_flash(page_size=20)` → list[dict]
  - 调用 `gateway.jrj.com/jrj-news/news/queryNewsFlash`
- 便捷封装：
  - `fetch_headline()` → A股头条 (010/001062)
  - `fetch_realtime()` → 市况直击 (010/001140)
  - `fetch_opportunity()` → 机会情报 (010/001161)
  - `fetch_daily_finance()` → 每日财经 (103/001116)
- `fetch_all_news(page_size=20)` → dict，一次获取所有频道

**Step 2: 手动测试**

```bash
cd skills/a-share-review-planner
python3 -c "
from scripts.fetchers.news import fetch_all_news
import json
result = fetch_all_news(page_size=5)
for k, v in result.items():
    print(f'{k}: {len(v)} items')
    if v:
        print(f'  first: {v[0].get(\"title\", v[0].get(\"content\", \"?\"))[:60]}')
"
```

**Step 3: Commit**

```bash
git add skills/a-share-review-planner/scripts/fetchers/news.py
git commit -m "feat: add JRJ news fetcher (4 channels + flash)"
```

---

## Task 5: 实现大盘云图 + 资金流向 fetcher

**Files:**
- Create: `skills/a-share-review-planner/scripts/fetchers/market_overview.py`

**Step 1: 实现 market_overview.py**

包含：
- `fetch_market_cloud()` → dict：获取大盘云图原始数据
- `fetch_capital_flow()` → dict：获取资金流向原始数据
- `build_sector_summary()` → list[dict]：
  将 market + hq 数据合并，按行业聚合，输出：
  ```
  [
    {"name": "电子", "sid": 270000, "scale": 12.74,
     "sub_sectors": [{"name": "半导体", "sid": 270100, ...}],
     "total_netin": 123456789.0,      # 行业总资金净流入
     "top_netin_stocks": [...],        # 资金净流入前5个股
     "top_outflow_stocks": [...]},     # 资金净流出前5个股
    ...
  ]
  ```
  按 total_netin 降序排列。
- `fetch_market_overview()` → dict：一次调用，返回完整概览

**Step 2: 手动测试**

```bash
cd skills/a-share-review-planner
python3 -c "
from scripts.fetchers.market_overview import fetch_market_overview
import json
r = fetch_market_overview()
print(f'trade_date: {r[\"trade_date\"]}')
print(f'sectors: {len(r[\"sectors\"])}')
for s in r['sectors'][:5]:
    print(f'  {s[\"name\"]}: netin={s[\"total_netin\"]/1e8:.2f}亿')
"
```

**Step 3: Commit**

```bash
git add skills/a-share-review-planner/scripts/fetchers/market_overview.py
git commit -m "feat: add market cloud and capital flow fetcher"
```

---

## Task 6: 实现淘股吧 fetcher

**Files:**
- Create: `skills/a-share-review-planner/scripts/fetchers/taoguba.py`

**Step 1: 实现 taoguba.py**

- 使用标准库 `html.parser` 解析 HTML（不使用正则，不依赖 bs4）
- `fetch_taoguba_hot(count=20)` → list[dict]
  - 获取精华帖列表页
  - 提取：标题、URL、作者、日期、浏览数、评论数
  - 并发获取帖子正文（ThreadPoolExecutor）
- 如果 html.parser 解析过于困难，备选方案：在 SKILL.md 中引导 LLM 使用 browser 工具

参考 `github_cache/smartrade-adk/backend/crawlers/taoguba/tgb_jinghua.py` 的逻辑，
但改用标准库实现。

**Step 2: 手动测试**

```bash
cd skills/a-share-review-planner
python3 -c "
from scripts.fetchers.taoguba import fetch_taoguba_hot
posts = fetch_taoguba_hot(count=5)
for p in posts:
    print(f'{p[\"title\"][:40]} | {p[\"author\"]} | {p[\"date\"]}')
"
```

**Step 3: Commit**

```bash
git add skills/a-share-review-planner/scripts/fetchers/taoguba.py
git commit -m "feat: add taoguba hot posts fetcher"
```

---

## Task 7: 实现数据采集主入口

**Files:**
- Create: `skills/a-share-review-planner/scripts/collect_sentiment.py`

**Step 1: 实现 collect_sentiment.py**

CLI 入口，功能：
- 解析参数：`--date`, `--output-dir`, `--news-count`, `--taoguba-count`
- 并发调用所有 fetcher（ThreadPoolExecutor）
- 每个 fetcher 的结果写入独立 JSON 文件
- 生成 `collection_summary.json`（各源状态、数量、耗时）
- 单个数据源失败不影响其他源（容错）
- 输出进度信息到 stderr

```bash
python3 scripts/collect_sentiment.py \
  --date 2026-02-17 \
  --output-dir /tmp/review/2026-02-17 \
  --news-count 20 \
  --taoguba-count 20
```

输出文件列表：
```
{output-dir}/
├── trade_date.json
├── taoguba_hot.json
├── news_headline.json
├── news_realtime.json
├── news_opportunity.json
├── news_daily.json
├── market_cloud.json
├── capital_flow.json
└── collection_summary.json
```

**Step 2: 端到端测试**

```bash
cd skills/a-share-review-planner
python3 scripts/collect_sentiment.py --output-dir /tmp/review_test --news-count 5 --taoguba-count 5
ls -la /tmp/review_test/
cat /tmp/review_test/collection_summary.json
```

Expected: 所有 JSON 文件生成，summary 显示各源状态为 ok 或 error。

**Step 3: Commit**

```bash
git add skills/a-share-review-planner/scripts/collect_sentiment.py
git commit -m "feat: add collect_sentiment.py main entry for data collection"
```

---

## Task 8: 编写分析框架参考文档

**Files:**
- Create: `skills/a-share-review-planner/references/analysis-framework.md`

**Step 1: 编写 analysis-framework.md**

详细的 LLM 分析思考模板，包含：
1. 市场环境判断（输入数据清单 → 思考步骤 → 输出格式）
2. 题材线索识别（同上结构）
3. 个股筛选（同上结构）
4. 交易计划制定（同上结构）
5. 风险检查（同上结构）
6. 策略回顾与微调（同上结构）

每个步骤都明确：
- 必须读取哪些数据文件
- 必须回答的问题列表
- 输出格式模板

参考设计文档第6节，但更加具体和可操作。

**Step 2: 验证内容完整性**

确认所有6个步骤都有明确的输入/输出定义。

**Step 3: Commit**

```bash
git add skills/a-share-review-planner/references/analysis-framework.md
git commit -m "feat: add analysis framework reference document"
```

---

## Task 9: 编写 SKILL.md

**Files:**
- Create: `skills/a-share-review-planner/SKILL.md`

**Step 1: 编写 SKILL.md**

这是整个 Skill 的核心文件，指导 LLM 完成完整的复盘工作流。

结构：
```
---
name: a-share-review-planner
description: Use when user wants to review A-share market after close,
  scan for trend/theme stocks, and generate next-day trading plan.
  Combines data collection scripts with LLM analysis for daily review,
  stock selection, and evolving trading strategies.
---

# A股复盘与交易计划

## Overview
## When to Use
## Workflow
  ### 阶段1: 数据采集
  ### 阶段2: 数据读取
  ### 阶段3: 分析（指向 references/analysis-framework.md）
  ### 阶段4: 输出交易计划
## Strategy Evolution（策略进化机制）
## Historical Experience（历史经验注入）
## Command Reference（脚本调用参考）
## Output Format（输出格式）
## Notes
```

关键要点：
- 明确指导 LLM 先运行 scripts 再分析
- 指向 references/analysis-framework.md 获取详细分析模板
- 说明如何读取和更新 strategy/active.yaml
- 说明如何读取 evolution/*.md
- 提供淘股吧采集的备选方案（browser 工具）

**Step 2: 检查 SKILL.md 长度**

确保 SKILL.md < 500 行，详细内容在 references/ 中。

**Step 3: Commit**

```bash
git add skills/a-share-review-planner/SKILL.md
git commit -m "feat: add SKILL.md for a-share-review-planner"
```

---

## Task 10: 端到端验证

**Step 1: 完整数据采集测试**

```bash
cd skills/a-share-review-planner
python3 scripts/collect_sentiment.py \
  --output-dir /tmp/review_e2e \
  --news-count 10 \
  --taoguba-count 10
```

验证所有 JSON 文件都有内容。

**Step 2: 检查 SKILL.md 可读性**

阅读 SKILL.md，确认一个不了解项目背景的 LLM Agent 能理解并执行所有步骤。

**Step 3: 检查文件完整性**

```bash
find skills/a-share-review-planner -type f | sort
```

确认所有文件都存在。

**Step 4: Final commit**

```bash
git add -A skills/a-share-review-planner/
git commit -m "feat: complete a-share-review-planner skill v1"
```

---

## Task 11: 部署测试（可选）

**Step 1: 拷贝至 Openclaw skills 目录**

```bash
cp -r skills/a-share-review-planner /Users/mindora/clawd/skills/
```

**Step 2: 重启 Openclaw Gateway**

```bash
openclaw gateway restart
```

**Step 3: 在 Openclaw 中触发 Skill**

告诉 Openclaw Agent："帮我做一下今天的A股复盘"，观察 Skill 是否被正确触发和执行。
