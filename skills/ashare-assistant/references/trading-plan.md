# 阶段4：输出交易计划

**⚠️ STEP 0：本阶段必须产出两份独立报告，完整模板见 `references/report-templates.md`，不得依赖记忆重建，必须逐章节对照填写。**

两份报告：
1. **复盘报告** → `~/.ashare-assistant/data/{DATE}/market_review.md`（市场分析+选股，无账户信息）
2. **交易计划** → `~/.ashare-assistant/data/{DATE}/trading_plan.md`（含账户操作清单）

保留所有章节标题，无内容时写"无"。

---

## 报告一：复盘报告（market_review.md）

按 `references/report-templates.md` 中"模板一"填写，包含：

- 市场环境（含强弱评级、主线风格、仓位建议）
- 美股前夜影响（有数据则填，无则跳过）
- 题材线索（含**市场情绪+舆情证据**，必须有帖子引用，不得为空）
- 候选股分析（含四维标签、深度分析校准）
- 风险提示
- 精华言论（10条）
- **七、趋势候选股汇总**（必填，从趋势扫描报告中提取全部4星/5星，或明确写"无"）

---

## 报告二：交易计划（trading_plan.md）

按 `references/report-templates.md` 中"模板二"填写，包含：

- 账户状态（账户健康度、总资产、可用资金、持仓盈亏）
- 交易复盘（当日执行情况，无交易则写"今日无交易"）
- 持仓洞察（每只持仓建议，含股数/动作/依据表格）
- 明日交易计划（每只候选股的操作清单）
- 执行优先级
- 仓位分配汇总

---

## 保存命令

```bash
mkdir -p ~/.ashare-assistant/data/{DATE}

# 保存复盘报告
cat > ~/.ashare-assistant/data/{DATE}/market_review.md << '__REPORT__'
[复盘报告正文]
__REPORT__

# 保存交易计划
cat > ~/.ashare-assistant/data/{DATE}/trading_plan.md << '__PLAN__'
[交易计划正文]
__PLAN__

# 向后兼容：旧路径保持可用
cp ~/.ashare-assistant/data/{DATE}/market_review.md ~/.ashare-assistant/data/{DATE}/report.md
```

---

**candidates.json 关键字段约束**：

1. `run_id`：必须使用阶段2读取的 `run_id.json` 中的值，不得自行生成
2. `market.regime` 只能是 `strong` / `neutral` / `weak`
3. `candidates[].action` 只能是 `buy` / `hold` / `sell` / `trim` / `watch`
4. `thesis_short` 与 `risk_note` 不超过 30 字

若阶段3结构校验通过（`validate_output.py` 返回 `ok=true`），执行：

```bash
python3 scripts/decision_logger.py \
  --input ~/.ashare-assistant/data/{DATE}/candidates.json \
  --log-file ~/.ashare-assistant/memory/decision_log.jsonl
```

---

强制语言约束：

1. 不使用缩写词（例如 `THS`、`DR`），统一写全称（例如"同花顺""深度分析"）。
2. 不单独输出"深度分析校准结论"章节，校准内容必须并入对应个股条目。

---

## ⚠️ 输出自检清单（发送报告前逐条核对）

**复盘报告检查**：

- [ ] 市场情绪已填写具体的淘股吧帖子引用（至少2条精华帖标题），不得仅写"乐观/谨慎"一词
- [ ] 新闻舆情已引用至少1条具体新闻标题
- [ ] 报告末尾已包含"七、趋势候选股汇总"表格（含 trend_report.md 中所有4/5星趋势股，不得遗漏）
- [ ] 报告中无缩写词（同花顺不写 THS，深度分析不写 DR）
- [ ] 深度分析结论已并入对应个股条目，不存在独立的"深度分析校准结论"章节

**交易计划检查**：

- [ ] 每只持仓股已给出持仓洞察（建议股数为100股整数倍，持仓≤100股时不建议操作）
- [ ] 每只候选股的目标仓位已换算为股数（向下取整至100股整数倍）
- [ ] 总仓位符合当日市场强弱建议
- [ ] 无单只股票仓位超出策略上限（趋势股≤20%，题材股≤15%）
- [ ] 交易复盘部分已基于 trade_review.json 数据（若无交易则明确说明）

**JSON文件检查**：

- [ ] `candidates.json` 中的 `run_id` 与阶段2读取的 `run_id.json` 中一致（非自行生成）
- [ ] `market.regime` 只使用 `strong` / `neutral` / `weak` 三者之一
- [ ] 每个候选股的 `action` 只使用 `buy` / `hold` / `sell` / `trim` / `watch`
- [ ] `thesis_short` 和 `risk_note` 均不超过 30 字
- [ ] 若 validate 失败，已标记 `run_failed=true` 且未写入 decision_log
