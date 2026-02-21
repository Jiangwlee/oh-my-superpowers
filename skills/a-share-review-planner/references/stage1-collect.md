# 阶段1：数据采集

**运行前提**：在执行任何脚本前，先确认变量：

```bash
# 确认 SKILL_DIR（替换为本 skill 实际路径）
SKILL_DIR=~/clawd/skills/a-share-review-planner
DATE=$(date +%Y-%m-%d)
```

若脚本报错或参数不确定，先查帮助，不要读取脚本源码：

```bash
python3 $SKILL_DIR/scripts/collect_sentiment.py --help
```

运行数据采集脚本，收集所有数据源。

```bash
# 标准采集（不含账户数据）
python3 {SKILL_DIR}/scripts/collect_sentiment.py \
  --output-dir /tmp/a-share-review/{DATE} \
  --news-count 20 \
  --taoguba-count 20

# 含账户持仓数据（需已配置 ~/.openclaw/jvquant.json）
python3 {SKILL_DIR}/scripts/collect_sentiment.py \
  --output-dir /tmp/a-share-review/{DATE} \
  --news-count 20 \
  --taoguba-count 20 \
  --broker
```

脚本参数详情及输出文件说明参见 `references/commands.md`。
jvQuant 配置说明参见 `references/commands.md` 中的“jvQuant 配置”章节。

采集完成后必须读取：

1. `/tmp/a-share-review/{DATE}/collection_summary.json`
2. `/tmp/a-share-review/{DATE}/run_id.json`

要求：

1. 先确认各数据源状态，如有失败需在后续分析中明确标注并继续处理可用数据。
2. 后续全部产物保持同一 `run_id`（报告注释、JSON 顶层、decision_log）。
