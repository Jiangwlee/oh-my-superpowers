# 阶段1：数据采集与预处理

**运行前提**：在执行任何脚本前，先确认日期变量和工作目录：

```bash
DATE=$(date +%Y-%m-%d)
cd <skill_root>   # SKILL.md 所在目录，即 skills/ashare-assistant/
```

> 所有脚本必须从 `<skill_root>` 执行，否则报 `ModuleNotFoundError`。

## 步骤 1：数据采集（raw/）

运行数据采集脚本，输出到 `raw/` 子目录：

```bash
python3 scripts/collect_sentiment.py \
  --output-dir ~/.ashare-assistant/data/${DATE}/raw \
  --news-count 20 \
  --taoguba-count 20
```

**券商账户数据（jvQuant）自动检测逻辑**：

- 脚本启动时自动检测 `~/.openclaw/jvquant.json` 是否存在：
  - **存在** → 自动采集账户持仓数据，无需任何额外参数
  - **采集失败** → 脚本以非零退出码终止，stderr 输出明确错误；此时**不能继续生成交易计划**，须告知用户修复 jvquant.json 配置
  - **文件不存在** → 打印跳过提示，不报错，但后续将无法生成持仓相关内容

## 步骤 2：格式转换（raw/ → filtered/）

将 JSON 数据转换为 Markdown 格式：

```bash
python3 scripts/filter_to_markdown.py \
  --input-dir ~/.ashare-assistant/data/${DATE}/raw \
  --output-dir ~/.ashare-assistant/data/${DATE}/filtered
```

> 纯规则转换，不调用 LLM。生成 `filtered/index.md` 索引文件。

## 步骤 3：子代理分析（filtered/ → report/）

对大文件运行子代理语义压缩：

```bash
python3 scripts/run_analysis.py \
  --data-dir ~/.ashare-assistant/data/${DATE} \
  --tasks all
```

> 使用 OpenCode CLI 作为子代理，分别运行新闻情绪分析和社交情绪分析。
> 生成 `report/index.md` 索引文件。

## 验证

采集和预处理完成后，读取索引文件确认数据完整性：

1. `~/.ashare-assistant/data/${DATE}/filtered/index.md` — 确认 filtered 层文件齐全
2. `~/.ashare-assistant/data/${DATE}/report/index.md` — 确认子代理报告已生成
3. `~/.ashare-assistant/data/${DATE}/raw/run_id.json` — 获取 `run_id`

要求：

1. 先确认各数据源状态，如有失败需在后续分析中明确标注并继续处理可用数据。
2. 后续全部产物保持同一 `run_id`（报告注释、JSON 顶层、decision_log）。

## 目录结构

```
~/.ashare-assistant/data/{DATE}/
├── raw/                    ← 步骤1: 采集脚本输出的原始 JSON
│   ├── news_headline.json
│   ├── taoguba_hot.json
│   ├── trend_scan.json
│   ├── run_id.json
│   └── ...
├── filtered/               ← 步骤2: 格式转换后的 Markdown
│   ├── index.md            ← 索引（标注 direct/subagent）
│   ├── market_sectors.md   ← direct: 主 agent 直读
│   ├── news_headline.md    ← subagent: 交给子代理
│   └── ...
├── report/                 ← 步骤3: 子代理分析报告
│   ├── index.md
│   ├── news_sentiment.md   ← 新闻情绪压缩摘要
│   ├── social_sentiment.md ← 社交情绪压缩摘要
│   └── dr_{CODE}_brief.md  ← 个股深研（第3.5步生成）
├── market_review.md        ← 最终复盘报告
└── trading_plan.md         ← 最终交易计划
```
