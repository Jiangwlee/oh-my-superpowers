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

## 报告转图片（手机/Telegram）

```bash
# 首次使用安装浏览器（只需一次）
uv run playwright install chromium

# 默认宽度 750px（Telegram 手机推荐）
uv run {SKILL_DIR}/scripts/report_to_image.py \
  /tmp/a-share-review/{DATE}/report.md \
  /tmp/a-share-review/{DATE}/report.png

# 平板/PC 宽度
uv run {SKILL_DIR}/scripts/report_to_image.py \
  /tmp/a-share-review/{DATE}/report.md \
  /tmp/a-share-review/{DATE}/report.png \
  --width 1080
```

依赖：`pandoc`（已有）+ `uv`（已有）+ `playwright`（由 uv 自动安装）。

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
