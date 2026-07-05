# Writing Conventions — 结构与写法

Purpose: 起草 SKILL.md 与 references 时的结构规范：什么放哪、用什么 Markdown 载体、渐进披露怎么切、文件头怎么写。第 4 步用本文件。
Sections: SKILL.md 骨架 | 渐进披露判据 | Markdown 载体 | 文件头 | description

## SKILL.md 骨架

SKILL.md 是扉页 + 目录，不是全文。标准骨架：

1. **frontmatter** —— `name`（= 目录名，小写连字符）+ `description`（触发依据，见末节）。
2. **标题 + summary 段** —— 紧跟标题写 `Purpose / Input / Output / Sections`（4 行以内，让 agent 读前 20 行即懂）。
3. **角色约定**（可选）—— 一句话定 agent 身份与边界。
4. **Hard Gate** —— 表格：`条件 | 动作`。列出禁止/必须的硬约束。
5. **Core Principles**（可选）—— 几条 leading word 式的原则，bullet。
6. **Workflow** —— 有序步骤，每步一句 brief + 一个可检验 Done 判据 + 按需 load pointer。
7. **References** —— 表格：`文件 | 作用 | 何时读`。

目标：SKILL.md body < 500 行（多数远小于）。逼近就下沉。

## 渐进披露判据

**一句话讲得清 → 内联；要展开多段才讲清 → 下沉 `references/`。**

- 每条分支路径都要的 → 内联。
- 只有部分分支够到的 → 下沉，SKILL.md 留一个措辞明确的 pointer（"读 X 来做 Y"）。
- pointer 触发不稳且指向必读材料 → 先锐化措辞，改不动才拉回内联。
- references 保持从 SKILL.md **一层深**：reference 文件不要再指向更深的 reference（弱模型只会 `head -100` 预览，读不全深层链）。

## Markdown 载体

用对的载体表达对的结构：

| 载体 | 用于 |
|---|---|
| 编号列表 | 严格顺序（Workflow 步骤） |
| bullet | 无序的同级规则 |
| 表格 | 决策映射、属性对照、路由（`条件 → 动作`） |
| 代码块 | 命令、示例、输出骨架，用**真实值**不用占位符 |
| mermaid | 多分支流程的总览图 |

硬约束的硬词用法见 `wording.md` §硬词。

## 文件头

- **SKILL.md**：frontmatter 后，标题下紧跟 `Purpose / Input / Output / Sections` summary 段。
- **reference 文件**：无 frontmatter；标题下紧跟 `Purpose / Sections` summary 段。
- **script**：完整 header（Purpose / Input / Output / Public API），英文。
- 原则：读前 20 行即懂此文件做什么。header 陈旧比没有更糟 —— 改内容就同步改 header。

## description

description 是模型决定是否加载 skill 的**唯一**依据。写法：

- **祈使句**：写"何时用"（"Use when the user…"），不写"这个 skill 做什么"（"This skill…"）。
- **对准用户意图**，不写内部机制。
- **适度 pushy**：显式列出适用场景，包括用户不点名领域的情形（"even without naming the format"）。
- **划边界**：写清 `Do NOT use when…`，与相邻 skill 区分。
- **精简**：几句到一小段，硬上限 1024 字符。
- 埋入你真实会用的**引导词** —— 同一个词活在 prompt/文档/代码里，触发更可靠。
