# Skill Design: agent-review

## 能力定义
- 封装的规范/知识：Pi agent markdown 格式规范 + 质量评审 rubric（8 个维度）
- 核心价值：「它让模型能够按照 Pi agent 规范和质量标准，审查 agents/ 目录下的 markdown 文件，输出结构化诊断报告」
- 能力边界：
  - 能做：检查 frontmatter 合规性、身份清晰度、输入规格、工作流结构、输出格式、失败处理、guardrails、工具最小化
  - 不能做：审查 skill 目录（skill-review 的职责）、运行 agent、测试 agent 实际行为

## 设计模式
- 主模式：Reviewer
- 组合模式：无
- 选择理由：Pi agent 是单个 markdown 文件，无运行时行为需验证，纯静态内容审查即可

## 目录结构

```
agent-review/
├── SKILL.md
└── references/
    ├── README.md        # 索引：场景 → 文件映射
    ├── agent-spec.md    # Pi agent 格式规范（frontmatter 字段、tools 合法值、model 合法值）
    └── rubric.md        # 8 个审查维度的详细评判标准和示例
```

## CLI 化方案
不适用（Reviewer 模式，无可执行脚本）

## SKILL.md Frontmatter 草稿

```yaml
---
name: agent-review
description: >-
  Review and audit a Pi agent markdown file for spec compliance and design quality.
  Use when: reviewing an agent file, checking if an agent is ready to deploy,
  auditing agent description quality, evaluating system prompt structure.
  Do NOT use when: reviewing a skill directory (use skill-review), designing a new agent
  (use agent-brainstorming), or testing agent runtime behavior.
metadata:
  pattern: Reviewer
---
```

## 渐进式披露规划

- **SKILL.md body**：
  - 工作流步骤（输入处理 → 加载规范 → 按维度审查 → 输出报告）
  - 输出格式模板（finding 结构：severity/dimension/issue/evidence/fix）
  - Guardrails（每条 finding 必须有文件证据）

- **references/**：
  - `agent-spec.md`：frontmatter 字段规范（name/description/tools/model）、tools 合法值列表、model 合法枚举值
  - `rubric.md`：8 个维度的判断标准（Frontmatter 合规、身份清晰度、输入规格、工作流结构、输出格式、失败处理、Guardrails、工具最小化）

## 8 个审查维度

| # | 维度 | 核心 Checkpoint |
|---|------|----------------|
| 1 | Frontmatter 合规 | name/description/tools/model 完整；name 与文件名一致；tools/model 值合法 |
| 2 | 身份清晰度 | 有具体职能角色；有明确专业领域；有铁律/核心约束 |
| 3 | 输入规格 | 明确需要用户提供什么；缺失输入时有处理策略 |
| 4 | 工作流结构 | 有明确阶段/步骤；不是模糊散文 |
| 5 | 输出格式 | 有结构化输出模板；有 done criteria |
| 6 | 失败处理 | 有 failure handling 分支；优雅降级而非硬失败 |
| 7 | Guardrails | 有明确的禁止行为列表 |
| 8 | 工具最小化 | tools 仅列出实际需要的工具，不过度授权 |

## Trigger Eval

- **应触发**：
  - "review agents/skill-review.md"
  - "检查这个 agent 写得怎么样"
  - "这个 agent 符合规范吗"
  - "agent-review agents/foo.md"
- **不应触发**：
  - "review skills/my-skill"（→ skill-review）
  - "设计一个新 agent"（→ agent-brainstorming）
  - "运行这个 agent"

## T1 测试计划

- [ ] SKILL.md frontmatter 的 name 字段为 `agent-review`
- [ ] references/README.md 存在且包含两个文件的索引
- [ ] references/agent-spec.md 存在且包含 tools 合法值列表
- [ ] references/rubric.md 存在且覆盖全部 8 个维度
- [ ] SKILL.md 无相对路径脚本调用
