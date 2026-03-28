# Team References

> 编排模式速查 + 场景->模式映射。Orchestrator 从这里开始。

## 模式速查

| 模式 | 文档 | 拓扑 | 适用场景 |
|------|------|------|---------|
| Pipeline | patterns/pipeline.md | A -> B -> C 线性链 | 编码->审查、多阶段处理 |
| Fan-out/Fan-in | patterns/fan-out-fan-in.md | 并行分发 + 聚合 | 辩论、多视角分析 |
| Discussion | patterns/discussion.md | 多 agent 共享上下文 | 圆桌讨论、头脑风暴 |
| Batch | patterns/batch.md | 大量短命 worker | 批量 bug 修复、并行任务 |

## 场景索引

| 场景 | 文档 | 使用模式 |
|------|------|---------|
| 编码与评审 | scenarios/code-and-review.md | Pipeline |
| 正反辩论 | scenarios/debate.md | Fan-out/Fan-in |
| 轻量圆桌 | scenarios/round-table.md | Discussion |

## Prompt 框架

| 模板 | 文档 | 用途 |
|------|------|------|
| 编码任务 | prompts/coding-task.md | 分配编码任务给 worker |
| 代码审查 | prompts/code-review.md | 分配代码审查给 worker |
| 角色激活 | prompts/role-activation.md | 通用角色定义 |

## Runtime 速查

详见 [runtime-reference.md](runtime-reference.md)
