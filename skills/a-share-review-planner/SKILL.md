---
name: a-share-review-planner
description: Use when user says "复盘"、"今日回顾"、"明日计划"、"选股" or wants to
  review A-share market and generate trading plan. Works on trading days,
  holidays, and weekends.
---

# A股复盘与交易计划

<IMPORTANT>
在开始任何分析之前，必须遵守以下约束：

- 禁止猜测数据：某数据源失败时，明确告知用户并跳过，不得用臆测填充
- 策略修改要谨慎：每次最多调整 active.yaml 中 1-2 个参数，必须写明原因
- 数据时效性：采集数据为当日快照，不得使用过期数据分析
- 严禁跳过阶段：不得在未执行阶段1采集时直接分析，也不得在未完成阶段4/5时结束任务
</IMPORTANT>

## Overview

目标：完成每日收盘后的A股复盘与次日交易计划。
流程：采集多源数据 → 分析市场与题材 → 生成候选与计划 → 落盘与结构化校验 → PDF推送。
原则：LLM负责判断，脚本负责执行。

## When to Use

- 用户说“复盘”“今日回顾”“明日计划”“帮我选股”
- 交易日收盘后
- 节假日/周末（使用最近交易日行情数据）

## 数据完整性说明

| 场景 | 新闻/舆情 | 板块资金 | 趋势扫描 |
|------|-----------|---------|---------|
| 交易日收盘后 | ✅ 完整 | ✅ 完整 | ✅ 完整 |
| 节假日/周末 | ✅ 有效 | ⚠️ 最后交易日数据 | ⚠️ 最后交易日数据 |
| 盘中 | ✅ 有效 | ⚠️ 实时但不完整 | ⚠️ 基于前一日收盘 |

## Workflow

完整工作流共 5 个阶段，必须按顺序执行。

### 阶段1：数据采集

按 `references/stage1-collect.md` 执行。

### 阶段2：数据读取

按 `references/stage2-read.md` 执行。

### 阶段3：分析与校验

按 `references/stage3-analysis.md` 执行。
详细分析框架见 `references/analysis-framework.md`。

### 阶段4：输出交易计划

按 `references/stage4-output.md` 执行。

### 阶段5：PDF推送

按 `references/stage5-delivery.md` 执行。

## Strategy Evolution

- `strategy/default.yaml`：基线策略，不可修改
- `strategy/active.yaml`：当前生效策略，可微调

修改门槛（ProposalJudge）：平均分 >= 7 且无任何维度 < 4 才允许写入；否则仅记录提案。

## Knowledge Evolution

- `evolution/known_pitfalls.md`：已知交易陷阱
- `evolution/selection_rules.md`：选股规则修正
- `evolution/feedback.md`：诊断反馈（由诊断脚本写入）
