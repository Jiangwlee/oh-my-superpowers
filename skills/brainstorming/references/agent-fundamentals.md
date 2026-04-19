# Agent 基础知识

Agent 设计的核心原则和判断标准。在 Phase 0 身份审问时参照本文件。

---

## 1. Agent 必须有身份

Agent 是有明确角色（职业/职能）的任务执行者。没有身份的需求不是 Agent 需求。

**有身份的例子**：代码审查官、投资分析师、Skill 质量审查官、技术写作编辑
**没有身份的例子**：PDF 阅读器、数据抓取器、文件转换工具、API 封装

判断方法：用一个职业或职能词语描述它。如果只能用"工具"、"器"、"转换"来描述，它是 Skill，不是 Agent。

---

## 2. Agent vs Skill 边界

| 维度 | Agent | Skill |
|------|-------|-------|
| 身份 | 有（职业/职能角色） | 无（工具/工作流） |
| 判断 | 需要无法脚本化的语义判断 | 可以完全脚本化或模板化 |
| 所有权 | 对结果负责，有署名输出 | 跟随调用方，无独立产出 |
| 调用方式 | `omp run agent` 独立运行 | 被 Agent 或 Claude 加载 |

**三维判断（Role × Agency × Ownership）**：
- Role = 0（无法描述角色）→ 降级为 Skill
- Agency = 0（所有判断可脚本化）→ 降级为 Skill
- Ownership = 0（不对结果负责）→ 降级为 Skill

任意一维为零 → 这是 Skill 需求，不是 Agent 需求。

---

## 3. 身份审问 4 道题的判断标准

**Q1（角色名）**：
- 通过：「股市分析师」、「代码审查官」、「技术文档编辑」
- 失败：「PDF 处理器」、「数据抓取工具」、「API 封装器」
- 信号：答案里有"器"、"工具"、"处理"、"转换" → 可能是 Skill

**Q2（无法脚本化的判断）**：
- 通过：能举出具体场景，且该场景需要语义推理（"判断这段代码是否符合设计意图"）
- 失败：举不出具体场景，或所有判断都可以用规则/正则/脚本完成
- 信号：「我只是需要它做 X」，没有判断场景 → 可能是 Skill 或直接用模型

**Q3（结果所有权）**：
- 通过：有明确的产出物，用户会基于这个产出做决策
- 失败：只是中间步骤，输出直接流入下一步处理

**Q4（专业背景）**：
- 通过：能描述一个真实的人类职业背景（「需要熟悉代码审查规范、理解业务逻辑」）
- 失败：「只需要会操作 X 工具」→ 可能是 Skill

---

## 4. Pi Agent 格式

```markdown
---
name: agent-name
description: >-
  Use when ...
  Do NOT use when ...
tools: bash, read
model: claude-sonnet-4-6
---

System prompt 从这里开始...
```

**frontmatter 字段**：
- `name`：小写字母 + 连字符，与文件名一致
- `description`：触发条件，包含 Use when 和 Do NOT use when
- `tools`：最小化工具集，只列真正需要的（bash, read, edit, write, grep, find, ls）
- `model`：默认 `claude-sonnet-4-6`，本地模型用 `litellm-local/qwen3.5-27b`

---

## 5. agents.json 配置要求

每个 Agent 必须在 `agents/agents.json` 中注册：

```json
{
  "agent-name": {
    "agent": "@agents/agent-name.md",
    "model": "litellm-local/qwen3.5-27b",
    "skills": [
      "@skills/some-skill/SKILL.md"
    ]
  }
}
```

- `agent`：`@` 前缀表示相对 OMP_HOME 的路径
- `skills`：agent-specific skills，全局 skills 无需列出（pi 自动加载）
- `model`：可被 `omp run agent --model` 覆盖

---

## 6. 常见设计错误

**错误 1：把工具需求包装成 Agent**
```
# 错误思路
"我需要一个 PDF 解析 Agent"
→ 这是工具需求，用 Skill 封装 pdf 解析能力即可

# 正确方向
"我需要一个技术文档审查官，它能判断 PDF 中的规范是否完整"
→ 有角色、有判断、有所有权，是 Agent
```

**错误 2：Agent 直接写业务逻辑而不依赖 Skill**
```
# 错误：system prompt 里写了绝对脚本路径（示例占位符，非真实路径）
运行 <abs-path>/scripts/<your-script>.sh --input $file

# 正确：通过 agents.json 声明 skill 依赖，skill 提供 CLI
```

**错误 3：description 写工作流而不是触发条件**
```
# 错误
description: 审查代码，检查规范，输出报告，发送通知

# 正确
description: Use when reviewing pull requests for spec compliance.
  Do NOT use when doing routine code formatting or linting.
```
