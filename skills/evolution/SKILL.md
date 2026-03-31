---
name: evolution
description: >-
  Evolve project skills and CLAUDE.md based on real usage data.
  Use when you want to audit and improve skills in the current project
  using cross-project session analysis, user feedback from memories,
  and rule consistency checks.
  Do NOT use for one-off skill fixes or new skill creation.
---

# Evolution

基于实证数据驱动项目 skills 和 CLAUDE.md 的持续演进。

## CLI

```bash
omp-evolution scan [--source <dir>] [--days <n>]
omp-evolution history [--limit <n>]
```

## 使用流程

<HARD-GATE>
每一步修改都必须经用户确认才执行。不允许批量自动修复。
</HARD-GATE>

### 阶段一：扫描

1. 运行 `omp-evolution scan`，获取机械信号 + session 样本
2. 读取 `references/evidence-sources.md`，理解数据含义
3. 读取 `references/mutation-operators.md`，理解算子映射
4. 对 session 样本做语义分析（误触发、重试、纠正）
5. 综合机械信号 + 语义分析，生成发现表格：

```
| # | 目标 | 类型 | 证据 | 建议算子 | 优先级 |
|---|------|------|------|---------|--------|
```

6. 呈现给用户，等待用户选择修复项

### 阶段二：修复（每条一个循环）

1. 用户选择一条 + 确认或覆盖算子
2. 记录基线 commit hash
3. 应用变异算子，生成修改
4. 呈现 diff，等待用户确认
5. 用户确认 → 运行 guard 检查（读取 `references/guard-checks.md`）
   - 机械 guard：`omp test skill <name>`
   - 语义 guard：对比修改前后 description 覆盖范围
6. guard 通过 → git commit，追加 results.tsv（status=keep）
7. guard 失败或用户拒绝 → git revert，追加 results.tsv（status=discard）
8. 回到发现表格，选下一条

### 阶段三：memory 收尾（所有修复完成后执行）

1. 运行 `omp-insight list --source .` 获取当前项目的 memory 列表
2. 读取 `references/memory-validity.md`，对照本轮修复内容逐条过三个 yes/no 问题
3. 生成候选删除表格，呈现给用户：

```
| # | memory ID | 摘要 | 失效类型 | 判断依据 |
|---|-----------|------|---------|---------|
```

4. 用户逐条确认 → `omp-insight delete <id>`
5. 拿不准 → 跳过，不删

**HARD-GATE 继承**：每条删除必须用户确认，禁止批量自动执行。

### results.tsv 追加格式

每次修复完成后追加一行（tab 分隔）：

```
date	commit	target	operator	status	description
```

文件路径：`~/.local/share/oh-my-superpowers/evolution/projects/<project>/results.tsv`

## 参考文档

| 场景 | 文档 |
|------|------|
| 数据源定义 | `references/evidence-sources.md` |
| 变异算子 + 证据映射 | `references/mutation-operators.md` |
| Guard 检查规则 | `references/guard-checks.md` |
| Memory 失效判断规则 | `references/memory-validity.md` |
