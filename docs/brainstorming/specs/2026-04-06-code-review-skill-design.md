# Skill Design: code-review

本地代码变更的结构化 review skill，整合 sanyuan-skills/code-review-expert 的技术检查深度与 superpowers 的工作流集成和反 sycophancy 机制。

## 目录

1. [能力定��](#能力定义)
2. [设���模式](#设��模式)
3. [目���结构](#目录结构)
4. [SKILL.md Frontmatter 草���](#skillmd-frontmatter-草稿)
5. [设计方案](#设计方案)
   - [Review 输入与 Diff 规模判���](#review-输入与-diff-规模判定)
   - [执行者选择与降级策略](#执行者选择��降级策略)
   - [Review Checklist 分层](#review-checklist-分层)
   - [Severity 分级与输出格式](#severity-分级与输出格式)
   - [完整流程编排](#完整流程编排)
6. [渐进式披露规划](#渐进式披露规划)
7. [Trigger Eval](#trigger-eval)
8. [行动原则](#行动原则)
9. [行动计划](#行��计划)
10. [T1 测试��划](#t1-测试计划)

---

## 能力定义

- **封装的工具/规范/脚本：** 结构化 review checklist（core + extended）、P0-P3 severity 体系、跨工具执行编排（sub agent / tmux codex / tmux claude）、降级策略
- **核心价值：** 让模型能够按标准化流程执行本地代码 review，输出结构化、可操作的结果
- **能力边界：**
  - 能做：review 工作区未提交变更、review 最近 N 个本地 commit
  - 不能做：PR review、分支对比、纯文档 review

## 设计模式

- **主模式：** Reviewer — 按标准审查代码，按严重程度分类输出
- **组合模式：** Pipeline — 多步骤流程（上下文准备 → 执行 review → 结果呈现）
- **选择理由：** 核心是结构化审查 + 有明确的编排步骤和检查点

## 目录结构

```
skills/code-review/
├── SKILL.md                              # 元数据 + 流程骨架 + 执���者选择 + 降级策略
├── references/
│   ├��─ review-checklist-core.md          # Correctness + Security checklist
│   ├── review-checklist-extended.md      # Performance + Maintainability + SOLID checklist
│   └��─ output-format.md                  # Severity 定义 + 结构化输出模板 + Verdict 语义
└── assets/
    └── review-prompt-template.md         # 发给执行者的 prompt 模板（含 placeholder）
```

无 `scripts/` 目录——纯知识型 skill，不需要 CLI 化。

## SKILL.md Frontmatter 草稿

```yaml
---
name: code-review
description: >-
  Review local code changes: uncommitted work (staged/unstaged) or recent
  unpushed commits. Use when code needs quality review during local development.
  Do NOT use for PR review or branch comparison.
metadata:
  pattern: reviewer + pipeline
---
```

## 设计方案

### Review 输入与 Diff 规模判定

**Review 输入方式：**

| 场景 | 命令 | 说明 |
|------|------|------|
| 未提交变更 | `git diff` + `git diff --cached` | unstaged + staged |
| ��近 N 个 commit | `git diff HEAD~N..HEAD` | 默认 N=1 |

**Diff 规模分级：**

| 规模 | 行数 | 检查策略 |
|------|------|----------|
| 小 | <50 行 | 只加载 core checklist |
| 中 | 50-300 ��� | 加载 core + extended checklist |
| 大 | >300 行 | 加载 core + extended，按文件分批 review |

**发起者职责：** 在构造 review 请求前，发起者负责：
1. 运行 git diff 获取变更内容
2. 统计 diff 行数，判���规模
3. 收集相关上下文（变更涉及的模块说明、原始需求）
4. 根据规模决定加载哪些 checklist

### 执行者选择与降级策略

**四种��行者：**

| 优先级 | 执行者 | 调用方式 | 适用场景 |
|--------|--------|----------|----------|
| 默认 | Sub agent | Claude Code Agent 工具 | 大多数场景 |
| 用户指定 | tmux codex (自定义 prompt) | `cat /tmp/review-prompt.md \| codex exec --ephemeral --dangerously-bypass-approvals-and-sandbox` | 用户要求 codex review |
| 用户指定 | tmux codex (内置 review) | `codex exec review --uncommitted --ephemeral --dangerously-bypass-approvals-and-sandbox` | 用户要求 codex 内置 review |
| 用户指定 | tmux claude | `cat /tmp/review-prompt.md \| claude -p --no-session-persistence --dangerously-skip-permissions` | 用户要求独立 claude |

**tmux 执行流程：**
1. 将 review prompt 写入临时文件 `/tmp/code-review-prompt.md`
2. 启动 tmux session：`tmux new-session -d -s code-review '<command>'`
3. 每 30s 检查状态：`tmux has-session -t code-review`
4. 完成后捕获输出：`tmux capture-pane -t code-review -p`
5. 清理临时文件和 tmux session

**降级路径：**

```
tmux 失败（启动失败/超时/崩溃）
  → 告知用户原因，降级为 sub agent
    → sub agent 失败
      → 告知用户原因，发起者直接 review（加载 checklist 自己做）
```

### Review Checklist 分层

**Core Checklist（必检，所有 diff 规模）** — `references/review-checklist-core.md`：

1. **Correctness** — 逻辑是否正确？边界条件是否处理？是否满足原始需求？
2. **Security** — 注入、硬编码密钥、auth bypass、unsafe deserialization？

**Extended Checklist（中大 diff 额外加载）** — `references/review-checklist-extended.md`：

3. **Performance** — N+1 查询、无界循环、缺失索引、不必要的内存���配？
4. **Maintainability** — 命名清晰度、代码结构、错误处理、代码异味？
5. **SOLID violations** — 仅在涉及类/模块设计时检查，不对小改动强制

**反模式检查（内嵌于两份 checklist）：**

- **反 sycophancy** — 发现问题必须指出，不允许"代码整体很好，只有小建议"式的敷衍
- **YAGNI 检查** — 新增抽象/接口前先确认是否有多处调用，单一使用不需要抽象
- **Removal candidates** — 标记变更中引入的死代码、未使用的 import、遗留的 debug 代码

### Severity ���级与输出格式

**Severity 定义：**

| 级别 | 含义 | 用户响应 |
|------|------|----------|
| **P0 — Critical** | 必须修复：bug、安全漏洞、数据丢失风险 | 不修不能提交 |
| **P1 — High** | 应当修复：性能问题、缺失错误处理、需求未满足 | 强烈建议修复 |
| **P2 — Medium** | 建议修复：代码风格、可读性、轻微改进 | 用户决定 |
| **P3 — Low** | 可选：替代方案建议、nitpick | 仅供参考 |

**结构化输出格式：**

```markdown
## Summary

[1-2 句：整体评估]

## Issues

- **[P0]** `file/path:line` — 问题描述
  - Evidence: [代码中观察到的具体证据]
  - Suggested fix: [具体可操作的修复建议]

- **[P1]** `file/path:line` — ...

（无问题时输出："No issues found."）

## Verdict

APPROVE — 无 P0/P1 问题
REQUEST_CHANGES — 存在 P0/P1 问题（列出编号）
```

**Verdict 后的流程：**
- **APPROVE** → 呈现结果给用户，流程结束
- **REQUEST_CHANGES** → 呈现结果给用户，用户决定是否修复、修哪些

### 完整流程编排

```
发起者（Claude Code）                    执行者（sub agent / tmux codex / tmux claude）
    │                                          │
    ├─ 1. 获取 diff（git diff）                │
    ├─ 2. 统计行数��判定规模                    │
    ├─ 3. 收集上下文（模块说明、需求）          │
    ├─ 4. 加载 checklist（core / core+extended）│
    ├─ 5. 组装 review prompt                    │
    ├─ 6. 选择执行者（默认 sub agent）          │
    │                                          │
    ├──────── 派发 ────────────────────────────→│
    │                                          ├─ 7. ���立执行 review
    │   （tmux 模式：每 30s 检查状态）          ├─ 8. 输出结构化结果
    │←──────── 返回结果 ─────��─────────────────┤
    │                                          │
    ├─ 9. 解析 Verdict                         │
    ��─ 10. 呈现结果给用户                       │
    │                                          │
    │   用户决定：                              │
    │   ├─ 无需修复 �� 结束                     │
    │   ├─ 修复指定 issues → 发起者执行修复     │
    │   └─ 全部修复 → 发起者执行修复            │
    │                                          │
    ├─ 11. 执行修复                             │
    ├─ 12. （可选）用户要求再次 review → 回到 1 │
    └─ 结束                                    │
```

**关键约束：**
- 修复循环不自动触发，每次由用户决定
- 每次降级必须告知用户原因

## 渐进式披露规划

- **SKILL.md body：** 流程骨架（checklist 形式）、diff 规模判定规则、执行者选择表、降级策略、tmux 命令参考
- **references/review-checklist-core.md：** 小 diff 必检，所有 review 加载
- **references/review-checklist-extended.md：** 中大 diff 额外加载
- **references/output-format.md：** Severity 定义 + 输出模板 + Verdict 语义
- **assets/review-prompt-template.md：** 发给执行者的 prompt 模板

## Trigger Eval

**应触发：**
- "review 一下这些改动"
- "帮我做 code review"
- "检查一下最近的 commit"
- coding 完成后的工作流衔接

**不应触发：**
- "review 这个 PR" — PR review 不在范围内
- "对比 main 分支" — 分支对比不在范围内
- "review 这篇文档" — 纯文档 review 不在范围内

## 行动原则

### 默认原则

1. **TDD: Red → Green → Refactor** — skill 的 checklist 和输出格式先用 T1 静态测试验证
2. **Break, Don't Bend** — 不兼容 team skill 的模板，自包含重写
3. **Zero-Context Entry** — SKILL.md 前 20 行让读者理解职责���边界

### 任务补充原则

4. **Explicit Contract** — severity 定义、输出格式、verdict 语义必须在 references 中明确声明，不靠隐式约定
5. **Minimum Blast Radius** — 分阶段交付：先 core checklist + sub agent 模式，再加 extended checklist + tmux 模式

### 任务专属原则

6. **Review 独立性** — 执行者在独立上下文中完成 review，不能访问发起者的对话历史，prompt 必须自包含所有信息
7. **人工决策权** — 修复决策始终由用户做出，skill 只呈现结果和建��，不自动执行修复循环

## 行动计划

### Task 1: 编写 review-checklist-core.md

**产出：** `references/review-checklist-core.md`

内容：
- Correctness 检查项（逻辑正确性、边界条件、需求满足）
- Security 检查项（注入、硬编码密钥、auth bypass、unsafe deserialization）
- 反 sycophancy 规则：发现问题必须指出，禁止敷衍式肯定
- YAGNI 检查：新增抽象前确认多处调用
- Removal candidates：死代码、未使用 import、debug 遗留

### Task 2: 编写 review-checklist-extended.md

**产出：** `references/review-checklist-extended.md`

���容：
- Performance 检查项（N+1、无界循环、缺失索引、内存分配）
- Maintainability 检查项（命名、结构、错误处理、代码异味）
- SOLID violations（仅涉及类/模块设计时检查）

### Task 3: 编��� output-format.md

**产���：** `references/output-format.md`

内容：
- P0-P3 severity 定义表
- 结构化输出 markdown 模板（Summary → Issues → Verdict）
- Verdict 语义定义（APPROVE / REQUEST_CHANGES）
- 每个 issue 的必填字段：severity、file:line、description、evidence、suggested fix

### Task 4: 编写 review-prompt-template.md

**产出：** `assets/review-prompt-template.md`

Placeholder 变量：
- `{role}` — reviewer 角色定义
- `{context}` — 项目描述 + 原始需求
- `{diff}` — 代码变更内容
- `{checklist}` — 根据 diff 规模拼装的 checklist 内容
- `{output_format}` — 输出格式要求（从 output-format.md 提取）

### Task 5: 编写 SKILL.md

**产出：** `skills/code-review/SKILL.md`

结构：
- Frontmatter（name + description）
- 流程 checklist（步骤 1-12）
- Diff 规模判定规则（<50 / 50-300 / >300）
- 执行者选择表（sub agent / tmux codex / tmux codex review / tmux claude）
- tmux 命令参考（session 创建、状态检查、输出捕获）
- 降级策略
- Checklist 加载指令（按 diff 规模读取 references/）

### Task 6: T1 静态测试

验证项：
- [ ] SKILL.md frontmatter 格式正确（name、description 字段存在）
- [ ] SKILL.md 无相对路径脚本调用（无 `bash scripts/`、`python scripts/`）
- [ ] references/ 下所有文件在 SKILL.md 中被引用
- [ ] assets/ 下模板文件中的 placeholder 在 SKILL.md 流程中被说明
- [ ] 无对其他 Skill 的依赖引用

### Task 7: 完成核查

- [ ] 逐项检查 Task 1-6 完成状态
- [ ] 对照设计方案确认实现无偏离
- [ ] 报告：tasks completed (X/X)、未完成步骤、spec 偏离、最终 ✅/⚠️ 结论

## T1 测试计划

1. frontmatter 格式校验：`name` 与目录名一致、`description` 非空
2. 自治检查：SKILL.md 中无项目外部文件引用、无其他 Skill 依赖
3. references 完整性：SKILL.md 中引用的 references 文件全部存在
4. assets 完整性：SKILL.md 中引用的 assets 文件全部存在
5. 无相对路径脚本调用
