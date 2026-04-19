# skill-review: {{skill-name}}

审查路径：`{{skill-dir}}`
审查范围：`{{review-scope}}`（SKILL.md + references/**/*.md 列表）
发现：{{X}} critical · {{Y}} warnings · {{Z}} suggestions
机械检查：完成 | 失败（原因：{{error}}）

---

## 汇总表

| 维度 | 名称                          | 状态    | 最高严重程度 | 问题数 |
|------|-------------------------------|---------|-------------|--------|
| A1   | Frontmatter & Directory Spec  | PASS / FINDING / N/A | — / WARNING / CRITICAL | 0 |
| A2   | File Reference Discipline     | PASS / FINDING / N/A | — | 0 |
| A3   | Skill Independence            | PASS / FINDING / N/A | — | 0 |
| A4   | Mechanical Consistency        | PASS / FINDING / N/A | — | 0 |
| A5   | Cross-File Consistency        | PASS / FINDING / N/A | — | 0 |
| B1   | Trigger Description Quality   | PASS / FINDING / N/A | — | 0 |
| B2   | Progressive Disclosure        | PASS / FINDING / N/A | — | 0 |
| B3   | Workflow Structure & Failure  | PASS / FINDING / N/A | — | 0 |
| B4   | Guardrails & Hard Constraints | PASS / FINDING / N/A | — | 0 |
| B5   | Script Interface Design       | PASS / FINDING / N/A | — | 0 |
| B6   | Output Contract Quality       | PASS / FINDING / N/A | — | 0 |
| B7   | Writing Quality               | PASS / FINDING / N/A | — | 0 |
| B8   | Expression Quality            | PASS / FINDING / N/A | — | 0 |
**N/A 条件**：B5 仅在 `scripts/` 存在时适用。

---

## 详情（按严重程度分组）

### CRITICAL

<!-- 无 CRITICAL 时写：无 -->

---

#### [CRITICAL] {{层}} / {{维度名}}

**标签**：SPEC | BEST_PRACTICE | PROJECT_POLICY

**文件**：{{source_file}}（SKILL.md / references/X.md / scripts/Y；跨文件冲突时列出所有相关文件）

**问题**：一句话精确描述。

**证据**：
```
直接引用文件原文、文件状态或脚本 JSON 输出
```

**影响**：一句话说明对执行、触发准确性或输出质量的影响。

**修复**：
```
具体的替换文本或操作步骤
```

**验证**：运行 `{{具体命令}}` 或检查 `{{具体文件状态}}`。

---

### WARNING

<!-- 无 WARNING 时写：无 -->

---

#### [WARNING] {{层}} / {{维度名}}

**标签**：SPEC | BEST_PRACTICE | PROJECT_POLICY

**文件**：{{source_file}}（SKILL.md / references/X.md / scripts/Y；跨文件冲突时列出所有相关文件）

**问题**：一句话精确描述。

**证据**：
```
直接引用文件原文、文件状态或脚本 JSON 输出
```

**影响**：一句话说明对执行、触发准确性或输出质量的影响。

**修复**：
```
具体的替换文本或操作步骤
```

**验证**：运行 `{{具体命令}}` 或检查 `{{具体文件状态}}`。

---

### SUGGESTION

<!-- 无 SUGGESTION 时写：无 -->

---

#### [SUGGESTION] {{层}} / {{维度名}}

**标签**：SPEC | BEST_PRACTICE | PROJECT_POLICY

**文件**：{{source_file}}（SKILL.md / references/X.md / scripts/Y；跨文件冲突时列出所有相关文件）

**问题**：一句话精确描述。

**证据**：
```
直接引用文件原文、文件状态或脚本 JSON 输出
```

**影响**：一句话说明对执行、触发准确性或输出质量的影响。

**修复**：
```
具体的替换文本或操作步骤
```

**验证**：运行 `{{具体命令}}` 或检查 `{{具体文件状态}}`。
