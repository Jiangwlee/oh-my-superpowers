# 阶段3：分析与校验

必须严格按照 `references/analysis-framework.md` 执行，不得跳步。

分析阶段结论要求：

1. 市场环境判断（强弱评级、风格、账户健康度、仓位建议）
2. 题材线索识别（潜在/新题材与已发酵热点分层）
3. 个股筛选（趋势股 + 题材股）
4. 个股深度分析（第3.5步，生成 brief 并做仓位校准）
5. 交易计划制定（校准信息并入个股条目，不得单独重复一节）
6. 风险检查（LLM 定性）
7. 策略回顾与微调（ProposalJudge）
8. 知识库积累（evolution 文档增量）
9. 精华言论提炼（10条，仅方法论/心理/风控）

阶段3完成后，必须先做硬规则校验，再做结构化输出校验：

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
