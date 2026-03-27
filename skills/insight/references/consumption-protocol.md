# Agent 消费 Insight 协议

## 强制消费流程

Agent 在执行新任务前，**必须**执行以下步骤：

### Step 1：检索相关 insight

```bash
omp-insight search "<当前任务的关键词描述>" --json --top-k 5
```

### Step 2：声明历史经验

在回复开头声明：

```
根据历史经验，我将注意以下问题：
1. [insight-id] 当 <trigger> 时，应该 <corrected_behavior> 而不是 <wrong_default>
2. ...
```

### Step 3：记录消费结果

任务完成后，由 orchestrator 或 agent 自身记录：
- 是否采用了 insight 的建议（adopted: true/false）
- 如果未采用，原因是什么（feedback）

## Prompt 模板

其他 Agent 可以在 system prompt 中引用以下片段来启用强制消费：

```
## Insight 消费协议

在开始任何任务之前，你必须：
1. 运行 `omp-insight search "<任务描述关键词>" --json --top-k 5`
2. 阅读返回的 insight 列表
3. 在回复开头声明你将注意的历史经验
4. 如果没有相关 insight，声明"未找到相关历史经验"

这确保你不会重复过去已经纠正过的错误。
```

## 消费追踪指标

| 指标 | 计算方式 | 目标 |
|------|---------|------|
| 命中率 | 检索返回结果的任务占比 | > 50% |
| 采用率 | adopted=true 的消费占比 | > 70% |
| 纠错复发率 | 同类错误在消费 insight 后仍发生的比率 | < 20% |

通过 `omp-insight stats` 查看。
