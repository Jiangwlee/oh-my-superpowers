# Memory 失效判断规则

evolution 阶段三的判断依据。对照本轮修复内容，逐条过以下三个问题，任一为 yes → 建议删除。拿不准 → 保留。

---

## 三类失效

| 类型 | 定义 |
|------|------|
| `fixed` | 记录的 bug / 错误行为已被代码修复 |
| `codified` | 记录的临时经验 / 约束已写入 SKILL.md 或规范文档 |
| `superseded` | 记录的决策已被新决策明确替代 |

---

## 判断流程（三个 yes/no 问题）

```
Q1. [fixed]      这条 memory 描述的 bug/错误行为，现在验证代码已正确实现？
Q2. [codified]   这条 memory 的核心规则，现在已在 SKILL.md 或文档中可 grep 到？
Q3. [superseded] 这条 memory 的决策前提，已被更新的 memory 或文档明确覆盖？
```

任一答案为 **yes** → 记录失效类型，列入候选删除表格，等待用户确认。  
全部 **no** 或拿不准 → 保留，不删。

---

## If-Then 检查逻辑

**fixed**
```
if 对应代码路径/函数已包含正确实现
  AND（可选）有测试或 SKILL.md 验证项覆盖
→ 标记 fixed，建议删除
```

**codified**
```
if grep <memory 核心关键词> <对应 SKILL.md 或 references/> 有结果
  AND 该文档是权威来源（不是另一条 memory）
→ 标记 codified，建议删除
```

**superseded**
```
if 存在更新的 memory（created_at 更晚）描述同一主题且结论不同
  OR 存在明确文档说明旧决策已作废
→ 标记 superseded，建议删除
```

---

## 默认保守原则

- **不删原则 1**：有效期不明确的架构原则、工作流偏好 → 保留
- **不删原则 2**：memory 描述的问题"理论上已修复"但没有验证 → 保留
- **不删原则 3**：两条 memory 部分重叠但各有侧重 → 保留，不因"相似"删除

---

## 正例 / 反例

**正例（建议删除）**

```
memory:  "bug: omp-insight capture --dry-run 跳过了整个 LLM 调用，没有输出"
类型:    fixed
依据:    cli.py:300-359 已在 dry_run=True 时执行 LLM 调用并打印结果，只跳过写入
结论:    ✅ 删除
```

```
memory:  "round-table 参与者必须遵从 roles.md 中的 runtime/model，不能全用 claude+sonnet"
类型:    codified
依据:    skills/round-table/SKILL.md 职责边界表已写入"禁止手动指定或覆盖 runtime/model"
结论:    ✅ 删除
```

**反例（保留）**

```
memory:  "Pi 是一等公民 LLM 后端，Claude 仅降级，必须 --no-session"
类型:    无（持续有效的架构原则）
依据:    这是跨 skill 的设计原则，不对应某个具体代码修复，未被任何文档取代
结论:    ❌ 保留
```

---

## `omp-insight list` 输出格式参考

```
## Memories

  [mem_19d3ec14edc_8d4ca6ab] (bug) conf=1.00 hits=0 | omp-evolution 命令未安装：CLI 入口存在但未安装到 PATH | tags: evolution, cli
  [mem_19d41c32342_322d3409] (workflow) conf=1.00 hits=0 | SKILL.md SOP 设计模式：职责边界表... | tags: sop-pattern
```

字段说明：`[<id>] (<kind>) conf=<置信度> hits=<召回次数> | <摘要> | tags: <标签>`
