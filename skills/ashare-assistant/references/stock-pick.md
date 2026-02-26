# 阶段3：分析与校验

> **何时读取 analysis-framework.md**：对某个分析步骤有疑问，或首次执行时，按需读取对应章节。
> 熟悉流程时无需全文加载；各步骤的章节标题与下方编号一一对应。

必须严格按照 `references/analysis-framework.md` 执行，不得跳步。

分析阶段结论要求（必须按序执行，不得跳步）：

1. 市场环境判断（强弱评级、风格、账户健康度、仓位建议）
2. 题材线索识别（潜在/新题材与已发酵热点分层）
3. 个股筛选（四因子评分，输出候选股列表）
4. **个股深度分析（第3.5步）**：使用子代理分析 `run_analysis.py --tasks stock`，生成 `report/dr_{CODE}_brief.md`，完成仓位校准 ← **此步骤必须执行，不得跳过**
5. 交易计划制定（校准信息并入个股条目，不得单独重复一节）
6. 风险检查（LLM 定性）
7. 策略回顾与微调（ProposalJudge）
8. 知识库积累（evolution 文档增量）
9. 精华言论提炼（10条，仅方法论/心理/风控）

阶段3完成后，必须先做硬规则校验，再做结构化输出校验。

### 第3.5步推荐执行方式

**方式一（推荐）：子代理分析**

```bash
PYTHONPATH=. python3 scripts/run_analysis.py \
  --data-dir ~/.ashare-assistant/data/{DATE} \
  --tasks stock \
  --stock-code {CODE} --stock-name {NAME}
```

子代理自动读取 `raw/deep_research/dr_{CODE}_em.json`、`raw/deep_research/dr_{CODE}_tgb.json`，生成 `report/dr_{CODE}_brief.md`。

**方式二：批量数据采集 + 手动分析**

```bash
  # 批量并行采集原始数据
  PYTHONPATH=. python3 scripts/run_deep_research_batch.py \
  --candidates-file ~/.ashare-assistant/data/{DATE}/analysis/candidates.json \
  --output-dir ~/.ashare-assistant/data/{DATE} \
  --max-workers 4 \
  --per-stock-timeout-sec 180 \
  --total-timeout-sec 900
```

执行后会写入 `~/.ashare-assistant/data/{DATE}/dr_timing.json`，用于定位慢点与超时股票。

### 校验

```bash
python3 scripts/risk_check.py --input ~/.ashare-assistant/data/{DATE}/analysis/candidates.json
```

如 `risk_check.py` 有 error 级别违规，必须调整候选计划并重试，直至通过。
warn 级别违规需在报告"风险提示"章节显式说明。

```bash
python3 scripts/validate_output.py \
  --input ~/.ashare-assistant/data/{DATE}/analysis/candidates.json
```

若结构校验失败：

1. 标记 `run_failed=true`
2. 标记 `risk_flags.output_schema_invalid=true`
3. 继续产出人类可读报告
4. 不写 `decision_log`
