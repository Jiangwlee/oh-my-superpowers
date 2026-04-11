# Code and Review

> **DEPRECATED**: 编码编排场景已由独立 skill `coding-orchestrator` 承担，
> 提供完整的 task spec 体系、worker protocol 和 compaction recovery。
> 本文档保留作为 team 原语层的 pipeline 用法示例。

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

4. **并行任务的 Worktree 隔离**（仅限 git 仓库内的并行 coding 任务）：

   当多个 worker 需要并行修改同一仓库的文件时，必须为每个 worker 创建独立的 git worktree，避免并发写入冲突：

   ```bash
   # 检查是否在 git repo 中
   if git rev-parse --is-inside-work-tree &>/dev/null; then
     # 为每个并行 worker 创建独立 worktree + 分支
     git worktree add .worktrees/worker-1 -b team/worker-1
     git worktree add .worktrees/worker-3 -b team/worker-3
   fi
   ```

   - 通过 `--cwd .worktrees/worker-N` 将 worker 隔离到独立目录
   - 非 git 目录跳过此步骤，直接共享目录执行（可能有并发写入风险，orchestrator 应通过任务划分避免文件重叠）
   - 单个 worker 执行时不需要 worktree

5. 执行编码任务：

```bash
omp team run codex --prompt-file coding-task-1.md --cwd .worktrees/worker-1
```

6. 检查退出码：
   - `0` — 成功，收集 stdout 输出
   - `1` — 失败，记录 stderr 错误信息
   - `124` — 超时，考虑拆分任务或增加 timeout

### Phase 2.5: Worktree Merge（并行 coding 后）

若 Phase 2 使用了 worktree 隔离，编码完成后需要 merge 回主分支：

```bash
# 逐个 merge（先 merge 的优先）
git merge --no-ff team/worker-1
git merge --no-ff team/worker-3

# 如果 merge 冲突 → 报告给用户，不自动解决
# git merge --abort  # 回退冲突的 merge

# 清理 worktree + 分支
git worktree remove .worktrees/worker-1
git worktree remove .worktrees/worker-3
git branch -d team/worker-1 team/worker-3
```

- merge 冲突时停止后续 merge，将冲突文件列表报告给用户
- 任务划分时应尽量避免不同 worker 修改同一文件（worktree 是兜底安全网，不是主要依赖）

### Phase 3: Review

7. 构造 review prompt（使用 `prompts/code-review.md` 模板），包含：
   - 原始需求
   - Coder 的实际输出（修改了哪些文件、做了什么决策）
   - 相关代码 diff

7. 执行审查：

```bash
omp team run claude --prompt-file review-task.md
```

8. 解析 review 结果，关注 Verdict 字段：
   - `APPROVE` — 进入完成
   - `REQUEST_CHANGES` — 进入修复循环

### Phase 4: Verify-Fix 循环（如需）

9. Verify 方式（二选一或组合）：
   - **LLM Review**：解析 claude review 的 Verdict 字段（`APPROVE` / `REQUEST_CHANGES`）
   - **命令验证**：运行测试或类型检查（`pytest`、`tsc --noEmit`、`bash -n`），退出码 0 = 通过

10. 若 verify 未通过（CRITICAL/HIGH 问题或命令失败）：
    - 从 review 输出 / 命令 stderr 提取**具体 issue 列表**
    - 构造修复 prompt，**必须包含**上一轮的 issue 列表和对应文件路径
    - 回到 Phase 2 执行修复（单个 worker，不需要 worktree）
    - **最多 3 轮**修复循环

11. 退出条件：
    - `APPROVE` 或命令退出码 0 → 完成
    - 达到 3 轮仍有问题 → **停止循环**，汇总未解决 issue 报告给用户，由用户决定下一步

12. 若 review 通过 → 完成

## Prompt 模板引用

- 编码任务：`prompts/coding-task.md`
- 代码审查：`prompts/code-review.md`

## 示例编排序列

```
[Orchestrator] 收集上下文 + 划分 3 个任务（task-1 无依赖, task-2 依赖 task-1, task-3 无依赖）

[Orchestrator] 在 git repo 中创建 worktree:
  git worktree add .worktrees/worker-1 -b team/worker-1
  git worktree add .worktrees/worker-3 -b team/worker-3

[Orchestrator] 并行执行 task-1 和 task-3（隔离到各自 worktree）:
  omp team run codex --prompt-file task-1.md --output-file out-1.txt --cwd .worktrees/worker-1 &
  omp team run codex --prompt-file task-3.md --output-file out-3.txt --cwd .worktrees/worker-3 &
  wait

[Orchestrator] Merge worktree:
  git merge --no-ff team/worker-1
  git merge --no-ff team/worker-3
  git worktree remove .worktrees/worker-1 && git worktree remove .worktrees/worker-3

[Orchestrator] 检查退出码，task-1 成功 → 执行 task-2:
  omp team run codex --prompt-file task-2.md --output-file out-2.txt --cwd ./project

[Orchestrator] 构造 review prompt（包含 task-1/2/3 输出和 diff）:
  omp team run claude --prompt-file review-all.md --output-file review-out.txt

[Orchestrator] 解析 review → REQUEST_CHANGES (1 CRITICAL in task-2)

[Orchestrator] Verify-Fix 循环（轮次 1/3）:
  构造修复 prompt（包含 review 的 issue 列表）→ omp team run codex
  再次 review → APPROVE → 完成
```
