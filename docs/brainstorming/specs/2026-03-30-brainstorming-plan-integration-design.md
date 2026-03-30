# Brainstorming Plan 阶段集成

> 将 writing-plans skill 的核心约束吸收进 brainstorming，让 design doc 的行动计划章节达到可直接执行的质量，消除 design → 开发之间的断层。

## 目录

- [设计方案](#设计方案)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 背景与目标

brainstorming 第12步从 design doc 直接跳到"推荐开发模式"，缺少将粗粒度行动计划细化为可执行 plan 的阶段。writing-plans skill（来自 superpowers 生态）恰好补这个缺口，但作为独立 skill 需要用户手动调用。

目标：吸收 writing-plans 的核心约束，升级 design doc 行动计划章节的质量标准，一个文件完成 design + plan。

### 架构

不引入新文件或新模板。变更集中在4个已有文件：

1. **SKILL.md** — checklist 流程调整（第9步拆分、第12步简化）
2. **design-doc-template-normal.md** — 行动计划章节升级
3. **document-writing.md** — 增加 plan 撰写约束
4. **spec-document-reviewer-prompt.md** — 扩展 plan 审查维度

### 关键决策

- **不新增模板文件**：复用现有 design-doc-template，升级行动计划章节
- **不要求完整代码**：plan 粒度为接口签名 + 关键逻辑描述，避免重复劳动
- **单次审查**：spec-reviewer 扩展覆盖 plan，不引入第二个 reviewer
- **Execution Handoff 简化**：只给推荐语，不绑定具体 skill/工具
- **writing-plans 废弃**：不再作为独立 skill 使用，核心价值已吸收

---

## 行动原则

- **Break Don't Bend** — 正确的设计 > 兼容性。吸收就是吸收，不留 writing-plans 的调用路径。**禁止：** 保留对 superpowers 生态的任何引用
- **YAGNI** — 只吸收 writing-plans 中真正有价值的约束，不搬运整个 skill 的所有细节。**禁止：** 搬运 subagent-driven-development / executing-plans 相关内容
- **Zero-Context Entry** — plan 写出来后，任何 agent 拿到 design doc 就能执行，不需要回溯讨论历史。**禁止：** plan 中出现"如前所述"等回指表达

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 修改 | `skills/brainstorming/assets/design-doc-template-normal.md` | 行动计划章节升级 |
| 修改 | `skills/brainstorming/references/document-writing.md` | 增加 plan 撰写约束 |
| 修改 | `skills/brainstorming/SKILL.md` | checklist 第9-12步重构 |
| 修改 | `skills/brainstorming/spec-document-reviewer-prompt.md` | 扩展 plan 审查维度 |

### Task 1: 升级 design-doc-template-normal.md 行动计划章节

**Files:**
- 修改: `skills/brainstorming/assets/design-doc-template-normal.md`

- [ ] Step 1: 在行动计划章节前增加 Scope Check 指引
  - 注释说明：多子系统必须拆分为独立 plan，每个 plan 产出可独立测试的软件

- [ ] Step 2: 增加 File Structure 章节
  - 在"文件变更清单"前增加文件结构设计段
  - 要求先定文件边界和职责再定任务

- [ ] Step 3: 升级 Task 模板粒度
  - 每步标注预估 2-5 分钟
  - Step 3（实现）改为接口签名 + 关键逻辑描述，移除完整代码要求
  - 保留 TDD 循环结构（RED → GREEN → COMMIT）

### Task 2: 更新 document-writing.md 撰写约束

**Files:**
- 修改: `skills/brainstorming/references/document-writing.md`

- [ ] Step 1: 在 Structure 部分扩展行动计划的撰写标准
  - Scope Check：多子系统必须拆分
  - File Structure First：先定文件边界再定任务
  - 粒度约束：每步 2-5 分钟
  - 接口级描述：给出签名 + 关键逻辑，不要求完整代码

### Task 3: 重构 SKILL.md checklist 第9-12步

**Files:**
- 修改: `skills/brainstorming/SKILL.md`

- [ ] Step 1: 拆分第9步
  - 9a: Write design sections（设计方案 + 行动原则）
  - 9b: Write implementation plan（scope check → file structure → task 分解）
  - 合并写入同一个 design doc

- [ ] Step 2: 简化第12步
  - 移除"推荐开发模式"的详细选项
  - 改为推荐语："多模块/5+ tasks 建议 subagent 逐 task 执行；简单任务建议 inline 执行"

### Task 4: 扩展 spec-document-reviewer prompt

**Files:**
- 修改: `skills/brainstorming/spec-document-reviewer-prompt.md`

- [ ] Step 1: 在 What to Check 表格中增加 Plan 审查 section
  - Task Decomposition：任务边界清晰、步骤可执行
  - Buildability：agent 拿到文档能否直接执行
  - Spec-Plan Alignment：plan 覆盖设计方案的所有需求

- [ ] Step 2: 更新 Calibration 段
  - plan 中出现 placeholder 代码、缺失文件路径、步骤模糊到无法执行 → 都是 issue
