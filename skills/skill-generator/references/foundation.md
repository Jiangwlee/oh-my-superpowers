# Foundation — 什么是 Skill，产出物长什么样

Purpose: 让刚加载本 skill 的 agent 先具备造 skill 的地基：skill 是什么、由什么构成、最终产出长什么样、以及核心词汇。没有这层，与用户澄清需求必然南辕北辙。
Sections: Skill 是什么 | 何时值得封装 | 目录结构 | 一个完整的最小示例 | 核心词汇

## Skill 是什么

Skill 是一个**自包含的目录**，把某项**真实能力**（真实工具、API、工作流、项目约定）打包成 agent 的"上岗手册"。它把一个通用 agent 变成某个领域的专家 —— 提供模型自身**不具备**的过程性知识。

Skill 不是代码库、不是文档站、不是 prompt 模板。它的唯一使命是让 agent 在该任务上**行为可预测**：每次都走相同的过程。

## 何时值得封装

判定方法（一票否决）：**去掉 SKILL.md 及其 references / assets，LLM 是否仍能可靠完成同样的事？**

- 仍能 → 这是通用 LLM 知识，**不值得封装**。别写"如何处理错误""遵循最佳实践"这类空话 skill。
- 不能（依赖具体 API 模式、项目约定、非显然的边界、特定工具序列）→ 值得封装。

## 目录结构

```
<skill-name>/
├── SKILL.md          # 必须：frontmatter（name + description）+ 骨架 + Hard Gate + Workflow
├── references/       # 可选：按需加载的详细文档（分支逻辑、规则、示例）
├── scripts/          # 可选：CLI 化的可执行单元（不被模型直接调用）
├── assets/           # 可选：Generator / Inversion 模式的模板或输出骨架
└── hooks.json        # 可选：Claude Code hook 声明
```

硬约束：

- **name 必须与目录名一致**，小写连字符。
- **tests 不进 skill 目录** —— 安装时整个目录会被 symlink 暴露给 agent；测试放项目根 `tests/skills/<name>/`。
- **自包含** —— 不依赖同项目其他 skill。

## 一个完整的最小示例

一个 Tool Wrapper 模式的 skill，让 agent 成为某内部 CLI 的专家：

```
csv-profiler/
├── SKILL.md
└── references/
    └── cli.md
```

`SKILL.md`：

```markdown
---
name: csv-profiler
description: >-
  Profile a CSV file — column types, null rates, outliers — via the
  `csvp` CLI. Use when the user asks to inspect, summarize, or sanity-check
  a .csv, even without naming the tool.
---
# CSV Profiler

Purpose: Profile a CSV's columns, nulls, and outliers.
Input:   A .csv path from the user.
Output:  A profile table printed to the user.
Sections: Workflow | References

## Workflow

- Run `csvp profile <path> --json`. Done: JSON returned.
- Summarize columns, null rates, and flagged outliers as a table.
  Done: table shown, outlier columns named.

## References

- `references/cli.md` — full `csvp` flags and output schema.
```

要点：SKILL.md 短、只有骨架；细节（CLI 全部参数）下沉 `references/cli.md`；description 用祈使句、覆盖不点名 CSV 的场景。

## 核心词汇

产出高质量 skill 要用到的术语（详细推理见 `philosophy.md`）：

| 术语 | 一句话 |
|---|---|
| **Predictability** | 根德性：agent 每次走相同的**过程**（不是相同的输出）。 |
| **Description** | frontmatter 里的触发依据；模型据此决定是否加载 skill。 |
| **Context load** | 一个 model-invoked skill 的 description 常驻上下文的成本。 |
| **Progressive disclosure（渐进披露）** | 把 reference 移出 SKILL.md、藏到按需加载的文件，保持顶层清爽。 |
| **Steps / Reference** | Steps = 有序动作（SKILL.md 主体）；Reference = 按需查阅的定义/规则/示例。 |
| **Completion criterion（Done 判据）** | 告诉 agent 一步是否完成的可检验条件。 |
| **Leading word（引导词）** | 一个模型预训练里已有的紧凑概念，反复作为 token 出现以锚定行为。 |
| **Single source of truth** | 每个含义只在一处权威定义；重复即 duplication。 |
