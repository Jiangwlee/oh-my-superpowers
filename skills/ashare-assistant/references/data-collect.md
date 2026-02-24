# 阶段1：数据采集

**运行前提**：在执行任何脚本前，先确认日期变量和工作目录：

```bash
DATE=$(date +%Y-%m-%d)
cd <skill_root>   # SKILL.md 所在目录，即 skills/ashare-assistant/
```

> 所有脚本必须从 `<skill_root>` 执行，否则报 `ModuleNotFoundError`。

运行数据采集脚本：

```bash
python3 scripts/collect_sentiment.py \
  --output-dir ~/.ashare-assistant/data/${DATE}/collect \
  --news-count 20 \
  --taoguba-count 20
```

**券商账户数据（jvQuant）自动检测逻辑**：

- 脚本启动时自动检测 `~/.openclaw/jvquant.json` 是否存在：
  - **存在** → 自动采集账户持仓数据，无需任何额外参数
  - **采集失败** → 脚本以非零退出码终止，stderr 输出明确错误；此时**不能继续生成交易计划**，须告知用户修复 jvquant.json 配置
  - **文件不存在** → 打印跳过提示，不报错，但后续将无法生成持仓相关内容

采集完成后必须读取：

1. `~/.ashare-assistant/data/${DATE}/collect/collection_summary.json`
2. `~/.ashare-assistant/data/${DATE}/collect/run_id.json`

要求：

1. 先确认各数据源状态，如有失败需在后续分析中明确标注并继续处理可用数据。
2. 后续全部产物保持同一 `run_id`（报告注释、JSON 顶层、decision_log）。
