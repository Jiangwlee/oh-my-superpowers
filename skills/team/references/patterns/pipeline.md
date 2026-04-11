# Pipeline 模式

> 线性链式编排：A -> B -> C，前一步输出是下一步输入。

## 拓扑图

```
┌──────────┐     stdout     ┌──────────┐     stdout     ┌──────────┐
│ Worker A │ ───────────→  │ Worker B │ ───────────→  │ Worker C │
│ (codex)  │               │ (claude) │               │ (claude) │
└──────────┘               └──────────┘               └──────────┘
     ↑                          ↑                          ↑
     │                          │                          │
  Orchestrator              Orchestrator              Orchestrator
  发起 + 注入上下文         检查 A 输出 + 决策        检查 B 输出 + 决策
```

## 适用条件

- 任务有明确的阶段依赖（后一步依赖前一步的输出）
- 每个阶段可由不同 runtime 执行（如 codex 写代码、claude 审查）
- Orchestrator 需要在步骤之间做中间决策（如 review 通过才继续）

## 编排规则

1. Orchestrator 按顺序调用 `omp team run`，等待每步完成后再启动下一步
2. 前一步的 stdout 作为下一步 prompt 的上下文（直接嵌入或通过 `--prompt-file`）
3. 任何一步失败（退出码 != 0）则整个 pipeline 停止
4. Orchestrator 在步骤之间可以：
   - 检查输出质量，决定是否继续
   - 对输出做预处理/裁剪，再注入下一步
   - 根据输出内容动态调整下一步的 prompt

**示例：编码 -> 审查 pipeline**

```bash
# Step 1: codex 实现
OUTPUT=$(omp team run codex "实现 parse_config 函数..." --cwd /project)
if [ $? -ne 0 ]; then echo "Step 1 failed" >&2; exit 1; fi

# Orchestrator 中间决策：检查输出，构建 review prompt

# Step 2: claude 审查
REVIEW=$(omp team run claude "审查以下代码的质量：${OUTPUT}")
if [ $? -ne 0 ]; then echo "Step 2 failed" >&2; exit 1; fi
```

## 失败处理

| 退出码 | 含义 | 处理方式 |
|--------|------|---------|
| 0 | 成功 | 继续下一步 |
| 1 | 执行错误 | 检查 stderr 日志，修正 prompt 或换 runtime 重试 |
| 124 | 超时 | 增加 `--timeout`，或将任务拆分为更小的子任务 |

## 退出条件

- **成功**：所有步骤退出码 0，最终输出符合预期
- **失败**：任一步骤失败，orchestrator 决定是否重试或终止
- **重试策略**：orchestrator 可以用修正后的 prompt 重试失败步骤（最多 2 次）
