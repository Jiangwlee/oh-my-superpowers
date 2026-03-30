# Guard Checks

每次修复后、提交前执行。防止优化了一个维度但搞坏了基本合规性。

## 机械 Guard（阻断）

运行 `omp test skill <name>`，检查：

- SKILL.md frontmatter 合法（name、description 存在且格式正确）
- name 与目录名一致
- 引用的文件全部存在
- 无相对路径脚本调���（`bash scripts/`、`python scripts/`）

失败 → 必须修复后重新提交，或 discard 本次修改。

如果修改目标是 CLAUDE.md 而非 skill，跳过机械 guard。

## 语义 Guard（警告）

LLM 对比修改前后：

1. **description 覆盖范围**：修改后的 description 是否仍然准确覆盖所有预期触发场景？是否意外排除了合法场景？
2. **指令一致性**：修改后的内容是否与 SKILL.md 其他部分、references 中的内容矛盾？

语义 guard 不阻断流程。输出警告信息，由用户决定是否继续。

## 执行顺序

```
修改完成
  → 机械 guard（失败则停止）
  → 语义 guard（输出警告）
  → 用户最终确认
  → keep 或 discard
```
