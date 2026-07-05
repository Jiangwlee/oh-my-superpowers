# Review Rubric — 评审标准

Purpose: 第 5 步独立评审用的标准。聚焦表达质量与结构，不只查格式。给 reviewer subagent 的唯一材料之一。
Sections: 评审方法 | Blocking 标准 | Positive 标准 | 表达扫描 | 值得模仿的特征

## 评审方法

先跑确定性的残留门：runtime Markdown 里不得含工具调用信封标签（sub-agent 的 Write 偶尔泄漏）。

```bash
grep -rnE '</?([a-zA-Z]+:)?(invoke|parameter|function_calls|content)>' skills/<name>/
```

命中 = 删掉报告的行再继续。

再做表达评审。可用 subagent 时**独立评审**，只给 reviewer：

- 草稿 skill 文件
- 本 rubric
- 用户的真实任务或 prompt 示例

**不要**给 reviewer 你的诊断或偏好修法 —— reviewer 必须从产物本身发现问题。subagent 不可用时，自己按本 rubric 再审一遍，并告知用户"本次评审非独立"。

## Blocking 标准

请用户确认前必须修掉。

| 领域 | 何时 Reject |
|---|---|
| 黑话 | 用了内部标签、框架俚语、未解释缩写、AI 过程词，而平实任务词本可胜任。 |
| 随意措辞 | 出现 `just`、`simply`、`vibe`、`stuff`、`do X nicely`、`as needed`、`酌情`、`适当` 等模糊表达。 |
| 元评论 | 解释某节"是关于什么"而非直接给指令（`This section explains…`、`本节介绍…`）。 |
| 弱动词 | 需要动作处用了被动或软语言：`should`、`try to`、`generally`、`if possible`、`建议`。 |
| 弱结构 | 该用工作流/路由表/清单/输出契约的地方，用了大段散文。 |
| 隐藏分支 | 说"根据情况处理"却无显式分支（`若 X → Y；否则 → Z`）。 |
| 模糊完成 | 有序步骤缺可检验的 Done 判据。 |
| 重复 | 同一规则在多处以不同措辞出现（duplication）。 |
| 通用知识 | 封装的是模型默认就会的通用知识（去掉 skill LLM 仍能可靠完成）。 |
| 依赖其他 skill | 生成的 skill 依赖同项目其他 skill，非自包含。 |
| 标签残留 | runtime Markdown 含工具调用信封标签（见评审方法）。 |

## Positive 标准

好 skill 通常具备：

- description 点名具体用户意图与触发短语，并划出边界。
- 开头告诉 agent 要执行什么活，不教通用 skill 理论。
- body 从最短可用的工作流或决策表开始。
- 每一节都改变 agent 行为；没有只为"显得完整"而存在的节。
- 长示例、领域细节、变体规则住在被引用的文件里。
- 命令与示例用真实值，不用占位符。
- 硬约束用硬词（`MUST` / `NEVER` / `不得`）。
- 表格映射决策/属性；编号列表表严格顺序；bullet 装同级规则。
- 期望输出在 agent 开始细活前就可见。

## 表达扫描

扫描每个 runtime 加载的 Markdown（`SKILL.md` 与 `references/**/*.md`）。每个问题报：

- `file`
- `quote`
- `problem`
- `severity`：`blocking` 或 `polish`
- `rewrite`

`blocking` 用于会导致错误行为、执行欠定义、或生成低质量 skill 的措辞；`polish` 用于只是不够锐利的措辞。

## 值得模仿的特征

强参考 skill 倾向于：把触发密集的 description 放 frontmatter；顶部给常见任务的快速路由；对常见失败给"错 vs 对"的具体示例；用直接语言陈述关键陷阱；把高级变体移入 reference；产物类任务带验证/QA；开工前先让期望输出可见。不要盲抄表面风格，抄的是这些操作性特征。
