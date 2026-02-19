---
name: a-share-review-planner
description: Use when user says "复盘"、"今日回顾"、"明日计划"、"选股" or wants to
  review A-share market and generate trading plan. Works on trading days,
  holidays, and weekends.
---

# A股复盘与交易计划

<IMPORTANT>
在开始任何分析之前，必须遵守以下约束：

- **禁止猜测数据**：某数据源失败时，明确告知用户并跳过，不得用臆测填充
- **策略修改要谨慎**：每次最多调整 active.yaml 中 1-2 个参数，必须写明原因
- **数据时效性**：采集数据为当日快照，不得使用过期数据分析
</IMPORTANT>

## Overview

帮助用户完成每日收盘后的A股复盘：采集多源市场数据 → 分析市场环境与题材线索 → 筛选候选标的 → 制定含入场/止盈/止损/仓位的交易计划 → 微调交易策略。

**核心原则**：LLM 做判断（分析推理、策略调整），代码做执行（数据采集、API调用）。

## When to Use

- 用户说"复盘"、"今日回顾"、"明日计划"、"帮我选股"
- 交易日收盘后（最完整）
- 节假日/周末（市场虽休市，但新热点持续涌现，适合梳理题材线索、预判开盘策略）

## 数据完整性说明

| 场景 | 新闻/舆情 | 板块资金 | 趋势扫描 |
|------|-----------|---------|---------|
| 交易日收盘后 | ✅ 完整 | ✅ 完整 | ✅ 完整 |
| 节假日/周末 | ✅ 有效 | ⚠️ 为最后交易日数据 | ⚠️ 为最后交易日数据 |
| 盘中 | ✅ 有效 | ⚠️ 实时但不完整 | ⚠️ 基于前一日收盘 |

数据有缺失时，在分析中明确标注，不得用臆测填充。

---

## Workflow

完整工作流分为 4 个阶段，**必须按顺序执行，不得跳过**。

### 阶段1：数据采集

运行数据采集脚本，收集所有数据源：

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

> 脚本参数详情及输出文件说明，参见 `references/commands.md`。
> jvQuant 配置说明，参见 `references/commands.md` 中的"jvQuant 配置"章节。

采集完成后读取 `/tmp/a-share-review/{DATE}/collection_summary.json`，确认各数据源状态。如有失败，告知用户并继续分析可用数据。

---

### 阶段2：数据读取

读取以下文件，整理关键信息：

| # | 文件 | 用途 |
|---|------|------|
| 1 | `/tmp/a-share-review/{DATE}/news_headline.json` | A股头条（指数、成交额） |
| 2 | `/tmp/a-share-review/{DATE}/news_daily.json` | 每日财经（政策/宏观） |
| 3 | `/tmp/a-share-review/{DATE}/news_opportunity.json` | 机会情报 |
| 4 | `/tmp/a-share-review/{DATE}/market_sectors.json` | 板块资金摘要 |
| 5 | `/tmp/a-share-review/{DATE}/taoguba_recommend.json` | 淘股吧今日推荐（**实时题材热点** ⭐，题材线索首选） |
| 6 | `/tmp/a-share-review/{DATE}/taoguba_hot.json` | 淘股吧精华帖（方法论/心理/风控，用于精华言论提炼） |
| 7 | `/tmp/a-share-review/{DATE}/ths_snapshot.json` | 涨停快照（最新交易日，连板天梯+最强板块+个股详情） |
| 8 | `/tmp/a-share-review/{DATE}/ths_history.json` | 近5交易日涨停历史（**情绪趋势判断** ⭐，用于多日对比） |
| 9 | `/tmp/a-share-review/{DATE}/trend_scan.json` | 趋势扫描结果 |
| 10 | `/tmp/a-share-review/{DATE}/trend_report.md` | 趋势股报告（人类可读） |
| 11 | `/tmp/a-share-review/{DATE}/broker_account.json` | 账户资金+持仓（**如存在**，用于账户健康度判断） |
| 12 | `{SKILL_DIR}/strategy/active.yaml` | 当前生效策略（含 account_mode 定义） |
| 13 | `{SKILL_DIR}/evolution/feedback.md` | 诊断反馈（有内容则读） |
| 14 | `{SKILL_DIR}/evolution/selection_rules.md` | 选股规则修正（有内容则读） |
| 15 | `{SKILL_DIR}/evolution/known_pitfalls.md` | 已知交易陷阱（有内容则读） |

---

### 阶段3：分析

**必须严格按照 `{SKILL_DIR}/references/analysis-framework.md` 的框架执行**，不得跳过任何步骤或遗漏必答问题：

1. 市场环境判断 → 强弱评级、主线风格、**账户健康度（account_mode）**、最终仓位建议
   - **THS 多日情绪分析**：用 `ths_history.json` 制作近5日涨停数量/板块变化表格，判断市场情绪是升温/冷却/持平；`ths_snapshot.json` 高亮当日连板天梯和热门板块内涨停最多的个股
2. 题材线索识别 → 主线题材、新兴线索、衰退警示、市场情绪
3. 个股筛选 → 趋势股（4星以上）+ 题材股（仅题材驱动市时）
4. **个股 Deep Research（第3.5步）** → 对步骤3筛出的候选股逐一采集股吧情绪与近期事件，生成 brief，输出仓位校准结论（命令详见 `references/commands.md`）
5. 交易计划制定 → 结合步骤4的 DR 校准结论，制定每只候选股的入场/止盈/止损/仓位
6. 风险检查（LLM 定性）→ 集中度、与昨日对比、持仓调整建议、特殊风险
7. 策略回顾与微调 → **提案生成 + 4 维度评分（ProposalJudge）**，评分 ≥ 7 才修改 active.yaml
8. 知识库积累 → 检查是否发现新规律/陷阱，有则追加到 evolution/*.md
9. 精华言论提炼 → 通读 `taoguba_hot.json` 全部帖子正文，提炼 **10 条最有建设性的交易经验**，要求：语言精炼（每条不超过 50 字），不录入选股推荐/板块预测类内容，只取方法论/心理/风控类真知灼见，并标注原作者

**阶段3 完成后，在输出交易计划之前，执行独立风控校验：**

```bash
# 将 LLM 生成的候选股计划输出为 JSON，然后执行硬性规则校验
python3 {SKILL_DIR}/scripts/risk_check.py --input /tmp/a-share-review/{DATE}/candidates.json
```

候选股 JSON 格式（先由 LLM 生成此文件，再执行校验）：
```json
{
  "total_capital": 100000,
  "market_mode": "strong",
  "account_mode": "normal",
  "candidates": [
    {"code": "000001", "name": "平安银行", "type": "trend", "sector": "银行", "position": 15000}
  ]
}
```

如校验有 **error 级别违规**，必须重新调整候选股计划，直至通过才能输出最终报告。warn 级别违规须在报告"风险提示"章节明确标注。

---

### 阶段4：输出交易计划

按以下格式输出完整报告：

```markdown
# A股复盘报告 - {DATE}

## 一、市场环境
- 强弱评级：[强/中/弱]
- 主线风格：[题材驱动/趋势主导/混沌轮动]
- 账户健康度：[growth/normal/defensive/critical/未知]
- 最终仓位建议：[激进/标准/防守/观望]
- 判断依据：...

## 二、题材线索

### 主线题材
- [题材名] | 阶段：[启动/加速/分歧/衰退] | 龙头：[个股]

### 新兴线索
- [题材名] | 催化：[事件] | 评估：[高/中/低]

### 衰退警示
- [题材名] | 信号：[具体信号]

### 市场情绪
[乐观/谨慎/恐慌] - [依据]

## 三、交易计划

### [代码] [名称] [类型：趋势/题材]
- **选股理由**：...
- **趋势评分**：[星级] [总分] | [情绪标签]（趋势股）
- **所属题材**：[题材名] | 阶段：[X]（题材股）
- **入场条件**：...
- **目标仓位**：...
- **止盈条件**：...
- **止损条件**：...
- **持有周期**：...
- **风险点**：...

（共 5-10 只候选股）

## 四、风险提示
- 集中度：[正常/偏高]
- 计划变更：[新增/移除/调整]
- 特殊风险：[如有]

## 五、策略调整
- 当前策略评估：[适用/需微调]
- 调整内容：[无/具体修改]

## 六、精华言论

> 来源：淘股吧精华帖，提炼最有建设性的交易经验。

1. [经验1] —— *[作者]*
2. [经验2] —— *[作者]*
3. [经验3] —— *[作者]*
4. [经验4] —— *[作者]*
5. [经验5] —— *[作者]*
6. [经验6] —— *[作者]*
7. [经验7] —— *[作者]*
8. [经验8] —— *[作者]*
9. [经验9] —— *[作者]*
10. [经验10] —— *[作者]*
```

报告生成后，**立即执行以下命令将报告保存为文件**（不得跳过，不得仅输出到聊天）：

```bash
mkdir -p /tmp/a-share-review/{DATE}
cat > /tmp/a-share-review/{DATE}/report.md << 'EOF'
[在此处粘贴上方完整报告，从"# A股复盘报告"起到"精华言论"结束，不得省略任何章节]
EOF
```

---

### 阶段5：生成 PDF 推送用户

报告文件保存后，执行以下步骤。**这是默认流程，不是可选项。**

**步骤1：生成 PDF**

```bash
mkdir -p ~/.openclaw/media/a-share-review/{DATE}
python3 {SKILL_DIR}/scripts/report_to_image.py \
  /tmp/a-share-review/{DATE}/report.md \
  --format pdf \
  --output ~/.openclaw/media/a-share-review/{DATE}/report.pdf
# 脚本输出路径，例如：
#   完成（pdf，XXkb）：~/.openclaw/media/a-share-review/{DATE}/report.pdf
```

**步骤2：通过 Telegram Bot API 发送 PDF（sendDocument）**

```bash
python3 {SKILL_DIR}/scripts/send_telegram_file.py \
  ~/.openclaw/media/a-share-review/{DATE}/report.pdf \
  --method document \
  --caption "A股复盘报告 {DATE}"
```

> 使用 `sendDocument`，Telegram 原生预览 PDF，可直接翻页阅读。
> 脚本自动从 `~/.openclaw/openclaw.json` 读取 botToken 和 chat_id，无需手动配置。

**Fallback：若发送失败**

直接将 `/tmp/a-share-review/{DATE}/report.md` 的文本内容输出给用户。

---

## Strategy Evolution（策略进化）

- `{SKILL_DIR}/strategy/default.yaml` — 基线策略，**不可修改**，仅作参照
- `{SKILL_DIR}/strategy/active.yaml` — 当前生效策略，每次复盘可微调

**修改门槛（ProposalJudge 机制）**：每次修改前必须对提案进行 4 维度评分，仅当平均分 ≥ 7 且无任何维度 < 4 才写入，否则记录提案但不执行。

```yaml
evolution_log:
  - date: "2026-02-18"
    change: "趋势股止损改为'跌破MA10且量能放大2倍以上'"
    reason: "近期MA20止损太慢，导致利润回吐过多"
    proposal_scores: {relevance: 8, value: 7, safety: 9, feasibility: 8}
```

若 active.yaml 与 default.yaml 偏差过大，需提醒用户审核。

## Knowledge Evolution（知识库进化）

- `{SKILL_DIR}/evolution/known_pitfalls.md` — 已知交易陷阱，**每次复盘第七步自动检查更新**
- `{SKILL_DIR}/evolution/selection_rules.md` — 选股规则修正，**同上**
- `{SKILL_DIR}/evolution/feedback.md` — 交易诊断反馈，由外部交易诊断工具写入
