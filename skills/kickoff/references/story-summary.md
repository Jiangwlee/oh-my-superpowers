# Story Summary Guideline

Phase 3 收尾时写 `story-summary.md`。本文件定义何时写、写到哪、写成什么结构，以及如何处理 promotion。

## When

满足以下条件后写：

- E2E 已通过
- 外围文档（架构 / README / Backlog）已同步
- Story 即将关闭

不要在调试或修复中途写。

## Where

固定路径：

`<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/story-summary.md`

## Template

```markdown
# Story Summary: <slug>

## 1. 结论

- **做了什么**：<一段话总结 story 交付了什么>
- **Commit 范围**：<commit hash range；e.g., `abc1234..def5678`>
- **关键决策**：
  - <决策 1：what + why>
  - <决策 2：what + why>

## 2. 负面机制

本次 kickoff 哪里不顺？

- **<mechanism / 节点>**：<具体描述哪里卡住、估算偏差、流程摩擦或工具卡点；附 commit / 时间点>

若全程顺畅，明确写"无"。

## 3. 未决项

留给下一次的 follow-up：

- **<item>**：<描述 + 处理建议；e.g. fix task / scope creep / 技术债登记位置>

若无未决项，明确写"无"。

## 4. Promotion 候选

本次暴露出 kickoff / `CLAUDE.md` / 项目流程**应当改进**的具体条款：

- **<目标文件 / 条款>**：<具体改动建议；e.g. "kickoff Hard Gate 应增加 X 行"、"项目 CLAUDE.md 应补 Y 约束">

若无可改进，明确写"无"。
```

## Promotion 处理

写完后重读 §2 / §4，再按下表处理：

| 条目类型 | 动作 |
|---|---|
| 跨 story 反复出现的负面机制 | 必须提给用户决定是否升级到 kickoff / CLAUDE.md |
| 跨 story 可复用的正面机制 | 提议加固到 kickoff `SKILL.md` 或 `references/` |
| 仅本 story 相关的发现 | 留在 `story-summary.md`，随归档冻结 |

任何 promotion 都是**显式动作**。把建议写在对话里，让用户决定；不要静默修改 kickoff 本体或项目 `CLAUDE.md`。
