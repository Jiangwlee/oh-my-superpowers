# Skill Review Rubric

Purpose: 审查标准 + 执行清单。每个维度包含评审标准、可操作检查项和严重程度指引。
Input:   Step 2 语义审查阶段加载。
Output:  Reference only.
Sections: 审查对象 | Layer A | Layer B | Label Rules | Severity Guide

---

## Hard Gate

- **不得跳过**Checklist中的任何检查项，必须逐一执行

---

## 审查对象

审查范围覆盖 skill 目录下所有会在运行时被 agent 加载或执行的内容：

| 文件 | 加载时机 | 审查意义 |
|------|---------|---------|
| `SKILL.md` | 总是 | 主入口指令 |
| `references/**/*.md` | agent 按需增量加载 | 加载后等同 SKILL.md 的延伸指令 |
| `scripts/*` | CLI 被调用时 | docstring / help 文本进入 agent 上下文 |
| `assets/**` | 模板引用时 | 影响输出结构和格式 |

**核心含义**：references 里的一句话、一个命令示例、一条约束措辞，都可能被 agent 当作指令执行。不能假设"这条规则只写在 SKILL.md 里"——冲突可能出现在任意文件对之间，机械检查必须穿透到所有 `.md` 文件。

每条 finding 必须带 `source_file` 字段，标明问题出在哪个文件。

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
- [ ] `description` 的描述简单、准确，不暴露skill的实现细节、内部逻辑，不耦合其他skill.
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
- [ ] 所有 referenced 文件实际存在于磁盘
- [ ] 非总是需要的 reference 文件有明确加载条件说明（不无条件加载大文件）

证据来源：脚本输出（missing file / path-style 检查项）+ SKILL.md 原文。

**Severity**
- CRITICAL：路径错误或文件缺失导致运行时失败
- WARNING：引用风格不稳定 / 无条件加载大文件

---

### A3. Skill Independence

**Labels**：`SPEC` · `PROJECT_POLICY`

Skill 必须能独立触发和运行，不得在执行时依赖其他 skill。

**Checklist**

- [ ] 不使用 `@skills/...` 或 `@.../SKILL.md` force-load 语法引用其他 skill
- [ ] 正文不出现跨 skill 路径引用（`skills/<other>/...` 指向兄弟 skill 的文件/资源）
- [ ] 正文无执行性语义依赖：不写"先运行/使用/调用/配合 X skill"、"after running the Y skill"、"依赖 Z skill 产出的..." 等
- [ ] 不依赖其他 skill 产出的 artifact 作为启动前提（若存在此类耦合，应在 SKILL.md 输入规格里显式要求用户提供，而不是要求先跑另一个 skill）

**允许的例外**：
- `description` 中写触发边界（"Do NOT use for X — use Y instead"）是允许的，这是**路由指引**而非执行依赖
- 正文提及另一个 skill 的名字用于**对比/区分**（非链式调用）是允许的

证据来源：脚本输出（`force_load_syntax` / `cross_skill_references`）+ SKILL.md 正文语义扫描。

**Severity**
- CRITICAL：force-load 其他 skill / 执行依赖其他 skill 产出的 artifact
- WARNING：正文含语义链式调用指令 / 跨 skill 路径引用

---

### A4. Mechanical Consistency

**Labels**：`SPEC` · `PROJECT_POLICY`

**Checklist**

直接使用 Step 1 脚本输出（覆盖 SKILL.md + references/**/*.md），不重新发明以下检查：

- [ ] 参数不一致（任一文件代码块内 `--flag` 与 `--help` 不符，见 `parameter_mismatches.source_file`）
- [ ] 文件缺失（任一文件引用的 script/reference 不存在，见 `missing_files.source_file`）
- [ ] name 与目录不匹配（SKILL.md 专属）
- [ ] frontmatter 错误（SKILL.md 专属）
- [ ] description 超长（SKILL.md 专属）
- [ ] 孤立 reference（references 下存在但无任何文件引用，见 `orphaned_references`）
- [ ] scripts/*.py 注释代码块与 migration TODO（见 `scripts_legacy_pollution`）
- [ ] references/*.md HTML 注释中的 TODO/deprecated/legacy/migrate 标记（见 `md_legacy_markers`）

脚本无输出 → 此维度无 finding，不得凭空发明。

证据来源：脚本 JSON 输出，每条 finding 必须包含 `source_file`。

**Severity**
- CRITICAL：参数不一致 / 文件缺失导致运行时失败
- WARNING：name 不匹配 / 孤立 reference / stale 内容

---

### A5. Cross-File Consistency

**Labels**：`SPEC` · `PROJECT_POLICY`

skill 目录下所有受审文件之间不得存在冲突指令。因为 references 被 agent 按需加载后等同 SKILL.md 的延伸，冲突会让 agent 无法确定该遵循哪条。

**Checklist**

- [ ] 同一命令（`omp X Y` / `python scripts/...`）在不同文件中的参数组合一致，或差异有明确分工说明（见 `cross_file_command_variants`）
- [ ] 同一约束的语气一致：不得 SKILL.md 写"禁止 X"而 references 示范 X（如 SKILL.md 要求 `omp <skill>` 统一入口，references 却出现 `python scripts/foo.py` 直接调用 → `cli_violations` 中 `source_file != SKILL.md` 的每一条都要判断）
- [ ] Step 顺序、阶段划分、维度编号在 SKILL.md 与 references 之间一致（人工对照）
- [ ] Skill Independence（A3）硬约束在 references 中同样遵守——references 里出现的 `@skills/...` / 跨 skill 路径 / 语义依赖关键字，若非规则引文，视为违规

**允许的例外**：
- references 作为"规则说明/rubric"引用自身禁用模式（如 `` `@skills/...` `` 在 backticks 内作为反例演示）→ 标记为允许的引文，不报 finding
- references 作为"第三方教学文档外部引入"包含的命令示例 → 必须在该文件顶部以 frontmatter 或显著 note 标明"本文件为外部资料，示例仅供参考，实际调用以 SKILL.md 为准"；否则视为污染

证据来源：脚本输出（`cross_file_command_variants` / 各扫描器带 `source_file` 的条目）+ 人工语义对照。

**Severity**
- CRITICAL：不同文件间存在执行路径冲突（agent 按任一条都可能走错）
- WARNING：参数或措辞漂移但可推断真实意图；外部教学文档未加 note
- SUGGESTION：冗余重复或术语不统一

---

## Layer B: Design Quality

这一层回答：skill 的写法是否能让 agent 可靠、高效地完成任务？

**范围**：B1–B6 主要针对 SKILL.md（触发描述、主工作流、guardrails 等定义于此）；**B7 / B8 必须对每个受审文件（SKILL.md + references/**/*.md）独立评估**——references 里的死文档或表达瑕疵同样会污染 agent 决策。每条 finding 标注 `source_file`。

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

基础表达（违反 → WARNING，每条附建议改写）：

- [ ] 过度解释：SKILL是菜谱/说明书，而不是课本
- [ ] 不良措辞与废话：比如：`只解决一件事` 这种无意义的表达
- [ ] 无元评注：无 "本节介绍..." / "以下是关于 X 的..." / "值得注意的是..."
- [ ] 约束用硬语言：NO / NEVER / MUST / 禁止 / 不得；不用"尽量 / 建议 / try to / if possible / generally"
- [ ] 指令以祈使动词开头（运行 / 加载 / 检查）；不用被动语态或"你应该..."
- [ ] 同一约束只出现一次；相同规则不在不同位置以不同措辞重复
- [ ] 分支条件显式写出（"如果 X → Y；否则 → Z"）；不用"根据情况处理"
- [ ] 示例是可执行的真实值；不用占位符（`[your_value]` / `<target>`）；好/坏对比比单独好例子更有效
- [ ] 无自定义非标准分隔符（`===RULE===` / `---BLOCK---` 类语法）
- [ ] 编号列表 `1. 2.` 仅用于严格顺序步骤（换序会破坏含义）
- [ ] 无序列表 `-` 仅用于无顺序枚举（概念、选项、并列规则）
- [ ] Checkbox `- [ ]` 仅用于可勾选的完成项（待办、验证清单、审查条目），每项独立可判定（done / not done）
- [ ] 表格 `\| ... \|` 用于多维对比或属性映射（≥2 列信息）；Mermaid 用于流程拓扑（见 Pipeline 第 5 条）
- [ ] Checkbox 不用于纯信息展示（已有状态字段时改用表格或无序列表；`- [ ] <子问题>（状态：open|partial|answered）` 属反模式）
- [ ] Checkbox 不用于互斥分支（分支用"如果 X → Y；否则 → Z"显式写出）
- [ ] Checkbox 不嵌套勾选框（最多一层 `- [ ]`；子项改用普通 bullet 或折行描述）
- [ ] 同一 checklist 内句式统一：全部祈使（"检查 X"）/ 全部陈述（"X 存在"）/ 全部疑问（"X 是否成立？"）三选一，不混用

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
