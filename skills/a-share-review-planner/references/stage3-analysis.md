# 阶段3：分析与校验

> **何时读取 analysis-framework.md**：对某个分析步骤有疑问，或首次执行时，按需读取对应章节。
> 熟悉流程时无需全文加载；各步骤的章节标题与下方编号一一对应。

必须严格按照 `references/analysis-framework.md` 执行，不得跳步。

分析阶段结论要求（必须按序执行，不得跳步）：

1. 市场环境判断（强弱评级、风格、账户健康度、仓位建议）
2. 题材线索识别（潜在/新题材与已发酵热点分层）
3. 个股筛选（四因子评分，输出候选股列表）
4. **个股深度分析（第3.5步）**：优先使用批量脚本 `run_deep_research_batch.py` 并行执行；生成 `dr_{CODE}_em.json` / `dr_{CODE}_tgb.json` / `dr_{CODE}_compact.json` / `dr_{CODE}_brief.json`，完成仓位校准 ← **此步骤必须执行，不得跳过**
5. 交易计划制定（校准信息并入个股条目，不得单独重复一节）
6. 风险检查（LLM 定性）
7. 策略回顾与微调（ProposalJudge）
8. 知识库积累（evolution 文档增量）
9. 精华言论提炼（10条，仅方法论/心理/风控）

阶段3完成后，必须先做硬规则校验，再做结构化输出校验：

推荐的第3.5步批量命令：

```bash
python3 {SKILL_DIR}/scripts/run_deep_research_batch.py \
  --candidates-file /tmp/a-share-review/{DATE}/candidates.json \
  --output-dir /tmp/a-share-review/{DATE} \
  --max-workers 4 \
  --per-stock-timeout-sec 180 \
  --total-timeout-sec 900
```

执行后会写入 `/tmp/a-share-review/{DATE}/dr_timing.json`，用于定位慢点与超时股票。

```bash
python3 {SKILL_DIR}/scripts/risk_check.py --input /tmp/a-share-review/{DATE}/candidates.json
```

如 `risk_check.py` 有 error 级别违规，必须调整候选计划并重试，直至通过。
warn 级别违规需在报告“风险提示”章节显式说明。

```bash
python3 {SKILL_DIR}/scripts/validate_output.py \
  --input /tmp/a-share-review/{DATE}/candidates.json
```

若结构校验失败：

1. 标记 `run_failed=true`
2. 标记 `risk_flags.output_schema_invalid=true`
3. 继续产出人类可读报告
4. 不写 `decision_log`
