# 数据采集命令参考

> 本文档由 SKILL.md 按需加载。仅在需要查阅具体命令参数时读取。

## 采集脚本

```bash
# 完整采集（推荐，含趋势扫描，约 2-3 分钟）
python3 {SKILL_DIR}/scripts/collect_sentiment.py \
  --output-dir /tmp/a-share-review/{DATE} \
  --news-count 20 \
  --taoguba-count 20

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
