# Self-Check — 生成后自查清单

Purpose: 起草者在派独立 reviewer 之前，先自查一遍草稿。逐项勾选；任一未过先修，再进入独立评审。
Sections: 结构 | 表达 | 触发 | 自包含

起草完成后，对照下列每项。未过即修。

## 结构

- [ ] `name` 与目录名一致，小写连字符。
- [ ] SKILL.md 有 frontmatter + 标题下的 `Purpose / Input / Output / Sections` summary 段。
- [ ] SKILL.md 是骨架（Hard Gate + Workflow + References 指针），body < 500 行。
- [ ] 每个有序步骤都有可检验的 Done 判据。
- [ ] 分支逻辑、长规则、详细示例已下沉 `references/`；references 从 SKILL.md 一层深。
- [ ] 归入了明确的模式（Tool Wrapper / Generator / Reviewer / Inversion / Pipeline 或组合）。
- [ ] 无 tests 在 skill 目录内。

## 表达

- [ ] 正文祈使句、强动词；硬约束用硬词。
- [ ] 无元评论（`本节介绍…`）、无空话（`酌情`、`just`、`simply`）、无未解释黑话。
- [ ] 隐藏分支已显式化（`若 X → Y；否则 → Z`）。
- [ ] 命令与示例用真实值，不用占位符。
- [ ] 同一含义只在一处（无 duplication）。
- [ ] runtime Markdown 无工具调用信封标签残留。

## 触发

- [ ] description 用祈使句、对准用户意图、适度 pushy、含 `Do NOT use` 边界。
- [ ] description ≤ 1024 字符。

## 自包含

- [ ] 不依赖同项目其他 skill。
- [ ] 封装的是真实能力 —— 去掉 skill 后 LLM 无法可靠完成同样的事。
