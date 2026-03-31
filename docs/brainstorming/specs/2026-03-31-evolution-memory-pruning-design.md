# Evolution Memory Pruning: Phase 3 + memory-validity.md

在 evolution skill 中添加阶段三（memory 收尾），配套 `references/memory-validity.md` 提供三类失效判断规则，让 LLM 在每轮修复完成后系统性地识别并清理失效 memory。

## 目录

1. [设计方案](#设计方案)
2. [行动原则](#行动原则)
3. [行动计划](#行动计划)

---

## 设计方案

### 背景

Evolution skill 当前只操作 SKILL.md / CLAUDE.md，没有处理 memory 的机制。当一个 bug 被修复、一条规则被写入 SKILL.md 后，记录该 bug/规则的 memory 条目会永久留存，成为过期信息，干扰未来的 recall。

`omp-insight delete <id>` 已存在，缺的是触发删除的判断 SOP。

### 范围

| 交付物 | 说明 |
|--------|------|
| `references/memory-validity.md` | 三类失效定义 + if-then 检查逻辑（evolution skill 内） |
| evolution `SKILL.md` 阶段三 SOP | 修复完成后的 memory 收尾流程 |

**明确排除**：insight memory schema 加 `invalidation_trigger` 字段（留待未来）。

### 三类失效

| 类型 | 定义 | 判断问题 |
|------|------|---------|
| `fixed` | 记录的 bug / 错误行为已被代码修复 | 对应代码路径现在是否已正确实现？ |
| `codified` | 记录的临时经验 / 约束已写入 SKILL.md 或规范文档 | 对应规则现在是否已在权威文档中可查？ |
| `superseded` | 记录的决策已被新决策明确替代 | 是否存在更新的 memory / 文档覆盖此决策？ |

**默认保守原则**：任何一条 yes → 建议删除；拿不准 → 保留，不删。

### 阶段三 SOP（新增）

在现有阶段二（逐条修复）之后追加：

```
阶段三：memory 收尾

1. 列出本轮涉及的所有 skill 名称
2. 调用 omp-insight list --source . 获取 memory 列表
3. 读取 references/memory-validity.md，对照本轮修复内容逐条过三个 yes/no 问题
4. 生成候选删除表格，呈现给用户：

   | # | memory ID | 摘要 | 失效类型 | 判断依据 |

5. 用户逐条确认 → omp-insight delete <id>
6. 拿不准 → 跳过，不删
```

**HARD-GATE 继承**：每条删除必须用户确认，禁止批量自动执行。

### 未来演进方向（不在本次范围）

Alan Kay + Lamport 方案：在 insight memory schema 加可选 `invalidation_trigger` 字段（结构化 shell 断言），capture 时 LLM 写入，阶段三优先机械执行。这需要改动 insight capture 逻辑，单独立项。

---

## 行动原则

1. **TDD** — SKILL.md 修改后验证 T1 静态检查（`omp test skill evolution`）
2. **Break, Don't Bend** — 不加"insight 未安装则跳过"的兼容分支
3. **Zero-Context Entry** — `memory-validity.md` 第一屏无需上下文即可理解三类判断
4. **Minimum Blast Radius** — 只改 evolution skill，不碰 insight

---

## 行动计划

### 文件结构

```
.claude/skills/evolution/
├── SKILL.md                          # [修改] 追加阶段三 SOP
└── references/
    ├── memory-validity.md            # [新建] 三类失效 + if-then 检查逻辑
    ├── evidence-sources.md           # 不变
    ├── mutation-operators.md         # 不变
    └── guard-checks.md               # 不变
```

### Task 1 — 新建 `references/memory-validity.md`

**文件职责**：三类失效的定义、判断问题、if-then 检查逻辑、正反例。不超过一屏。

**内容结构**：
```
# Memory 失效判断规则

## 三类失效

fixed / codified / superseded 的定义各 2-3 行

## 判断流程

三个 yes/no 问题（对应三类），任一 yes → 建议删除

## If-Then 检查逻辑

- fixed: if 对应代码路径/测试/SKILL.md 已覆盖 → delete
- codified: if 对应规则在 SKILL.md 可 grep 到 → delete
- superseded: if 有更新 memory/文档覆盖此决策 → delete

## 默认保守

拿不准 → 保留。不要为了"清理感"删除模糊条目。

## 正例 / 反例

各一条，说明什么情况删、什么情况不删
```

### Task 2 — 修改 `SKILL.md`：追加阶段三

在现有"阶段二：修复"之后，追加"阶段三：memory 收尾"段落：

- 步骤 1：`omp-insight list --source .` 获取 memory 列表
- 步骤 2：读 `references/memory-validity.md`，对照本轮修复逐条判断
- 步骤 3：生成候选删除表格（id / 摘要 / 失效类型 / 依据）
- 步骤 4：用户确认每条 → `omp-insight delete <id>`
- 步骤 5：跳过拿不准的条目

同时更新 `references/` 索引表（在 SKILL.md 末尾）加入 `memory-validity.md` 条目。

### Task 3 — T1 验证

运行 `omp test skill evolution`，确认：
- `references/memory-validity.md` 存在
- SKILL.md 包含"阶段三"关键词
- SKILL.md 无相对路径脚本调用
