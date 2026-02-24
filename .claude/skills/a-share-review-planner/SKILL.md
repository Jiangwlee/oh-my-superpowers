---
name: a-share-review-planner
description: >
  A-share daily market review and next-day trading plan. 
  Use when: (1) user says "复盘"、"今日回顾"、"明日计划"、"选股"、"帮我看看大盘"、
  "今天行情"、"大盘分析"、"明天买什么"、"帮我分析行情", (2) user wants A-share market
  analysis or trading plan, (3) user says "板块"、"涨停"、"题材"、"选股",
  (4) user says "交易复盘"、"检查执行"、"review"、"今天交易怎么样"、"执行回顾",
  (5) user says "持仓建议"、"持仓分析"、"加减仓"、"holding insight"、"我的持仓怎么样"、
  "该买还是该卖"、"持仓洞察".
  Works on trading days, holidays, and weekends.
---

# A股复盘与交易计划

## Prerequisite check (required)

**STOP and resolve before proceeding:**

1. **Python 3.10+**: `python3 --version`
2. **Dependencies**: `python3 -c "import requests, bs4, yaml"` -> If missing, run `pip install -r requirements.txt`

<HARD-GATE>
NO ANALYSIS WITHOUT RUNNING collect_sentiment.py FIRST.
NO TRADING PLAN WITHOUT COMPLETING STAGES 1–3 FIRST.
NO REPORT WITHOUT PASSING risk_check.py FIRST.
NO COMPLETION WITHOUT WRITING /tmp/a-share-review/{DATE}/report.md FIRST.

Violating the letter of this rule is violating the spirit of this rule.
No exceptions. Not even when the user asks for a quick summary.
</HARD-GATE>

## 核心约束

- **禁止猜测数据**：某数据源失败时，明确告知并跳过，不得用臆测填充
- **策略修改要谨慎**：每次最多调整 active.yaml 中 1-2 个参数，必须写明原因
- **数据时效性**：采集数据为当日快照，不得使用过期数据分析
- **严禁跳过阶段**：不得在未执行阶段1采集时直接分析，也不得在未完成阶段4时结束任务

## 常见借口——一律拒绝

| LLM 可能说的 | 实际情况 |
|-------------|---------|
| "用户只是想快速了解，不需要完整采集" | 没有真实数据就没有真实分析，臆测比无结果更危险 |
| "数据昨天已经采集过了" | 行情每日变化，过期数据会产生错误判断 |
| "Deep Research 比较慢，可以跳过" | 个股深度分析是仓位校准的前提，跳过会导致入场价格失准 |
| "risk_check 只是 warn，不是 error" | warn 级必须在报告"风险提示"章节显式说明，不可静默忽略 |

## Overview

目标：完成每日收盘后的A股复盘与次日交易计划，并可选执行交易复盘（对比计划 vs 实际执行）。
流程：采集多源数据 → 分析市场与题材 → 生成候选与计划 → 落盘与结构化校验 → 交易执行复盘。
原则：LLM负责判断，脚本负责执行。

**终态**：`/tmp/a-share-review/{DATE}/report.md` 与 `candidates.json` 已落盘，
`decision_log` 已写入（校验通过时）。
若执行了交易复盘，`trade_review.json` 已落盘。
若执行了持仓洞察，`holding_insight.json` 已落盘。
最终回复基于已落盘的 `report.md` 内容进行总结，需明确说明关键结论与风险提示。

## 关键决策分支

在执行过程中，遇到以下情况须按指定路径处理：

```
阶段1完成
  └─ 若 collection_summary 有失败源 → 标注失败源，继续处理可用数据，不中止

阶段2完成
  └─ 若 account_mode = critical → 阶段3仅做市场分析，跳过交易计划，直接进阶段4

阶段3完成
  ├─ 若 risk_check 有 error 级违规 → 必须修改候选并重跑，不得继续
  └─ 若 validate_output.py 失败 → run_failed=true，继续输出人类可读报告，不写 decision_log
```

## Workflow

完整工作流共 5 个阶段。阶段 1-4 必须按顺序执行；阶段 5 和阶段 6 可独立触发。

### 阶段1：数据采集

按 `references/stage1-collect.md` 执行。

### 阶段2：数据读取

按 `references/stage2-read.md` 执行。

### 阶段3：分析与校验

按 `references/stage3-analysis.md` 执行。
详细分析框架按需见 `references/analysis-framework.md`。

### 阶段4：输出交易计划

按 `references/stage4-output.md` 执行。

### 阶段5：交易执行复盘（可独立触发）

按 `references/stage5-trade-review.md` 执行。

**触发条件**（满足任一即执行）：
- 用户在阶段 4 完成后主动要求
- 用户直接说"交易复盘"/"检查执行"/"review"/"今天交易怎么样"
- 当日有 broker 数据（`--broker` 采集过或 jvQuant 配置可用）

**跳过条件**：
- 无 jvQuant 配置且用户未要求 → 跳过并告知
- 非交易日且无历史持仓 → 跳过

### 阶段6：持仓洞察（可独立触发）

按 `references/commands.md` 中"持仓洞察"章节执行。

对每只持仓运行规则引擎决策，输出 **加仓/持有/卖出** 建议，附带具体价格和数量。
决策基于瀑布式规则链（Level 0-5），纯规则驱动，不依赖 LLM 判断。

**触发条件**（满足任一即执行）：
- 用户说"持仓建议"/"持仓分析"/"加减仓"/"holding insight"/"我的持仓怎么样"/"该买还是该卖"
- 阶段 5 完成后用户要求进一步分析
- 用户直接要求对持仓给出操作建议

**跳过条件**：
- 无 jvQuant 配置且用户未要求 → 跳过并告知
- 无持仓 → 输出空结果并告知

## 首次部署

在新服务器上安装本 skill 时，先探测目标系统，再执行安装脚本：

```bash
# 1. 探测系统（让 LLM 了解实际环境）
uname -s && cat /etc/os-release 2>/dev/null | grep -E "^(ID|ID_LIKE|NAME)=" | head -3

# 2. 执行安装（脚本自动识别 Debian/Ubuntu/RHEL/Fedora，无需手动选命令）
bash setup.sh
```

`setup.sh` 支持：macOS、Ubuntu/Debian（apt）、RHEL/CentOS/Rocky/AlmaLinux/Fedora（dnf/yum）。
若系统不在此列，脚本会退出并提示参考 `requirements.txt` 手动安装。

## Strategy Evolution

- `strategy/default.yaml`：基线策略，不可修改
- `strategy/active.yaml`：当前生效策略，可微调

修改门槛（ProposalJudge）：平均分 >= 7 且无任何维度 < 4 才允许写入；否则仅记录提案。

## Knowledge Evolution

- `evolution/known_pitfalls.md`：已知交易陷阱
- `evolution/selection_rules.md`：选股规则修正
- `evolution/feedback.md`：诊断反馈（由诊断脚本和交易复盘脚本写入）
