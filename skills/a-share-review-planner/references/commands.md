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
  --format pdf
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
| `taoguba_hot.json` | 淘股吧精华帖（含正文摘要，最重要的舆情源） |
| `ths_snapshot.json` | 同花顺涨停快照（连板天梯 + 最强板块） |
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
