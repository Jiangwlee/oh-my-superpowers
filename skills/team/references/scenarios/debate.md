# Debate

> **DEPRECATED**: 多视角辩论场景已由独立 skill `round-table` 承担，
> 提供完整的角色库、session 管理和多轮讨论流程。
> 本文档保留作为 team 原语层的 fan-out/fan-in 用法示例。

> pattern: fan-out-fan-in
> 正反方对抗式辩论：多 agent 并行阐述立场 → orchestrator 聚合结论。

## 参与者配置

- 至少 2 个对立方（使用 `prompts/role-activation.md` 定义角色）
- 每方使用不同 runtime 或相同 runtime 均可
- 建议：不同 runtime 天然产生不同推理风格，增加辩论多样性

## 编排流程

### Phase 1: 定义辩题与角色

1. Orchestrator 定义辩题，明确论域边界
2. 为每方构造角色 prompt（使用 `prompts/role-activation.md` 模板）：
   - 角色身份和立场
   - 辩题描述
   - 立场要求（正方/反方/特定视角）
   - 输出格式要求：论点 + 论据 + 结论

### Phase 2: 并行阐述

3. 并行执行各方辩论：

```bash
omp dispatch run claude --prompt-file debate-pro.md --output-file debate-side-1.txt &
omp dispatch run codex --prompt-file debate-con.md --output-file debate-side-2.txt &
omp dispatch run pi --prompt-file debate-neutral.md --output-file debate-side-3.txt &
wait
```

4. 检查所有退出码，处理失败方（重试或跳过）

### Phase 3: 聚合分析

5. Orchestrator 读取所有输出，构造综合分析 prompt：
   - 各方核心论点摘要
   - 要求识别：共识区域、根本分歧、逻辑漏洞、最强论点

6. 执行综合分析：

```bash
omp dispatch run claude --prompt-file synthesis.md --output-file synthesis-out.txt
```

### Phase 4: 多轮深化（可选）

7. 将上轮综合结论反馈给各方：
   - 在新一轮 prompt 中包含对方论点和综合分析
   - 要求各方回应对方最强论点、修正自身弱点
8. 重复 Phase 2-3

## 完成判定

- Orchestrator 认为论点已充分展开（新一轮无实质新论据）
- 或达到预设轮次（建议 2-3 轮，辩论比讨论更快收敛）
- 最终输出：综合分析报告，包含各方立场、关键分歧、结论建议

## 示例编排序列

```
[Orchestrator] 辩题: "微服务 vs 单体架构"
  - 正方 (claude): 微服务倡导者
  - 反方 (codex): 单体架构捍卫者
  - 中立方 (pi): 务实工程师

[Round 1] 并行执行 → 收集输出 → 综合分析
[Round 2] 反馈对方论点 → 并行回应 → 再次综合
[Final] 输出综合报告：适用场景矩阵 + 决策建议
```
