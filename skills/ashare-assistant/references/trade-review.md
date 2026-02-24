# 阶段5：交易复盘

**触发时机**：阶段 1-4 完成后，或用户主动要求"交易复盘"/"检查执行"/"review"。

**前提条件**：

- 已配置 jvQuant 账户（环境变量或 `~/.openclaw/jvquant.json`）
- 当日有交易数据（至少 broker_account 可用）

> 若无 jvQuant 配置或获取失败，明确告知用户并跳过本阶段，不得猜测数据。

## 步骤

### 5.1 执行交易复盘脚本

> **必须从 skill 根目录执行**，否则报 `ModuleNotFoundError: No module named 'scripts'`。

```bash
cd <skill_root>   # 即 SKILL.md 所在目录，例如 skills/ashare-assistant/
PYTHONPATH=. python3 scripts/trade_review.py \
  --decision-log ~/.ashare-assistant/memory/decision_log.jsonl \
  --strategy strategy/active.yaml \
  --output ~/.ashare-assistant/data/{DATE}/trade_review.json \
  --pretty
```

脚本自动完成：
1. 从 jvQuant 获取当日持仓 + 委托（自动持久化到 `~/.openclaw/broker_data/`）
2. 加载最近的 `decision_log` 记录（昨日或最近一次交易计划）
3. 加载 `active.yaml` 策略限制
4. 执行六大瑕疵检测
5. 输出 `trade_review.json` 并追加 `evolution/feedback.md`

### 5.2 读取复盘结果

读取 `~/.ashare-assistant/data/{DATE}/trade_review.json`，关注以下要点：

1. **flaw_counts** — 瑕疵总览（error / warning / info 各多少）
2. **flaws** — 逐条瑕疵明细，按严重程度排序解读
3. **timing_scores** — 择时评分（A/B/C/D），重点关注 C/D 级
4. **position_check** — 仓位合规性（单股超限、总仓位与市场匹配）
5. **execution_summary** — 计划匹配率（plan_match_rate）
6. **improvement_suggestions** — 系统生成的改进建议

### 5.3 生成复盘总结

将结果整理为人类可读的总结，追加到 report.md 末尾（若已有），或独立输出：

```markdown
## 七、交易执行复盘

### 执行概况
- 总委托 {total_orders} 笔，买入 {buy_orders}，卖出 {sell_orders}，撤单 {cancelled_orders}
- 计划匹配率：{plan_match_rate}%
- 账户模式：{account_mode}，总仓位 {total_position_pct}%

### 瑕疵检测
- error: {error_count}，warning: {warning_count}，info: {info_count}

#### 严重问题（error）
[逐条列出 error 级瑕疵及建议]

#### 注意事项（warning）
[逐条列出 warning 级瑕疵]

### 择时评分
| 代码 | 名称 | 方向 | 成交价 | VWAP | 评分 |
[timing_scores 表格]

### 改进建议
[improvement_suggestions]
```

### 5.4 决策闭环检查

若同时完成了阶段 4（交易计划），检查本次复盘是否暴露了计划层面的系统性问题：

- **连续 3 次以上出现同类 error** → 建议在 `evolution/known_pitfalls.md` 新增条目
- **plan_match_rate < 50%** → 提示用户检查是否计划质量不足或执行纪律松散
- **择时 C/D 级占比 > 50%** → 建议关注分时图位置，避免追高/恐慌

## 瑕疵类别说明

| 类别 | 说明 | 示例 |
|------|------|------|
| unplanned_trade | 买入不在推荐列表中的股票 | 计划外冲动买入 |
| missed_execution | 推荐 action=buy 但未执行 | 错过高分候选 |
| timing_flaw | 买入在日内高位或卖出在低位 | 追高买入、恐慌卖出 |
| position_flaw | 单股或总仓位超出策略限制 | 弱市重仓 |
| holding_flaw | 持仓管理不当 | 未执行 MA20 止损 |
| discipline_flaw | 违反交易纪律 | 防御模式加仓 |

## 严重程度

| 级别 | 含义 | 处理 |
|------|------|------|
| error | 可能导致重大损失 | 必须在报告中突出标注 |
| warning | 偏离计划 | 需要在报告中说明 |
| info | 轻微参考 | 可选择性提及 |

## 无交易日处理

若当日无委托记录（`total_orders = 0`），脚本仍正常运行：

- 输出 `execution_summary` 全部为 0
- 如有持仓，仍检测 holding_flaw（MA20 止损、MA5 乖离）
- 如有 decision_log 且有 action=buy 候选，检测 missed_execution
