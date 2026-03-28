# Batch 模式

> 大量短命 worker 并行执行独立任务，互不依赖。

## 拓扑图

```
  ┌──────────────┐
  │ Orchestrator │
  │  任务列表     │
  │  [T1,T2,...TN]│
  └──────┬───────┘
         │ 循环分发（可分批）
    ┌────┴────┬────────┬────────┬── ... ──┐
    ▼         ▼        ▼        ▼         ▼
 Worker 1  Worker 2  Worker 3  Worker 4  Worker N
 (Task 1)  (Task 2)  (Task 3)  (Task 4)  (Task N)
    │         │        │        │         │
    ▼         ▼        ▼        ▼         ▼
 Output 1  Output 2  Output 3  Output 4  Output N

  Orchestrator 收集所有输出 + 失败列表
```

## 适用条件

- 有大量结构相似的独立任务（如批量修 bug、批量处理文件、批量跑测试）
- 每个任务短小、自包含，worker 之间无需通信
- 可接受部分失败（单个失败不影响整体）

## 编排规则

1. Orchestrator 维护任务列表，为每个任务生成独立 prompt
2. 通过 shell 后台任务批量分发：

```bash
TASKS=("fix bug in auth.py" "fix bug in cache.py" "fix bug in db.py")
PIDS=()

for i in "${!TASKS[@]}"; do
  omp-team run codex "${TASKS[$i]}" \
    --output-file "/tmp/batch-${i}.md" \
    --cwd /project \
    --timeout 120 &
  PIDS+=($!)
done

# 等待所有 worker 完成
FAILED=()
for i in "${!PIDS[@]}"; do
  wait ${PIDS[$i]}
  if [ $? -ne 0 ]; then
    FAILED+=("Task $i: ${TASKS[$i]}")
  fi
done

# 报告结果
echo "Completed: $((${#TASKS[@]} - ${#FAILED[@]}))/${#TASKS[@]}"
if [ ${#FAILED[@]} -gt 0 ]; then
  echo "Failed tasks:" >&2
  printf '  - %s\n' "${FAILED[@]}" >&2
fi
```

3. **分批控制**：当任务数量很大时（>10），分批执行避免资源耗尽：

```bash
BATCH_SIZE=5
for ((start=0; start<${#TASKS[@]}; start+=BATCH_SIZE)); do
  # 启动一批
  PIDS=()
  for ((i=start; i<start+BATCH_SIZE && i<${#TASKS[@]}; i++)); do
    omp-team run codex "${TASKS[$i]}" --output-file "/tmp/batch-${i}.md" &
    PIDS+=($!)
  done
  # 等待本批完成
  for pid in "${PIDS[@]}"; do wait $pid; done
done
```

4. 所有任务使用相同的 prompt 模板，只替换任务特定变量

## 失败处理

- 单个 worker 失败**不影响**其他 worker
- Orchestrator 记录失败列表（任务 ID + 错误信息）
- 全部完成后，orchestrator 决定：
  - 对失败任务重试（换 prompt 或换 runtime）
  - 汇报失败列表给用户
  - 如果失败率过高（>50%），停止并排查共性问题

## 退出条件

- **成功**：所有任务完成（或失败率在可接受范围内）
- **部分成功**：大部分任务完成，失败列表已记录
- **中止**：失败率超过阈值，orchestrator 停止剩余任务并报告
