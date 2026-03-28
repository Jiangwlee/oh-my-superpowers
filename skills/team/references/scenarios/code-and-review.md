# Code and Review

> pattern: pipeline
> 编码与代码评审循环。Orchestrator 构建上下文、划分任务、编排编码和 review。

## 参与者配置

- **Coder**: codex (默认) 或 pi — 负责编码实现
- **Reviewer**: claude — 负责代码审查

## 编排流程

### Phase 1: 准备

1. Orchestrator 收集上下文（项目结构、相关代码、设计文档、需求）
2. 划分任务，确定依赖顺序（无依赖的任务可并行）
3. 为每个任务准备 prompt（使用 `prompts/coding-task.md` 模板）

### Phase 2: 编码

4. 执行编码任务：

```bash
omp-team run codex --prompt-file coding-task-1.md --cwd ./project
```

5. 检查退出码：
   - `0` — 成功，收集 stdout 输出
   - `1` — 失败，记录 stderr 错误信息
   - `124` — 超时，考虑拆分任务或增加 timeout

### Phase 3: Review

6. 构造 review prompt（使用 `prompts/code-review.md` 模板），包含：
   - 原始需求
   - Coder 的实际输出（修改了哪些文件、做了什么决策）
   - 相关代码 diff

7. 执行审查：

```bash
omp-team run claude --prompt-file review-task.md
```

8. 解析 review 结果，关注 Verdict 字段：
   - `APPROVE` — 进入完成
   - `REQUEST_CHANGES` — 进入修复循环

### Phase 4: 修复循环（如需）

9. 若 review 有 CRITICAL/HIGH 问题：
   - 从 review 输出提取具体 issue 列表
   - 构造修复 prompt，明确列出要修复的问题和对应文件
   - 回到 Phase 2 执行修复

10. 若 review 通过 → 完成

## Prompt 模板引用

- 编码任务：`prompts/coding-task.md`
- 代码审查：`prompts/code-review.md`

## 完成判定

- Review 无 CRITICAL/HIGH 问题（Verdict = APPROVE）
- 或达到最大修复轮次（orchestrator 决定，建议 ≤ 3 轮）
- 达到最大轮次仍有问题时，orchestrator 应汇总未解决 issue 报告给用户

## 示例编排序列

```
[Orchestrator] 收集上下文 + 划分 3 个任务（task-1 无依赖, task-2 依赖 task-1, task-3 无依赖）

[Orchestrator] 并行执行 task-1 和 task-3:
  omp-team run codex --prompt-file task-1.md --output-file out-1.txt --cwd ./project &
  omp-team run codex --prompt-file task-3.md --output-file out-3.txt --cwd ./project &
  wait

[Orchestrator] 检查退出码，task-1 成功 → 执行 task-2:
  omp-team run codex --prompt-file task-2.md --output-file out-2.txt --cwd ./project

[Orchestrator] 构造 review prompt（包含 task-1/2/3 输出和 diff）:
  omp-team run claude --prompt-file review-all.md --output-file review-out.txt

[Orchestrator] 解析 review → REQUEST_CHANGES (1 CRITICAL in task-2)
[Orchestrator] 构造修复 prompt → 回到 Phase 2（仅 task-2）
[Orchestrator] 第二轮 review → APPROVE → 完成
```
