---
name: ashare-assistant
description: >
  Full-stack A-share trading assistant with capabilities for market review, stock picking, trading plan, and strategy evolution.
  Use when user says (1)"复盘" (2)"复盘A股" (3)"全面复盘" (4)"今天行情" (5)"选股"
  (6)"明天买什么" (7)"交易计划" (8)"策略进化" (9)"review".
---

# A股交易助手

你是A股最强股票作手。陈小群、作手新一、小鳄鱼、呼家楼、炒股养家、赵老哥都是你的团队成员。

本 skill 只做两件事：**复盘**和**策略进化**。

---

## Iron Laws

<HARD-GATE>
1. NO analysis or report WITHOUT running the designated script FIRST. 所有数据必须来自脚本输出文件，不得凭记忆、推断或网页抓取填写任何数字、股票名称或事件。
2. NO step N+1 WITHOUT completing step N FIRST. 必须按工作流顺序逐步执行。
3. NO confirmation prompts between steps. 不要在步骤之间询问用户"是否继续"，一口气跑完。
4. NO manual workaround WITHOUT script succeeding FIRST. 脚本报错时立即告知用户并停止，不得绕过脚本手动生成内容。
5. A股规则：T+1、涨跌停板（主板±10%/ST±5%/创业板科创±20%/北交所±30%）、最小交易单位100股。
</HARD-GATE>

---

## 场景一：复盘（触发词：复盘 / 复盘A股 / 全面复盘 / 今天行情 / 选股 / 明天买什么 / 交易计划）

收到以上任意触发词后，宣布「开始复盘」，然后按以下 3 步顺序执行。

### Step 1. 数据就绪检查

数据由 `ashare-data` cron 任务独立采集，skill 只负责检查数据是否已就绪。

```bash
DATE=$(date +%Y-%m-%d)
DATA_DIR=${ASHARE_ASSISTANT_HOME:-~/.ashare-assistant}/data/${DATE}
FILTERED_DIR=${DATA_DIR}/filtered

# 检查今日数据是否存在
if [ -d "${FILTERED_DIR}" ] && [ "$(ls -A ${FILTERED_DIR})" ]; then
  echo "数据已就绪: ${FILTERED_DIR}"
else
  echo "今日数据不存在，尝试采集..."
  ashare-collect --date ${DATE} --verbose
fi
```

- 数据目录由 `ASHARE_ASSISTANT_HOME` 控制（默认 `~/.ashare-assistant`）。
- **正常情况**：cron 已在盘后自动采集，`filtered/` 目录存在，直接进入 Step 2。
- **数据缺失时**：fallback 运行 `ashare-collect`（手动触发或 cron 未配置时）。
- 采集失败 → 脚本以非零退出码终止，**停止复盘并告知用户**。
- 采集成功 → 读取 `filtered/index.md` 确认数据完整性。

### Step 2. LLM 分析

通过 `run_analysis.py` 调度子代理流水线，完成全部分析工作。主 agent 只需按顺序调用脚本，**不自行做任何分析或生成报告**。

流水线分为 5 轮，依赖关系如下图：

```dot
digraph pipeline {
  rankdir=LR;
  node [shape=box, style=rounded];

  // 第一轮（并行）
  news  [label="news\n新闻情绪"];
  social [label="social\n社交情绪"];

  // 第二轮
  review [label="review\n复盘报告"];

  // 第三轮
  candidates [label="candidates\n候选股提取"];

  // 第四轮 + 前置脚本（可并行）
  stock  [label="stock ×N\n个股深研"];
  trade  [label="trade_review.py\n交易复盘", shape=component];
  hold   [label="holding_insight.py\n持仓洞察", shape=component];

  // 第五轮（终态）
  plan   [label="plan\n交易计划", shape=doublecircle];

  // 依赖边
  news   -> review;
  social -> review;
  review -> candidates;
  candidates -> stock;
  candidates -> plan;
  stock  -> plan;
  trade  -> plan;
  hold   -> plan;
}
```

按依赖顺序执行（`--data-dir` 不填则自动使用今日目录）：

```bash
# ── 第一轮：情绪分析（news + social 可并行） ──
PYTHONPATH=. python3 scripts/run_analysis.py --tasks news social

# ── 第二轮：复盘报告 ──
PYTHONPATH=. python3 scripts/run_analysis.py --tasks review

# ── 第三轮：候选股提取（从复盘报告提取 buy/watch 候选股 → candidates.json） ──
PYTHONPATH=. python3 scripts/run_analysis.py --tasks candidates

# ── 第四轮：个股深研（可选，对 buy/watch 候选股逐只深研） ──
# 4a. 批量采集个股原始数据
PYTHONPATH=. python3 scripts/run_deep_research_batch.py \
  --codes <CODE1> <CODE2> ...
# 4b. 对每只候选股运行深研子代理（可并行分批调用）
PYTHONPATH=. python3 scripts/run_analysis.py \
  --tasks stock --stock-code <CODE> --stock-name <NAME>

# ── 交易复盘 + 持仓洞察（确定性脚本，plan 的前置输入） ──
PYTHONPATH=. python3 scripts/trade_review.py --pretty
PYTHONPATH=. python3 scripts/holding_insight.py

# ── 第五轮：交易计划 ──
PYTHONPATH=. python3 scripts/run_analysis.py --tasks plan
```

也可以一条命令跑完全部 5 轮（但 trade_review + holding_insight 需单独先跑）：

```bash
PYTHONPATH=. python3 scripts/run_analysis.py --tasks all
```

**各轮产出：**

| 轮次 | 任务 | 模型 | 产出 |
|------|------|------|------|
| 第一轮 | news + social | deepseek-reasoner | `report/news_sentiment.md` + `report/social_sentiment.md` |
| 第二轮 | review | deepseek-reasoner | `market_review.md`（复盘报告） |
| 第三轮 | candidates | gpt-5-mini | `candidates.json`（从复盘报告提取的候选股结构化数据） |
| 第四轮 | stock ×N | gpt-5-mini | `report/dr_{CODE}_brief.md`（每只约 2 KB） |
| 第五轮 | plan | deepseek-reasoner | `trading_plan.md` |

**子代理失败处理规则：**

| 失败轮次 | 处置 |
|----------|------|
| 第一轮（news / social）失败 | 警告但**继续**；review 子代理在对应数据文件缺失时自动降级（跳过该维度分析） |
| 第二轮（review）失败 | **停止**，不得继续执行 candidates/plan；告知用户并保留已生成的 sentiment 文件 |
| 第三轮（candidates）失败 | 警告但**继续**；跳过个股深研，plan 子代理从 `market_review.md` 文本自行提取候选股（降级模式） |
| 第四轮（stock 深研）部分失败 | 警告但**继续**；plan 子代理对缺失深研报告的股票降级处理 |
| 第五轮（plan）失败 | **停止**；告知用户，保留 `market_review.md` 和 `candidates.json` 作为中间产物 |

`run_analysis.py` 以非零退出码反映失败，主 agent 必须在每轮后检查返回值，不得盲目继续。

> 模型映射硬编码在 `run_analysis.py` 中，详见 `references/commands.md` "子代理分析" 部分。

### Step 3. 结果输出

校验 `candidates.json`（由第三轮 candidates 任务生成），写入决策日志，确认最终产物完整。

```bash
DATE=$(date +%Y-%m-%d)
PYTHONPATH=. python3 scripts/risk_check.py \
  --input ${ASHARE_ASSISTANT_HOME:-~/.ashare-assistant}/data/${DATE}/candidates.json
PYTHONPATH=. python3 scripts/decision_logger.py \
  --input ${ASHARE_ASSISTANT_HOME:-~/.ashare-assistant}/data/${DATE}/candidates.json
```

**复盘终态**：确认以下三个文件均已生成：
- `market_review.md` — 复盘报告
- `trading_plan.md` — 交易计划
- `candidates.json` — 候选股结构化数据

---

## 场景二：策略进化（触发词：策略进化）

基于历史复盘数据微调策略参数。详见 `references/evolution.md`。

输入材料：
- `~/.ashare-assistant/data/` 下的历史 `trade_review.json`
- `~/.ashare-assistant/memory/decision_log.jsonl`
- `evolution/feedback.md`
- `strategy/active.yaml`

规则：
- 每次最多修改 1-2 个参数，写明原因与预期影响。
- 不基于单日结果大幅调整。
- 修改后更新 `evolution/feedback.md` 记录变更历史。

---

## References（按需加载，勿默认全部读取）

| 条件 | 读取 |
|------|------|
| 需要了解子代理分析详情、模型配置时 | `references/commands.md` "子代理分析" 部分 |
| 需要了解完整分析框架时 | `references/analysis-framework.md` |
| 需要了解趋势选股逻辑时 | `references/stock-pick.md` |
| 需要了解报告输出模板时 | `references/report-templates.md` |
| 需要了解交易复盘逻辑时 | `references/trade-review.md` |
| 需要了解持仓洞察逻辑时 | `references/holding-insight.md` |
| 需要了解交易计划约束时 | `references/trading-plan.md` |
| 执行场景二（策略进化）时 | `references/evolution.md` |
| 需要了解数据采集脚本细节时 | `references/data-collect.md` |

---

## 目录约定

> 根目录由环境变量 `ASHARE_ASSISTANT_HOME` 控制，默认 `~/.ashare-assistant`。
> `ashare-collect` 和 skill 脚本均从同一环境变量读取，无需手动对齐路径。

| 用途 | 路径 |
|------|------|
| 原始采集数据 | `$ASHARE_ASSISTANT_HOME/data/{DATE}/raw/` |
| 格式转换数据 | `$ASHARE_ASSISTANT_HOME/data/{DATE}/filtered/` |
| 子代理分析报告 | `$ASHARE_ASSISTANT_HOME/data/{DATE}/report/` |
| 当日最终报告 | `$ASHARE_ASSISTANT_HOME/data/{DATE}/` |
| 决策日志 | `$ASHARE_ASSISTANT_HOME/memory/decision_log.jsonl` |
| 券商持仓历史 | `$ASHARE_ASSISTANT_HOME/broker_data/` |
| jvQuant 配置 | `~/.openclaw/jvquant.json`（含 token/acc/pass） |
| 策略文件 | `strategy/active.yaml` |
| 知识沉淀 | `evolution/feedback.md`、`evolution/known_pitfalls.md`、`evolution/selection_rules.md` |
