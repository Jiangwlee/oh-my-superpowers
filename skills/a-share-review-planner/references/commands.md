# 数据采集命令参考

> 本文档由 SKILL.md 按需加载。仅在需要查阅具体命令参数时读取。

## 采集脚本

```bash
# 完整采集（推荐，含趋势扫描，约 2-3 分钟）
python3 {SKILL_DIR}/scripts/collect_sentiment.py \
  --output-dir /tmp/a-share-review/{DATE} \
  --news-count 20 \
  --taoguba-count 20

# 含账户持仓数据（需已配置 jvQuant，见下方章节）
python3 {SKILL_DIR}/scripts/collect_sentiment.py \
  --output-dir /tmp/a-share-review/{DATE} \
  --news-count 20 \
  --taoguba-count 20 \
  --broker

# 精简采集（测试用，跳过趋势扫描，约 30 秒）
python3 {SKILL_DIR}/scripts/collect_sentiment.py \
  --output-dir /tmp/a-share-review/{DATE} \
  --news-count 5 \
  --taoguba-count 5 \
  --no-scan-trends

# 限制扫描范围（仅前50名，约 40 秒）
python3 {SKILL_DIR}/scripts/collect_sentiment.py \
  --output-dir /tmp/a-share-review/{DATE} \
  --news-count 20 \
  --taoguba-count 20 \
  --popularity-max 50
```

`{DATE}` 替换为当天日期，如 `2026-02-18`。
`{SKILL_DIR}` 替换为本 Skill 所在目录，如 `/Users/mindora/clawd/skills/a-share-review-planner`。

## 报告转图片（推荐，不依赖 browser relay）

```bash
# 生成 PNG（默认，Chrome headless 截全页，自动探测页面高度）
python3 {SKILL_DIR}/scripts/report_to_image.py \
  /tmp/a-share-review/{DATE}/report.md

# 生成 PDF（完整分页，Telegram 原生预览）
python3 {SKILL_DIR}/scripts/report_to_image.py \
  /tmp/a-share-review/{DATE}/report.md \
  --format pdf \
  --output ~/.openclaw/media/a-share-review/{DATE}/report.pdf
```

依赖：系统已安装 Google Chrome（/Applications/Google Chrome.app），无需 pip 安装任何包。

## 报告转 HTML（备用，供 browser 工具截图）

```bash
python3 {SKILL_DIR}/scripts/report_to_html.py \
  /tmp/a-share-review/{DATE}/report.md
```

依赖：`pandoc`（可选，无则自动降级纯文本）。生成后用 Openclaw `browser` 工具打开 `file://` URL。

## 输出文件一览

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
| `taoguba_recommend.json` | 淘股吧今日推荐（含 `content` 正文，用于潜在/新题材挖掘） |
| `taoguba_hot_discussion.json` | 淘股吧热门讨论（`subject/body/quotecontent`，用于潜在/新题材挖掘） |
| `taoguba_hot.json` | 淘股吧精华帖（用于识别已发酵热点题材；方法论提炼） |
| `ths_snapshot.json` | 同花顺涨停快照（原始 JSON，最新交易日） |
| `ths_history.json` | 近5交易日涨停历史（原始 JSON，精简版） |
| `ths_report.md` | 涨停综合报告（**LLM 直接阅读**，含5日趋势表 + 连板天梯 + 板块明细） |
| `trend_scan.json` | 趋势扫描完整结果（含评分/信号/情绪） |
| `trend_report.md` | 趋势股筛选报告（人类可读） |
| `broker_account.json` | 账户资金+持仓+当日委托（仅 --broker 时生成） |
| `candidates.json` | 候选股计划（LLM 生成，供 risk_check.py 校验） |

## 独立风控校验

LLM 完成第3步个股筛选后，将候选股写成 candidates.json，然后执行：

```bash
python3 {SKILL_DIR}/scripts/risk_check.py \
  --input /tmp/a-share-review/{DATE}/candidates.json
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

---

## Deep Research 个股采集

在完成第三步个股初筛后，对每只候选股执行以下命令：

```bash
# 东方财富股吧采集（帖子 + 资讯 + 公告）
python3 {SKILL_DIR}/scripts/collect_eastmoney_guba.py \
  --code {CODE} \
  --output /tmp/a-share-review/{DATE}/dr_{CODE}_em.json \
  --post-limit 36 \
  --detail-limit 5 \
  --notice-days 3

# 淘股吧个股扩展采集（题材标签 + 个股讨论）
python3 {SKILL_DIR}/scripts/collect_taoguba_stock.py \
  --full-code {FULL_CODE} \
  --output /tmp/a-share-review/{DATE}/dr_{CODE}_tgb.json \
  --quotes-count 8 \
  --zh-count 0
```

采集完成后，执行 compact 提取脚本（**不调用 LLM**，约 600 tokens），再由主 LLM 读取 compact 文件生成 brief：

```bash
# compact 提取（规则抽取，不污染上下文）
python3 {SKILL_DIR}/scripts/summarize_stock_brief.py \
  --code {CODE} \
  --em-raw /tmp/a-share-review/{DATE}/dr_{CODE}_em.json \
  --tgb-raw /tmp/a-share-review/{DATE}/dr_{CODE}_tgb.json \
  --output /tmp/a-share-review/{DATE}/dr_{CODE}_compact.json \
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
