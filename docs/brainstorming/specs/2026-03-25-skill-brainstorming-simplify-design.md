# skill-brainstorming 精简重构

> 将 skill-brainstorming 精简为"前置检验 + 移交 brainstorming"，只保留 skill-specific 的不可替代价值，其余交给 brainstorming 完成。

## 目录

- [设计方案](#设计方案)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 目标

当前 skill-brainstorming 有 7 个 Phase，大量工作与 brainstorming skill 重复。本次重构将其精简为"种子生成器"：只做 skill-specific 判断，然后移交 brainstorming 继续完整流程。

### 方案

skill-brainstorming 重构后只做三件事：

1. **加载 skill 知识** — 读取 `references/skill-fundamentals.md` 和 `references/design-patterns.md`
2. **Phase 0：真实能力检验** — 判断封装是否有价值；失败则终止并说明原因
3. **模式选择** — 从 5 种模式中推荐一个，给出理由，用户确认

检验通过、模式确认后，构造种子并移交 brainstorming：

```
我已完成 skill-brainstorming 前置检验，结果如下：
- 能力检验：通过。[一句话说明封装了什么真实能力]
- 选定模式：[模式名]。[一句话说明理由]
请基于以上上下文继续 brainstorming 流程。
```

brainstorming 接手后正常走完整流程（澄清问题 → 设计 → 文档 → 开发模式推荐）。

**移除的 Phase：**
- Phase 1 能力定义 → brainstorming 澄清阶段
- Phase 3 结构设计 → brainstorming 设计阶段
- Phase 4 CLI 化设计 → brainstorming 设计阶段
- Phase 5 触发边界设计 → brainstorming 设计阶段
- Phase 6 渐进式披露规划 → brainstorming 设计阶段
- Phase 7 规格生成 → brainstorming 输出文档
- writing-plans 调用 → 已废弃

**保留不动：** `references/` 和 `assets/` 目录（brainstorming 接手后仍需读取）

---

## 行动原则

- **Break, Don't Bend**：直接删除冗余 Phase，不做"兼容旧流程"的过渡层。
- **Minimum Blast Radius**：只改 SKILL.md，不动 references/ 和 assets/。

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 修改 | `skills/skill-brainstorming/SKILL.md` | 精简为 Phase 0 + 模式选择 + 移交逻辑 |

### 任务步骤

- [ ] 重写 SKILL.md：保留 Phase 0 完整逻辑（含失败情形）
- [ ] 保留模式选择逻辑（5种模式速查 + 模型主动推荐格式）
- [ ] 新增移交章节：种子格式 + 调用 brainstorming 的指令
- [ ] 删除 Phase 1/3/4/5/6/7 和 writing-plans 引用
- [ ] 更新文件头注释（Zero-Context Entry）
- [ ] 提交
