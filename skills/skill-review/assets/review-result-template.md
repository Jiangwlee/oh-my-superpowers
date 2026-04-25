# skill-review: {{skill-name}}

审查路径：`{{skill-dir}}`
审查范围：`{{review-scope}}`
机械检查：完成 | 失败（原因：{{error}}）
findings：{{X}} CRITICAL · {{Y}} WARNING · {{Z}} SUGGESTION

> **本文件是 scaffold 模板。** Agent 不直接编辑这份模板——通过 `omp skill-review emit-checklist` 生成实例文件后填写。规则：
> - 每条 checkbox 必须勾选为 `[✓]`、`[✗]` 或 `[—]`，不得保留 `[ ]`
> - 每条必须替换 `__STATE__` 与 `__EVIDENCE__` 占位符
> - 仅 `[✗]` 行必须展开 4 个内联子项：标签 / 影响 / 修复 / 验证
> - 不得保留任何 `{{...}}` 模板变量

---

## 机械检查 JSON

<details>
<summary>consistency_check 原始输出</summary>

```json
{{consistency_check_json}}
```

</details>

---

## 审查结果

### A1. Frontmatter and Directory Spec — __STATE__

- [ ] `SKILL.md` 存在，有有效的开闭 `---` 界定符 → __STATE__ · __EVIDENCE__
- [ ] `name` 与父目录名一致 → __STATE__ · __EVIDENCE__
- [ ] `name` 格式合规：1-64 字符，小写字母+数字+连字符，无前后缀或连续连字符 → __STATE__ · __EVIDENCE__
- [ ] `description` 非空，≤ 1024 字符 → __STATE__ · __EVIDENCE__
- [ ] `description` 的描述简单、准确，不暴露 skill 的实现细节、内部逻辑，不耦合其他 skill → __STATE__ · __EVIDENCE__
- [ ] 可选字段（`license` / `compatibility` / `metadata` / `allowed-tools`）若存在则结构合法 → __STATE__ · __EVIDENCE__

### A2. File Reference Discipline — __STATE__

- [ ] 不使用 `$SKILL_DIR` 等路径变量调用脚本 → __STATE__ · __EVIDENCE__
- [ ] 所有 referenced 文件实际存在于磁盘 → __STATE__ · __EVIDENCE__
- [ ] 非总是需要的 reference 文件有明确加载条件说明（不无条件加载大文件）→ __STATE__ · __EVIDENCE__

### A3. Skill Independence — __STATE__

- [ ] 不使用 `@skills/...` 或 `@.../SKILL.md` force-load 语法引用其他 skill → __STATE__ · __EVIDENCE__
- [ ] 正文不出现跨 skill 路径引用（`skills/<other>/...` 指向兄弟 skill 的文件/资源）→ __STATE__ · __EVIDENCE__
- [ ] 正文无执行性语义依赖："先运行/使用/调用/配合 X skill"、"after running the Y skill" 等 → __STATE__ · __EVIDENCE__
- [ ] 不依赖其他 skill 产出的 artifact 作为启动前提 → __STATE__ · __EVIDENCE__

### A4. Mechanical Consistency — __STATE__

- [ ] 参数不一致（`parameter_mismatches`）→ __STATE__ · __EVIDENCE__
- [ ] 文件缺失（`missing_files`）→ __STATE__ · __EVIDENCE__
- [ ] name 与目录不匹配 → __STATE__ · __EVIDENCE__
- [ ] frontmatter 错误（`frontmatter_warnings`）→ __STATE__ · __EVIDENCE__
- [ ] description 超长 → __STATE__ · __EVIDENCE__
- [ ] 孤立 reference（`orphaned_references`）→ __STATE__ · __EVIDENCE__
- [ ] scripts/*.py 注释代码块与 migration TODO（`scripts_legacy_pollution`）→ __STATE__ · __EVIDENCE__
- [ ] references/*.md HTML 注释中的 TODO/deprecated/legacy/migrate 标记（`md_legacy_markers`）→ __STATE__ · __EVIDENCE__

### A5. Cross-File Consistency — __STATE__

- [ ] 同一命令在不同文件中的参数组合一致（`cross_file_command_variants`）→ __STATE__ · __EVIDENCE__
- [ ] 同一约束语气一致：SKILL.md 与 references 不互相违反（`cli_violations` 中 `source_file != SKILL.md` 的条目）→ __STATE__ · __EVIDENCE__
- [ ] Step 顺序、阶段划分、维度编号在 SKILL.md 与 references 之间一致 → __STATE__ · __EVIDENCE__
- [ ] Skill Independence 约束在 references 中同样遵守 → __STATE__ · __EVIDENCE__

### B1. Trigger Description Quality — __STATE__

- [ ] description 使用命令式意图框架（"Use when..." 或等价表达）→ __STATE__ · __EVIDENCE__
- [ ] 触发条件聚焦用户意图/场景，不是 skill 内部工作流摘要 → __STATE__ · __EVIDENCE__
- [ ] 包含间接场景覆盖：用户未显式提及 skill 名称时也能触发 → __STATE__ · __EVIDENCE__
- [ ] 有近似负例边界：说明哪些相似场景不应触发 → __STATE__ · __EVIDENCE__

### B2. Progressive Disclosure and Context Cost — __STATE__

- [ ] SKILL.md 只含每次运行都需要的核心流程和约束 → __STATE__ · __EVIDENCE__
- [ ] 分支细节、长规则、模式差异在 references/ 而非 inline → __STATE__ · __EVIDENCE__
- [ ] 每个 reference 文件有明确加载条件 → __STATE__ · __EVIDENCE__
- [ ] 无 `@path` force-load 语法 → __STATE__ · __EVIDENCE__
- [ ] 长示例和参考材料在 references/ 或 assets/，不在 SKILL.md inline → __STATE__ · __EVIDENCE__
- [ ] 一句话能说清 → inline；需要多段 → 放 references/ → __STATE__ · __EVIDENCE__

### B3. Workflow Structure and Failure Handling — __STATE__

- [ ] 多步骤任务有明确执行顺序 → __STATE__ · __EVIDENCE__
- [ ] 有明确的完成标准（Done when: [可验证状态]）→ __STATE__ · __EVIDENCE__
- [ ] 每个可能失败点有对应处理（不是统一兜底）→ __STATE__ · __EVIDENCE__
- [ ] 任务范围内聚，不是不相关任务的菜单 → __STATE__ · __EVIDENCE__

### B4. Guardrails and Hard Constraints — __STATE__

- [ ] 主要失败模式有显式说明 → __STATE__ · __EVIDENCE__
- [ ] 关键约束使用强指令语言（禁止 / 不得 / 必须 / NO / NEVER / MUST）→ __STATE__ · __EVIDENCE__
- [ ] 硬约束不埋在软性描述文字里 → __STATE__ · __EVIDENCE__
- [ ] 正面锚定与负面禁止并存 → __STATE__ · __EVIDENCE__

### B5. Script Interface Design — __STATE__

- [ ] `cli/<skill-name>/main.py` 存在且是唯一 CLI 入口 → __STATE__ · __EVIDENCE__
- [ ] SKILL.md 调用方式是 `omp <skill-name> [args]`，不含 `bash scripts/` 或 `python scripts/` → __STATE__ · __EVIDENCE__
- [ ] 无绕过 CLI 直接调用的独立脚本 → __STATE__ · __EVIDENCE__
- [ ] CLI 用法与实际 `omp <skill-name> --help` 输出一致 → __STATE__ · __EVIDENCE__
- [ ] CLI 前置条件（runtime 版本 / PATH 要求）有说明 → __STATE__ · __EVIDENCE__
- [ ] 复杂 shell 逻辑在 CLI 内部实现，不 inline 在 SKILL.md → __STATE__ · __EVIDENCE__

### B6. Output Contract Quality — __STATE__

- [ ] 期望输出形态清晰（格式、结构、内容范围）→ __STATE__ · __EVIDENCE__
- [ ] 若有严格模板，SKILL.md 中有明确引用（`assets/` 路径）→ __STATE__ · __EVIDENCE__
- [ ] 灵活输出仍有合理默认值说明 → __STATE__ · __EVIDENCE__
- [ ] 非显而易见的输出有示例 → __STATE__ · __EVIDENCE__

### B7. Writing Quality and Dead Documentation — __STATE__

- [ ] 使用精确动词（检查 / 禁止 / 加载 / 运行）→ __STATE__ · __EVIDENCE__
- [ ] 措辞自包含，无需上下文才能理解 → __STATE__ · __EVIDENCE__
- [ ] 无迁移注释或兼容性说明（"previously..." / "TODO: migrate..."）→ __STATE__ · __EVIDENCE__
- [ ] 无已失效的工作流分支或 reference → __STATE__ · __EVIDENCE__

### B8. Expression Quality — __STATE__

- [ ] 无过度解释：SKILL 是菜谱/说明书，不是课本 → __STATE__ · __EVIDENCE__
- [ ] 无不良措辞与废话（如"只解决一件事"类无意义表达）→ __STATE__ · __EVIDENCE__
- [ ] 无元评注（"本节介绍..."、"以下是关于 X 的..."、"值得注意的是..."）→ __STATE__ · __EVIDENCE__
- [ ] 约束用硬语言：NO / NEVER / MUST / 禁止 / 不得；不用"尽量 / 建议 / try to / if possible / generally" → __STATE__ · __EVIDENCE__
- [ ] 指令以祈使动词开头（运行 / 加载 / 检查）；不用被动语态或"你应该..." → __STATE__ · __EVIDENCE__
- [ ] 同一约束只出现一次；相同规则不在不同位置以不同措辞重复 → __STATE__ · __EVIDENCE__
- [ ] 分支条件显式写出（"如果 X → Y；否则 → Z"）；不用"根据情况处理" → __STATE__ · __EVIDENCE__
- [ ] 示例是可执行的真实值；不用占位符；好/坏对比比单独好例子更有效 → __STATE__ · __EVIDENCE__
- [ ] 无自定义非标准分隔符（`===RULE===` / `---BLOCK---` 类语法）→ __STATE__ · __EVIDENCE__
- [ ] 编号列表 `1. 2.` 仅用于严格顺序步骤 → __STATE__ · __EVIDENCE__
- [ ] 无序列表 `-` 仅用于无顺序枚举 → __STATE__ · __EVIDENCE__
- [ ] Checkbox `- [ ]` 仅用于可勾选完成项，每项独立可判定 → __STATE__ · __EVIDENCE__
- [ ] 表格用于多维对比或属性映射，Mermaid 用于流程拓扑 → __STATE__ · __EVIDENCE__
- [ ] Checkbox 不用于纯信息展示 → __STATE__ · __EVIDENCE__
- [ ] Checkbox 不用于互斥分支 → __STATE__ · __EVIDENCE__
- [ ] Checkbox 不嵌套 → __STATE__ · __EVIDENCE__
- [ ] 同一 checklist 内句式统一 → __STATE__ · __EVIDENCE__
- [ ] 控制转移显式写出（"完成 Step N 后，加载 X，从其 Step 1 执行"）→ __STATE__ · __EVIDENCE__
- [ ] 跨文件流程使用不同命名层级（如 SKILL.md 用 Phase，scenario 用 Step）→ __STATE__ · __EVIDENCE__
- [ ] 每个步骤有可验证的完成条件（"Done when: [状态]"）→ __STATE__ · __EVIDENCE__
- [ ] 所有术语在首次使用时定义 → __STATE__ · __EVIDENCE__
- [ ] 有 3+ 分支或跨文件控制转移的 workflow → 用 Mermaid flowchart → __STATE__ · __EVIDENCE__

---

## 填写示例

下面展示一条 `[✗]` 行如何展开。**实例报告中**所有占位符都必须替换。

```markdown
### A1. Frontmatter and Directory Spec — FINDING

- [✓] SKILL.md 存在，有有效的开闭 `---` 界定符 → consistency_check 无 frontmatter 错误
- [✓] name 与父目录名一致 → name_mismatch == null
- [✗] description 非空，≤ 1024 字符 → 实际 1287 字符
  - **标签**: SPEC
  - **影响**: description 超长可能被截断，影响触发命中
  - **修复**: 删除 description 中的 "## Workflow" 段落引用
  - **验证**: `omp skill-review check --skill-dir <path>` 重跑，frontmatter_warnings 为空
- [—] 可选字段 → 未使用 license / metadata 字段
```
