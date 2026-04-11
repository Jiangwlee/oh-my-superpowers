# Discussion 模式

> 多 agent 共享上下文讨论：每轮所有参与者看到前一轮输出，逐步收敛。

## 拓扑图

```
Round 1:
  ┌──────────────┐
  │ Orchestrator │──→ 构建初始 prompt（含议题 + 角色分配）
  └──────┬───────┘
         │ 并行分发
    ┌────┴────┬────────┐
    ▼         ▼        ▼
 Worker A  Worker B  Worker C
    │         │        │
    └────┬────┴────────┘
         ▼
  Orchestrator 聚合 Round 1 输出

Round 2:
  ┌──────────────┐
  │ Orchestrator │──→ 构建 prompt（含 Round 1 所有输出 + 引导问题）
  └──────┬───────┘
         │ 并行分发
    ┌────┴────┬────────┐
    ▼         ▼        ▼
 Worker A  Worker B  Worker C
    │         │        │
    └────┬────┴────────┘
         ▼
  Orchestrator 聚合 Round 2 输出

  ... 重复直到退出条件 ...
```

## 适用条件

- 问题需要多视角迭代讨论（不是一轮能定的）
- 参与者需要看到彼此的观点并做出回应
- 需要逐轮收敛到结论

## 编排规则

1. Orchestrator 在每轮开始前构建 prompt，包含：
   - 议题背景（首轮）或前一轮所有参与者的输出（后续轮）
   - 当前轮次的引导问题或焦点
   - 参与者的角色定义和行为约束

2. 每轮内部使用 Fan-out/Fan-in 模式并行执行：

```bash
# Round 1
omp team run claude "你是安全专家。议题：... 请给出观点" --output-file /tmp/r1-security.md &
omp team run claude "你是架构师。议题：... 请给出观点" --output-file /tmp/r1-arch.md &
omp team run pi "你是产品经理。议题：... 请给出观点" --output-file /tmp/r1-pm.md &
wait

# Orchestrator 聚合 Round 1，构建 Round 2 prompt
# Round 2 的 prompt 包含 Round 1 所有人的观点

omp team run claude "你是安全专家。前轮讨论：[R1输出]。请回应..." --output-file /tmp/r2-security.md &
omp team run claude "你是架构师。前轮讨论：[R1输出]。请回应..." --output-file /tmp/r2-arch.md &
omp team run pi "你是产品经理。前轮讨论：[R1输出]。请回应..." --output-file /tmp/r2-pm.md &
wait
```

3. Orchestrator 在每轮之间：
   - 聚合所有输出，提炼争议点和共识点
   - 判断是否达到退出条件
   - 构建下一轮的引导问题

## 上下文管理

- 随着轮次增加，历史输出会膨胀。Orchestrator 应该：
  - 对前轮输出做摘要压缩，而非全文透传
  - 只保留与当前焦点相关的历史
  - 在 prompt 中标明"本轮焦点"，避免讨论发散

## 失败处理

- 单个 worker 在某轮失败：跳过该 worker 本轮输出，其他人继续
- 连续两轮同一 worker 失败：从讨论中移除该角色
- 超时：缩短 prompt（减少历史上下文），或降低参与者数量

## 退出条件

- **达成共识**：Orchestrator 判断所有参与者观点趋同
- **达到最大轮次**：预设上限（建议 3-5 轮），防止无限循环
- **用户指示停止**：Orchestrator 在每轮结束后可征求用户意见
- **收敛停滞**：连续两轮无新观点产生
