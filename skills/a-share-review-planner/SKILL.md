---
name: a-share-review-planner
description: >
  A-share daily market review and next-day trading plan. Collects multi-source
  data (news, sector flows, sentiment, trend scan), performs 5-stage structured
  analysis, and outputs a formatted report with PDF delivery to Telegram.
  Use when: (1) user says "复盘"、"今日回顾"、"明日计划"、"选股"、"帮我看看大盘"、
  "今天行情"、"大盘分析"、"明天买什么"、"帮我分析行情", (2) user wants A-share market
  analysis or trading plan, (3) user says "板块"、"涨停"、"题材"、"选股".
  Works on trading days, holidays, and weekends.
---

# A股复盘与交易计划

<HARD-GATE>
NO ANALYSIS WITHOUT RUNNING collect_sentiment.py FIRST.
NO TRADING PLAN WITHOUT COMPLETING STAGES 1–3 FIRST.
NO REPORT WITHOUT PASSING risk_check.py FIRST.
NO TEXT RETURN WITHOUT FIRST ATTEMPTING PDF GENERATION AND SEND.

Violating the letter of this rule is violating the spirit of this rule.
No exceptions. Not even when the user asks for a quick summary.
</HARD-GATE>

## 开始前声明

开始复盘前，先声明：
> "开始 A 股复盘，共 5 个阶段。当前阶段：[阶段1-数据采集]"

每完成一个阶段，更新声明：
> "阶段X完成，进入阶段X+1。"

## 核心约束

- **禁止猜测数据**：某数据源失败时，明确告知并跳过，不得用臆测填充
- **策略修改要谨慎**：每次最多调整 active.yaml 中 1-2 个参数，必须写明原因
- **数据时效性**：采集数据为当日快照，不得使用过期数据分析
- **严禁跳过阶段**：不得在未执行阶段1采集时直接分析，也不得在未完成阶段4/5时结束任务

## 常见借口——一律拒绝

| LLM 可能说的 | 实际情况 |
|-------------|---------|
| "用户只是想快速了解，不需要完整采集" | 没有真实数据就没有真实分析，臆测比无结果更危险 |
| "数据昨天已经采集过了" | 行情每日变化，过期数据会产生错误判断 |
| "Deep Research 比较慢，可以跳过" | 个股深度分析是仓位校准的前提，跳过会导致入场价格失准 |
| "risk_check 只是 warn，不是 error" | warn 级必须在报告"风险提示"章节显式说明，不可静默忽略 |

## Overview

目标：完成每日收盘后的A股复盘与次日交易计划。
流程：采集多源数据 → 分析市场与题材 → 生成候选与计划 → 落盘与结构化校验 → PDF推送。
原则：LLM负责判断，脚本负责执行。

**终态**：PDF 已通过 Telegram 发送给用户，candidates.json 和 report.md 已落盘，
decision_log 已写入（校验通过时）。
仅当 report_to_image.py 或 send_telegram_file.py 脚本执行失败时，才允许以文本形式
紧急降级返回，并须向用户说明失败原因。

## 关键决策分支

在执行过程中，遇到以下情况须按指定路径处理：

```
阶段1完成
  └─ 若 collection_summary 有失败源 → 标注失败源，继续处理可用数据，不中止

阶段2完成
  └─ 若 account_mode = critical → 阶段3仅做市场分析，跳过交易计划，直接进阶段5

阶段3完成
  ├─ 若 risk_check 有 error 级违规 → 必须修改候选并重跑，不得继续
  └─ 若 validate_output.py 失败 → run_failed=true，继续输出人类可读报告，不写 decision_log
```

## Workflow

完整工作流共 5 个阶段，必须按顺序执行。

### 阶段1：数据采集

按 `references/stage1-collect.md` 执行。

### 阶段2：数据读取

按 `references/stage2-read.md` 执行。

### 阶段3：分析与校验

按 `references/stage3-analysis.md` 执行。
详细分析框架按需见 `references/analysis-framework.md`。

### 阶段4：输出交易计划

按 `references/stage4-output.md` 执行。

### 阶段5：PDF推送

按 `references/stage5-delivery.md` 执行。

## 首次部署

在新服务器上安装本 skill 时，先探测目标系统，再执行安装脚本：

```bash
# 1. 探测系统（让 LLM 了解实际环境）
uname -s && cat /etc/os-release 2>/dev/null | grep -E "^(ID|ID_LIKE|NAME)=" | head -3

# 2. 执行安装（脚本自动识别 Debian/Ubuntu/RHEL/Fedora，无需手动选命令）
bash {SKILL_DIR}/setup.sh
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
- `evolution/feedback.md`：诊断反馈（由诊断脚本写入）
