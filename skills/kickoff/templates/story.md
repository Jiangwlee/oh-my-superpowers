# Story: <story-name>

<!--
story.md 是静态契约：Goal / Scope / 必读 / 测试环境 / 红线 / Task 计划。
过程状态、决策、坑点、ISSUE 全部进 journal.md，不回写到本文件。
init 时已预置 ## Summary 骨架；Phase 3 收尾时填写各子节内容。
-->

## Goal

<!-- 一句话目标。WHY 在 design-doc 里就别复制；没有 design-doc 时把动机塞进来一两句。 -->

## Scope

### In

<!-- 要改的文件 / 模块 -->

-

### Out

<!-- 明确不改的部分。防 scope creep 的负面清单。强制写。 -->

-

## 参考文档

<!--
设计 / 契约 / 外部资料；可空可多条可外链；和"必读文件"职责不同：
  参考文档 = 一次性建立背景；必读文件 = 每 task 入口对照事实。
无内容则整段省略本节。

格式（替换以下注释内的样板，并把真实条目写到注释外）：
  | 文档 | 读什么 |
  |---|---|
  | `docs/adr/0023-xxx.md` | 协议契约 |
  | `docs/brainstorming/specs/YYYY-MM-DD-xxx.md` | 本 story design 决策 |
-->


## 必读文件

<!--
每个 task 入口必读。锚点用语义不用行号（行号会过期）。
锚点形式：函数/类名 / 章节标题 / 关键标识符。
验证命令是给 developer 进 task 时的起手 grep（也是反凭记忆机制的物证）。

格式（替换以下注释内的样板，并把真实条目写到注释外）：
  | 文件 | 锚点 | 读什么 | 验证命令 |
  |---|---|---|---|
  | `cli/foo/main.py` | `bar` 命令定义（`@app.command`） | 命令签名、option 风格 | `rg -n '@app.command' cli/foo/main.py` |
  | `scripts/baz.py` | `dispatch()` 函数 | 入口分发逻辑 | `rg -n 'def dispatch' scripts/baz.py` |
-->


## 测试环境

<!--
测试 / E2E 命令、fixture 路径、特殊环境（docker、远程机器等）。
Agent 不会读你的脑子，把"运行什么、在哪运行"显式写出来。
-->

- 项目根：
- venv：
- 单测：
- E2E：
- Fixture：

## 红线

<!-- 可选段；与 design-guard / 既有 ADR 的兼容点。无内容则整段省略本节。 -->

-

## Task 计划

<!--
原始拆分。状态/进度看 journal.md，不回写到这里。
每条带"验收"——一句话能看出怎么算完。

格式（替换以下注释内的样板，并把真实 task 写到注释外）：
  - **T1 explore**：... — 验收：...
  - **T2 implement**：... — 验收：...
-->


---

<!-- 以下 Summary 节在 init 时即预置骨架；Phase 3 收尾时填写各子节内容。 -->

## Summary

### 结论

<!-- 做了什么 / commit 范围 / 关键决策（一句话） -->

### 负面机制

<!-- 本次哪里不顺：估算偏差、流程摩擦、工具卡点 -->

### 未决项

<!-- follow-up：fix task / scope creep / 技术债登记。引用 journal 里的 ISSUE-### -->

### Promotion 候选

<!-- kickoff / CLAUDE.md / 项目规范应当改进的具体条款。无可改进时写"无"。 -->
