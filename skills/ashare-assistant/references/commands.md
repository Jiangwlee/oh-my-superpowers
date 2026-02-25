# 数据采集命令参考

> 本文档按需加载。仅在需要查阅具体命令参数、脚本选项或配置说明时读取。

## 目录

- [采集脚本](#采集脚本) — collect_sentiment.py 完整参数
- [格式转换](#格式转换) — filter_to_markdown.py（raw/ → filtered/）
- [子代理分析](#子代理分析) — run_analysis.py（filtered/ → report/）
- [输出文件一览](#输出文件一览) — 所有采集产物说明
- [独立风控校验](#独立风控校验) — risk_check.py 用法与 candidates.json 格式
- [结构化输出校验与决策日志](#结构化输出校验与决策日志) — validate + decision_logger + diagnose
- [交易执行复盘](#交易执行复盘) — trade_review.py 用法与输出
- [持仓洞察](#持仓洞察) — holding_insight.py 用法与输出
- [Deep Research 个股采集](#deep-research-个股采集) — 批量并行命令、预算参数、输出文件
- [jvQuant 配置](#jvquant-配置) — 配置文件、环境变量、费用说明

---

## 采集脚本

```bash
# 完整采集（推荐，含趋势扫描，约 2-3 分钟）
python3 scripts/collect_sentiment.py \
  --output-dir ~/.ashare-assistant/data/{DATE}/raw \
  --news-count 20 \
  --taoguba-count 20

# 含账户持仓数据（需已配置 jvQuant，见下方章节）
python3 scripts/collect_sentiment.py \
  --output-dir ~/.ashare-assistant/data/{DATE}/raw \
  --news-count 20 \
  --taoguba-count 20 \
  --broker

# 精简采集（测试用，跳过趋势扫描，约 30 秒）
python3 scripts/collect_sentiment.py \
  --output-dir ~/.ashare-assistant/data/{DATE}/raw \
  --news-count 5 \
  --taoguba-count 5 \
  --no-scan-trends

# 限制扫描范围（仅前50名，约 40 秒）
python3 scripts/collect_sentiment.py \
  --output-dir ~/.ashare-assistant/data/{DATE}/raw \
  --news-count 20 \
  --taoguba-count 20 \
  --popularity-max 50
```

`{DATE}` 替换为当天日期，如 `2026-02-18`（`$(date +%Y-%m-%d)`）。
若不确定路径，可在 `references/data-collect.md` 的变量声明中确认。

## 格式转换

将 raw/ JSON 数据转换为 filtered/ Markdown 文件（纯规则转换，不调用 LLM）：

```bash
python3 scripts/filter_to_markdown.py \
  --input-dir ~/.ashare-assistant/data/{DATE}/raw \
  --output-dir ~/.ashare-assistant/data/{DATE}/filtered
```

生成 `filtered/index.md` 索引文件，标注每个文件的读取方式（direct/subagent）。

## 子代理分析

对 filtered/ 中的大文件运行子代理语义压缩，以及生成复盘报告和交易计划。

完整流水线：news → social → review → plan（4 + N 轮子代理）。

### 内置模型映射

| 任务 | 模型 | 说明 |
|------|------|------|
| news | `anthropic/claude-opus-4-20250514` | 新闻情绪分析（高质量） |
| social | `anthropic/claude-opus-4-20250514` | 社交情绪分析（高质量） |
| review | `anthropic/claude-opus-4-20250514` | 复盘报告生成（高质量） |
| plan | `anthropic/claude-opus-4-20250514` | 交易计划生成（高质量） |
| stock | `github-copilot/gpt-5-mini` | 个股深研（快速、低成本） |

`--model` 参数可覆盖所有任务的模型，但不建议用于生产环境。

### 常用命令

```bash
# 运行完整流水线（news + social + review + plan）
python3 scripts/run_analysis.py \
  --data-dir ~/.ashare-assistant/data/{DATE} \
  --tasks all

# 仅运行情绪分析（第一轮）
python3 scripts/run_analysis.py \
  --data-dir ~/.ashare-assistant/data/{DATE} \
  --tasks news social

# 仅运行复盘报告（需 news/social 已完成）
python3 scripts/run_analysis.py \
  --data-dir ~/.ashare-assistant/data/{DATE} \
  --tasks review

# 仅运行交易计划（需 review 已完成）
python3 scripts/run_analysis.py \
  --data-dir ~/.ashare-assistant/data/{DATE} \
  --tasks plan

# 运行个股深研子代理（使用 gpt-5-mini）
python3 scripts/run_analysis.py \
  --data-dir ~/.ashare-assistant/data/{DATE} \
  --tasks stock \
  --stock-code 002050 --stock-name 三花智控

# 覆盖模型（调试用）
python3 scripts/run_analysis.py \
  --data-dir ~/.ashare-assistant/data/{DATE} \
  --tasks social \
  --model anthropic/claude-sonnet-4-20250514
```

### 任务依赖关系

```
news ──┐
       ├──→ review ──→ plan
social ┘        ↑
              stock ×N（并行，输出 dr_*_brief.md 供 plan 读取）
```

- `review` 依赖 `report/news_sentiment.md` + `report/social_sentiment.md`
- `plan` 依赖 `market_review.md`（+ 可选的 `report/dr_*_brief.md`）
- `stock` 独立运行，但输出供 `plan` 使用

### 输出文件

| 任务 | 输出路径 | 说明 |
|------|---------|------|
| news | `report/news_sentiment.md` | 新闻情绪分析摘要 |
| social | `report/social_sentiment.md` | 社交情绪分析摘要 |
| review | `market_review.md` | 复盘报告（根目录） |
| plan | `trading_plan.md` + `candidates.json` | 交易计划 + 候选股 JSON |
| stock | `report/dr_{CODE}_brief.md` | 个股深研报告 |

## 输出文件一览

### raw/ — 采集脚本输出

| 文件 | 说明 |
|------|------|
| `collection_summary.json` | 采集结果汇总（必查，确认各源状态） |
| `trade_date.json` | 最近交易日期 |
| `news_headline.json` | A股头条（含指数涨跌、成交额等宏观信息） |
| `news_realtime.json` | 市况直击 |
| `news_opportunity.json` | 机会情报 |
| `news_daily.json` | 每日财经（政策/宏观） |
| `news_flash.json` | 7x24快讯 |
| `market_sectors.json` | 板块资金摘要（净流入前5+后5板块） |
| `funding.json` | 资金面摘要（北向净流入 + 主力净流入Top20） |
| `taoguba_recommend.json` | 淘股吧今日推荐（含 `content` 正文） |
| `taoguba_hot_discussion.json` | 淘股吧热门讨论（`subject/body/quotecontent`） |
| `taoguba_hot.json` | 淘股吧精华帖 |
| `ths_snapshot.json` | 同花顺涨停快照（原始 JSON） |
| `ths_history.json` | 近5交易日涨停历史 |
| `ths_report.md` | 涨停综合报告 |
| `trend_scan.json` | 趋势扫描完整结果 |
| `trend_report.md` | 趋势股筛选报告 |
| `us_market.json` | 美股行情 |
| `broker_account.json` | 账户资金+持仓+当日委托（仅 --broker 时生成） |
| `run_id.json` | 本次运行标识（run_id + strategy_version） |

### filtered/ — 格式转换输出

| 文件 | 读取方式 | 说明 |
|------|---------|------|
| `index.md` | — | 文件索引 |
| `market_sectors.md` | direct | 板块资金 Markdown |
| `funding.md` | direct | 资金面 Markdown |
| `us_market.md` | direct | 美股行情 Markdown |
| `news_flash.md` | direct | 7x24快讯 Markdown |
| `ths_report.md` | direct | 涨停综合报告 |
| `trend_report.md` | direct | 趋势股报告 |
| `news_headline.md` | subagent | A股头条 Markdown（大文件） |
| `news_daily.md` | subagent | 每日财经 Markdown（大文件） |
| `news_opportunity.md` | subagent | 机会情报 Markdown（大文件） |
| `news_realtime.md` | subagent | 市况直击 Markdown（大文件） |
| `taoguba_hot.md` | subagent | 精华帖 Markdown（大文件） |
| `taoguba_recommend.md` | subagent | 今日推荐 Markdown（大文件） |
| `taoguba_hot_discussion.md` | subagent | 热门讨论 Markdown |

### report/ — 子代理分析输出

| 文件 | 说明 |
|------|------|
| `index.md` | 报告索引 |
| `news_sentiment.md` | 新闻情绪分析摘要（~3-5 KB） |
| `social_sentiment.md` | 社交情绪分析摘要（~3-5 KB） |
| `dr_{CODE}_brief.md` | 个股深研报告（第3.5步生成，~2 KB/只） |

### 根目录 — 最终产物

| 文件 | 说明 |
|------|------|
| `candidates.json` | 候选股计划（LLM 生成，供 risk_check.py 校验） |
| `market_review.md` | 复盘报告（最终产物） |
| `trading_plan.md` | 交易计划（最终产物） |
| `trade_review.json` | 交易执行复盘结果 |

## 独立风控校验

LLM 完成第3步个股筛选后，将候选股写成 candidates.json，然后执行：

```bash
python3 scripts/risk_check.py \
  --input ~/.ashare-assistant/data/{DATE}/candidates.json
```

candidates.json 格式：
```json
{
  "total_capital": 100000,
  "market_mode": "strong",
  "account_mode": "normal",
  "candidates": [
    {
      "code": "000001",
      "name": "平安银行",
      "type": "trend",
      "sector": "银行",
      "position": 15000
    }
  ]
}
```

字段说明：

- `total_capital`：总可用资金（元），来自 broker_account.json 中的 usable，无账户数据时由用户提供
- `market_mode`：第一步市场环境判断结论（strong/neutral/weak）
- `account_mode`：第一步账户健康度判断结论（growth/normal/defensive/critical）
- `type`：trend（趋势股）/ theme（题材股）
- `sector`：所属板块或题材名称（用于集中度检查）
- `position`：计划仓位金额（元）

## 结构化输出校验与决策日志

```bash
# 1) 校验 candidates.json 核心结构
python3 scripts/validate_output.py \
  --input ~/.ashare-assistant/data/{DATE}/candidates.json

# 2) 风控通过 + 结构通过后，写入 decision_log
python3 scripts/decision_logger.py \
  --input ~/.ashare-assistant/data/{DATE}/candidates.json \
  --log-file ~/.ashare-assistant/memory/decision_log.jsonl

# 3) 独立诊断（T+1/T+5，当前实现 T+1）
python3 scripts/diagnose.py \
  --log-file ~/.ashare-assistant/memory/decision_log.jsonl \
  --feedback-file evolution/feedback.md
```

失败语义：

- `validate_output.py` 非0退出：结构不合法，继续出报告但不写 decision_log
- `decision_logger.py` 非0退出：日志写入失败，主流程继续并在风险提示中标注

---

## 交易执行复盘

阶段5 独立脚本，对比交易计划 vs 实际执行，检测六大类交易瑕疵。

```bash
# 标准用法（阶段4完成后执行）
python3 scripts/trade_review.py \
  --decision-log ~/.ashare-assistant/memory/decision_log.jsonl \
  --strategy strategy/active.yaml \
  --output ~/.ashare-assistant/data/{DATE}/trade_review.json \
  --pretty

# 独立执行（用户直接要求交易复盘，不依赖阶段1-4）
python3 scripts/trade_review.py \
  --output ~/.ashare-assistant/data/{DATE}/trade_review.json \
  --pretty
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--decision-log` | `~/.ashare-assistant/memory/decision_log.jsonl` | 交易计划日志路径 |
| `--strategy` | `strategy/active.yaml` | 策略配置文件路径 |
| `--output` | `trade_review.json` | 复盘结果输出路径 |
| `--pretty` | off | 终端打印格式化 JSON |

### 数据来源

脚本自动获取以下数据（无需手动准备）：

| 数据 | 来源 | 费用 |
|------|------|------|
| 当日持仓 + 委托 | jvQuant broker_account（复用 ticket 缓存） | 首次登录 0.5 元 |
| 历史持仓/委托 | `~/.openclaw/broker_data/` 本地快照 | 免费 |
| 分钟K线（择时分析） | JRJ 免费 API | 免费 |
| 日K线（持仓管理） | JRJ 免费 API | 免费 |
| 交易计划 | `~/.ashare-assistant/memory/decision_log.jsonl` | 免费 |
| 策略限制 | `strategy/active.yaml` | 免费 |

### 输出文件

| 文件 | 说明 |
|------|------|
| `trade_review.json` | 结构化复盘结果（六类瑕疵 + 择时评分 + 仓位检查） |
| `evolution/feedback.md` | 追加当日复盘摘要（瑕疵统计 + 关键问题） |

### 瑕疵类别与严重程度

六类瑕疵：`unplanned_trade`、`missed_execution`、`timing_flaw`、`position_flaw`、`holding_flaw`、`discipline_flaw`

三级严重程度：`error`（必须标注）、`warning`（需说明）、`info`（参考）

详见 `references/trade-review.md`。

---

## 持仓洞察

阶段6 独立脚本，对每只持仓运行瀑布式规则引擎，输出加仓/持有/卖出建议（含具体价格和数量）。

```bash
# 标准用法（独立执行）
python3 scripts/holding_insight.py \
  --strategy strategy/active.yaml \
  --regime neutral \
  --output ~/.ashare-assistant/data/{DATE}/holding_insight.json

# 输出可读文本摘要
python3 scripts/holding_insight.py \
  --strategy strategy/active.yaml \
  --regime neutral \
  --text
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--strategy` | `strategy/active.yaml` | 策略配置文件路径 |
| `--regime` | `neutral` | 市场状态（strong / neutral / weak） |
| `--output` | 无 | 输出 JSON 路径，不指定则输出到 stdout |
| `--text` | off | 输出可读文本而非 JSON |

### 数据来源

| 数据 | 来源 | 费用 |
|------|------|------|
| 当日持仓 + 资金 | jvQuant broker_account（复用 ticket 缓存） | 首次登录 0.5 元 |
| 历史持仓 | `~/.openclaw/broker_data/` 本地快照 | 免费 |
| 日K线（趋势分析） | JRJ 免费 API | 免费 |
| 趋势评分 | analyze_trend() + apply_scoring() | 免费 |
| 资金面 | fetch_funding_for_codes()（缓存） | 免费 |
| 策略限制 | `strategy/active.yaml` | 免费 |

### 决策规则链（瀑布式，命中即停）

| Level | 名称 | 触发条件 | 动作 |
|-------|------|---------|------|
| 0 | 账户模式 | critical + 趋势破 → 清仓；defensive → 禁加仓 | sell / hold |
| 1 | 硬止损 | MA20跌破>=3日 → 卖；亏损>=15% + 趋势破 → 卖 | sell |
| 2 | 止盈 | MA5偏离>=20% → 卖50%；>=15% → 卖30%；2星+趋势破 → 卖 | sell |
| 3 | 技术弱化 | 趋势破+持仓>5日+2星 → 卖；MA20跌破1-2日 → 观察 | sell / hold |
| 4 | 加仓 | 8项前提全满足 + 4星 + 趋势完好 → 加仓 | add |
| 5 | 默认 | 以上均未命中 | hold |

### 加仓前提条件（Level 4，全部必须满足）

1. account_mode = normal 或 growth
2. 单股仓位 < 策略上限（默认20%）
3. 总仓位 < 市场状态上限
4. 可用资金充足（>=100股买入金额）
5. 当前持仓不亏损（pnl >= 0）
6. 当前浮盈 < 20%（锁利优先）
7. defense_safe_ratio >= 0.7（防守能力充足）
8. emotion_level >= 3（情绪不弱）

### 输出文件

| 文件 | 说明 |
|------|------|
| `holding_insight.json` | 结构化决策结果（每股一条决策记录） |

### 输出结构

```json
{
  "review_date": "2026-02-24",
  "account_snapshot": {
    "total_assets": 100000,
    "usable_cash": 30000,
    "account_mode": "normal",
    "total_position_pct": 70.0,
    "market_regime": "neutral",
    "position_count": 5
  },
  "decisions": [
    {
      "code": "000001",
      "name": "平安银行",
      "action": "sell",
      "urgency": "immediate",
      "target_price": 12.50,
      "target_qty": 500,
      "price_type": "market",
      "sell_pct": 1.0,
      "reasons": ["MA20止损: 连续3日跌破MA20未收回"],
      "risk_level": "high",
      "rule_level": 1,
      "star_rating": 2,
      "position_pct": 15.0,
      "pnl_pct": -8.5
    }
  ],
  "summary": {
    "sell_count": 1,
    "hold_count": 3,
    "add_count": 1,
    "high_risk_count": 1
  }
}
```

---

## Deep Research 个股采集

推荐先使用批量并行命令（Phase A 性能优化）：

```bash
python3 scripts/run_deep_research_batch.py \
  --candidates-file ~/.ashare-assistant/data/{DATE}/candidates.json \
  --output-dir ~/.ashare-assistant/data/{DATE} \
  --max-workers 4 \
  --per-stock-timeout-sec 180 \
  --total-timeout-sec 900
```

批量脚本会自动执行：
1. `collect_eastmoney_guba.py`
2. `collect_taoguba_stock.py`
3. `summarize_stock_brief.py --compact-only`

并在 `~/.ashare-assistant/data/{DATE}/dr_timing.json` 输出单票耗时与状态（ok/error/timeout）。

---

在完成第三步个股初筛后，对每只候选股执行以下命令：

```bash
# 东方财富股吧采集（帖子 + 资讯 + 公告）
python3 scripts/collect_eastmoney_guba.py \
  --code {CODE} \
  --output ~/.ashare-assistant/data/{DATE}/dr_{CODE}_em.json \
  --post-limit 36 \
  --detail-limit 5 \
  --notice-days 3

# 淘股吧个股扩展采集（题材标签 + 个股讨论）
python3 scripts/collect_taoguba_stock.py \
  --full-code {FULL_CODE} \
  --output ~/.ashare-assistant/data/{DATE}/dr_{CODE}_tgb.json \
  --quotes-count 8 \
  --zh-count 0
```

采集完成后，执行 compact 提取脚本（**不调用 LLM**，约 600 tokens），再由主 LLM 读取 compact 文件生成 brief：

```bash
# compact 提取（规则抽取，不污染上下文）
python3 scripts/summarize_stock_brief.py \
  --code {CODE} \
  --em-raw ~/.ashare-assistant/data/{DATE}/dr_{CODE}_em.json \
  --tgb-raw ~/.ashare-assistant/data/{DATE}/dr_{CODE}_tgb.json \
  --output ~/.ashare-assistant/data/{DATE}/dr_{CODE}_compact.json \
  --compact-only
```

主 LLM 读取 `dr_{CODE}_compact.json` 后，按 `references/analysis-framework.md` 第3.5步生成 brief，并将 brief JSON 写入 `dr_{CODE}_brief.json`。

`{CODE}` = 6位股票代码（如 `002050`）
`{FULL_CODE}` = 带市场前缀的代码（如 `sz002050`，深市用 `sz`，沪市用 `sh`）

### Deep Research 预算参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 候选股上限 | **8 只** | 超出按技术评分高的优先执行 |
| compact token 预算 | ~600 tokens | 规则提取，脚本自动控制 |
| 每股 brief token 预算 | ~300 tokens | 主 LLM 生成，固定 schema |
| 全部候选股 brief 总预算 | ~2400 tokens | 8只 × 300 tokens |
| 帖子正文 detail-limit | 5 | collect_eastmoney_guba.py 默认值 |
| 淘股吧讨论 quotes-count | 8 | collect_taoguba_stock.py 默认值 |
| 公告过滤天数 notice-days | 3 | 只取近3天公告 |
| zh-count（综合推荐） | 0 | 默认关闭，市场级热帖对个股分析价值有限 |

### Deep Research 输出文件

| 文件 | 说明 |
|------|------|
| `dr_{CODE}_em.json` | 东方财富股吧原始数据（帖子/资讯/公告），追溯用，勿直接传给 LLM |
| `dr_{CODE}_tgb.json` | 淘股吧原始数据（题材标签/个股讨论），追溯用，勿直接传给 LLM |
| `dr_{CODE}_compact.json` | 规则提取的精简数据，约 600 tokens，主 LLM 读取此文件 |
| `dr_{CODE}_brief.json` | 主 LLM 生成的结构化 brief，约 300 tokens，供分析使用 |

### Deep Research 结果追踪

每次复盘完成后，若 deep research 影响了 `position_multiplier` 调整，在 `evolution/feedback.md` 中追加记录：

```markdown
## {DATE} DR 校准记录
- 股票：{CODE} {NAME}
- 关键信号：[触发调整的证据，tier A/B 优先]
- 仓位调整：×1.0 → ×0.8（轻减）
- 后续验证：[待填写，3日后]
```

---

## jvQuant 配置

### 配置文件（推荐）

创建 `~/.openclaw/jvquant.json`：

```json
{
  "counter": "http://xxx.xxx.xxx.xxx:xxxx",
  "token": "你的jvquant用户token",
  "acc": "资金账号",
  "pass": "资金密码"
}
```

### 环境变量（可覆盖配置文件）

```bash
export JVQUANT_COUNTER="http://xxx.xxx.xxx.xxx:xxxx"
export JVQUANT_TOKEN="你的jvquant用户token"
export JVQUANT_ACC="资金账号"
export JVQUANT_PASS="资金密码"
```

### 费用说明

- **登录（/login）有计费**：每次登录会产生费用，计费周期为 1 分钟聚合
- **ticket 缓存机制**：broker_account.py 将 ticket 缓存到 `~/.openclaw/.jvquant_ticket_cache.json`，在 ticket 有效期内（通常 3600 秒）复用，不重新登录
- `broker_account.json` 中的 `ticket_reused` 字段显示本次是否复用了缓存（true = 未产生登录计费）
- **建议**：每个交易日只在收盘后复盘时运行一次 `--broker`，充分利用缓存
