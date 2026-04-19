# Skill Review Rubric

Purpose: 审查标准 + 执行清单。每个维度包含评审标准、可操作检查项和严重程度指引。
Input:   Step 2 语义审查阶段加载。
Output:  Reference only.
Sections: Layer A | Layer B | Layer C | Label Rules | Severity Guide

---

## Layer A: Spec Compliance

这一层回答：skill 是否符合 Agent Skills 规范和路径级执行规则？

### A1. Frontmatter and Directory Spec

**Labels**：`SPEC`

**Checklist**

- [ ] `SKILL.md` 存在，有有效的开闭 `---` 界定符
- [ ] `name` 与父目录名一致
- [ ] `name` 格式合规：1-64 字符，小写字母+数字+连字符，无前后缀或连续连字符
- [ ] `description` 非空，≤ 1024 字符
- [ ] 可选字段（`license` / `compatibility` / `metadata` / `allowed-tools`）若存在则结构合法

证据来源：脚本输出（frontmatter 检查项）+ 文件系统状态。优先使用脚本输出。

**Severity**
- CRITICAL：frontmatter 格式错误 / `name` 不合法 / `description` 缺失
- WARNING：可选字段误用但不阻断激活

---

### A2. File Reference Discipline

**Labels**：`SPEC` · `BEST_PRACTICE`

**Checklist**

- [ ] 不使用 `$SKILL_DIR` 等路径变量调用脚本
- [ ] 不使用 `@skills/...` force-load 语法引用其他 skill
- [ ] 所有 referenced 文件实际存在于磁盘
- [ ] 非总是需要的 reference 文件有明确加载条件说明（不无条件加载大文件）

证据来源：脚本输出（missing file / force-load / path-style 检查项）+ SKILL.md 原文。

**Severity**
- CRITICAL：路径错误或文件缺失导致运行时失败
- WARNING：引用风格不稳定 / 无条件加载大文件

---

### A3. Mechanical Consistency

**Labels**：`SPEC` · `PROJECT_POLICY`

**Checklist**

直接使用 Step 1 脚本输出，不重新发明以下检查：

- [ ] 参数不一致（`--flag` 在 SKILL.md 有但 `--help` 无）
- [ ] 文件缺失
- [ ] name 与目录不匹配
- [ ] frontmatter 错误
- [ ] description 超长
- [ ] 孤立 reference（文件存在但未被引用）
- [ ] legacy 污染（注释代码块 / migration TODO）

脚本无输出 → 此维度无 finding，不得凭空发明。

证据来源：脚本 JSON 输出。

**Severity**
- CRITICAL：参数不一致
- WARNING：文件缺失 / name 不匹配 / 孤立 reference / stale 内容

---

## Layer B: Design Quality

这一层回答：skill 的写法是否能让 agent 可靠、高效地完成任务？

### B1. Trigger Description Quality

**Labels**：`BEST_PRACTICE` · `PROJECT_POLICY`

**Checklist**

- [ ] description 使用命令式意图框架（"Use when..." 或等价表达），而非被动描述"This skill does..."
- [ ] 触发条件聚焦用户意图/场景，不是 skill 内部工作流的摘要
- [ ] 包含间接场景覆盖：即用户未显式提及 skill 名称时也能触发
- [ ] 有近似负例边界：说明哪些相似场景不应触发（与相邻 skill 的边界）

如发现 FINDING → 加载 `references/how-to-optimize-skill-descriptions.md`。

证据来源：frontmatter description 原文。

**Severity**
- CRITICAL：description 过窄或格式错误导致触发大概率失败
- WARNING：description 模糊 / 过宽 / 可能误触发

---

### B2. Progressive Disclosure and Context Cost

**Labels**：`BEST_PRACTICE` · `PROJECT_POLICY`

**Checklist**

- [ ] SKILL.md 只含每次运行都需要的核心流程和约束
- [ ] 分支细节、长规则、模式差异在 references/ 而非 inline
- [ ] 每个 reference 文件有明确加载条件（什么情况下加载）
- [ ] 无 `@path` force-load 语法
- [ ] 长示例和参考材料在 references/ 或 assets/，不在 SKILL.md inline
- [ ] 判断原则：一句话能说清 → inline；需要多段 → 放 references/

如发现 FINDING → 加载 `references/agent-skills-best-practices.md`。

证据来源：SKILL.md 行数 + 有无多段 inline 规则。

**Severity**
- WARNING：SKILL.md 含详细分支逻辑 / 多段操作规则 / 模式差异说明
- WARNING：references 无加载条件（总是全量加载）
- SUGGESTION：结构可行但可以更紧凑

---

### B3. Workflow Structure and Failure Handling

**Labels**：`BEST_PRACTICE` · `PROJECT_POLICY`

**Checklist**

- [ ] 多步骤任务有明确执行顺序
- [ ] 有明确的完成标准（Done when: [可验证状态]）
- [ ] 每个可能失败点有对应处理（不是统一兜底）
- [ ] 任务范围内聚，不是不相关任务的菜单

证据来源：SKILL.md Workflow 和 Failure Handling 段落。

**Severity**
- WARNING：缺完成标准或失败处理，影响可靠性
- SUGGESTION：流程可用但难以跟踪

---

### B4. Guardrails and Hard Constraints

**Labels**：`BEST_PRACTICE` · `PROJECT_POLICY`

**Checklist**

- [ ] 主要失败模式有显式说明
- [ ] 关键约束使用强指令语言（禁止 / 不得 / 必须 / NO / NEVER / MUST）
- [ ] 硬约束不埋在软性描述文字里
- [ ] 正面锚定（应该做什么）与负面禁止（不得做什么）并存

证据来源：SKILL.md Guardrails 段落 + 全文约束语言扫描。

**Severity**
- CRITICAL：脆弱的工作流依赖软性或可选语言
- WARNING：guardrails 存在但过于泛泛或语气过弱

---

### B5. Script Interface Design

**Labels**：`BEST_PRACTICE` · `PROJECT_POLICY`

**仅在 `scripts/` 目录存在时检查；否则标记 N/A。**

**Checklist**

硬约束（PROJECT_POLICY，违反即 CRITICAL）：
- [ ] `cli/<skill-name>/main.py` 存在且是唯一 CLI 入口
- [ ] SKILL.md 调用方式是 `omp <skill-name> [args]`，不含 `bash scripts/` 或 `python scripts/`
- [ ] 无绕过 CLI 直接调用的独立脚本

设计质量（BEST_PRACTICE）：
- [ ] CLI 用法与实际 `omp <skill-name> --help` 输出一致
- [ ] CLI 前置条件（runtime 版本 / PATH 要求）有说明
- [ ] 复杂 shell 逻辑在 CLI 内部实现，不 inline 在 SKILL.md

如发现 FINDING → 加载 `references/how-to-use-scripts-in-skills.md`。

证据来源：脚本输出（parameter mismatch）+ SKILL.md 调用方式原文 + `cli/` 目录状态。

**Severity**
- CRITICAL：`scripts/` 存在但 `cli/<skill-name>/main.py` 不存在
- CRITICAL：SKILL.md 通过相对路径调用脚本（`bash scripts/` 或 `python scripts/`）
- CRITICAL：存在多个 CLI 入口
- WARNING：CLI 用法与 `--help` 不一致 / 前置条件未说明
- SUGGESTION：脚本用法正确但未充分利用 CLI 封装

---

### B6. Output Contract Quality

**Labels**：`BEST_PRACTICE` · `PROJECT_POLICY`

**Checklist**

- [ ] 期望输出形态清晰（格式、结构、内容范围）
- [ ] 若有严格模板，SKILL.md 中有明确引用（`assets/` 路径）
- [ ] 灵活输出仍有合理默认值说明
- [ ] 非显而易见的输出有示例

证据来源：SKILL.md Output 说明段 + `assets/` 目录状态。

**Severity**
- WARNING：结构化任务的输出约定未明确
- SUGGESTION：输出指引存在但缺少打磨

---

### B7. Writing Quality and Dead Documentation

**Labels**：`BEST_PRACTICE` · `PROJECT_POLICY`

**Checklist**

- [ ] 使用精确动词（检查 / 禁止 / 加载 / 运行）
- [ ] 措辞自包含，无需上下文才能理解
- [ ] 无迁移注释或兼容性说明（"previously..." / "TODO: migrate..."）
- [ ] 无已失效的工作流分支或 reference

以脚本输出（legacy pollution）为锚点，再做语义扫描；无脚本证据则不报告 finding。

证据来源：脚本输出（legacy pollution）+ 全文扫描过时内容。

**Severity**
- WARNING：死文档或有害可靠性的措辞
- SUGGESTION：动词精确度问题

---

### B8. Expression Quality

**Labels**：`BEST_PRACTICE` · `PROJECT_POLICY`

**Checklist**

基础表达（8 条，违反 → WARNING，每条附建议改写）：

- [ ] 无元评注：无 "本节介绍..." / "以下是关于 X 的..." / "值得注意的是..."
- [ ] 约束用硬语言：NO / NEVER / MUST / 禁止 / 不得；不用"尽量 / 建议 / try to / if possible / generally"
- [ ] 指令以祈使动词开头（运行 / 加载 / 检查）；不用被动语态或"你应该..."
- [ ] 同一约束只出现一次；相同规则不在不同位置以不同措辞重复
- [ ] 分支条件显式写出（"如果 X → Y；否则 → Z"）；不用"根据情况处理"
- [ ] 示例是可执行的真实值；不用占位符（`[your_value]` / `<target>`）；好/坏对比比单独好例子更有效
- [ ] 无自定义非标准分隔符（`===RULE===` / `---BLOCK---` 类语法）
- [ ] 对比信息用表格；顺序步骤用编号列表；不用散文段落混列多项

Pipeline/Workflow 表达（5 条，违反 → SUGGESTION，视 workflow 复杂度）：

- [ ] 控制转移显式写出（"完成 Step N 后，加载 X，从其 Step 1 执行"）；不用 `↓` / "branch into" / "see X"
- [ ] 跨文件流程使用不同命名层级（如 SKILL.md 用 Phase，scenario 用 Step），避免同一 session 内编号歧义
- [ ] 每个步骤有可验证的完成条件（"Done when: [状态]"）
- [ ] 所有术语在首次使用时定义；无未定义直接使用的概念
- [ ] 有 3+ 分支或跨文件控制转移的 workflow → 用 Mermaid flowchart；节点名对应文档中的 `## Step N` 标题；简单线性流程（≤5步无分支）用编号列表即可

证据来源：SKILL.md 全文扫描。

**Severity**
- WARNING：基础表达 1-8 条
- SUGGESTION：Pipeline 表达 9-13 条

---

## Label Rules

- `SPEC`：问题依据 Agent Skills 官方规范或严格格式要求。
- `BEST_PRACTICE`：来自参考文档集的通用设计指导。
- `PROJECT_POLICY`：仓库特定风格、更严格约定或部署期望。
- 一个 finding 可以有多个标签。
- 不得把纯项目偏好标记为 `SPEC`。

## Severity Guide

| 级别 | 定义 |
|------|------|
| `[CRITICAL]` | skill 将无法正确执行、无法正确触发，或可能将 agent 引入错误路径。 |
| `[WARNING]` | skill 大概率能工作，但可靠性、输出质量、可维护性或证据质量明显下降。 |
| `[SUGGESTION]` | skill 正常工作，但有可辩护的清晰度、效率或校准改进空间。 |
