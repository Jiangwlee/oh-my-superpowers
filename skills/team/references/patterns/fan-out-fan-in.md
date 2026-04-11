# Fan-out/Fan-in 模式

> 并行分发 + 聚合：同一任务从 N 个视角并行执行，收集后由 orchestrator 综合。

## 拓扑图

```
                         ┌──────────────┐
                         │ Orchestrator │
                         │  构建 N 个    │
                         │  差异化 prompt│
                         └──────┬───────┘
               Fan-out          │
          ┌─────────────┬───────┴───────┬─────────────┐
          ▼             ▼               ▼             ▼
   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
   │ Worker A   │ │ Worker B   │ │ Worker C   │ │ Worker N   │
   │ (视角 1)   │ │ (视角 2)   │ │ (视角 3)   │ │ (视角 N)   │
   └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
         │              │              │              │
         └──────────────┴──────┬───────┴──────────────┘
               Fan-in          │
                         ┌─────▼───────┐
                         │ Orchestrator │
                         │  聚合 + 综合 │
                         └──────────────┘
```

## 适用条件

- 同一任务可从多个视角/角色分析（如安全、性能、可维护性）
- 各 worker 之间无依赖，可真正并行
- 需要 orchestrator 最终综合多方意见

## 编排规则

1. Orchestrator 为每个 worker 构建差异化的 prompt（不同角色/视角/约束）
2. 使用 `--output-file` 将各 worker 输出写入独立文件
3. 通过 shell 后台任务实现并行：

```bash
# Fan-out：并行启动
omp team run claude "从安全角度分析..." --output-file /tmp/security.md &
PID1=$!
omp team run claude "从性能角度分析..." --output-file /tmp/performance.md &
PID2=$!
omp team run pi "从成本角度分析..." --output-file /tmp/cost.md &
PID3=$!
wait $PID1 $PID2 $PID3

# Fan-in：收集结果
SECURITY=$(cat /tmp/security.md)
PERFORMANCE=$(cat /tmp/performance.md)
COST=$(cat /tmp/cost.md)

# Orchestrator 聚合（可以自行综合，也可以再派一个 worker）
```

4. 每个 worker 的 prompt 必须自包含（不能假设看到其他 worker 的输出）

## 聚合策略

Orchestrator 在 fan-in 阶段选择聚合方式：

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| 投票 | 多数意见胜出 | 二元决策（通过/不通过） |
| 加权合并 | 按 worker 专长加权 | 多维度评审 |
| LLM 综合 | 将所有输出交给一个 worker 做最终综合 | 开放式分析 |
| 列举 | 直接列出所有视角，不做裁决 | 信息收集 |

## 失败处理

- 部分 worker 失败**不阻塞**整个流程
- Orchestrator 设定**最低完成数**（如 N 个 worker 中至少 M 个成功）
- 检查每个后台任务的退出码：

```bash
wait $PID1; EXIT1=$?
wait $PID2; EXIT2=$?
wait $PID3; EXIT3=$?

SUCCEEDED=0
[ $EXIT1 -eq 0 ] && SUCCEEDED=$((SUCCEEDED + 1))
[ $EXIT2 -eq 0 ] && SUCCEEDED=$((SUCCEEDED + 1))
[ $EXIT3 -eq 0 ] && SUCCEEDED=$((SUCCEEDED + 1))

if [ $SUCCEEDED -lt 2 ]; then
  echo "Too few workers succeeded ($SUCCEEDED/3)" >&2
  exit 1
fi
```

## 退出条件

- **成功**：至少 M 个 worker 完成，orchestrator 聚合出结论
- **失败**：成功 worker 数低于最低阈值
- **超时**：个别 worker 超时时，用已完成的结果继续聚合
