# Skills 开发规范索引

开发 Skill 前读本文件。只有需要深入某个方向时，才读对应的详细文档。

## 核心原则

1. **Skill 封装真实能力，不封装通用 LLM 知识。** 来自真实工具、API、工作流的能力才值得封装。判定方法：去掉 SKILL.md 及其 references/assets，LLM 是否仍能可靠完成同样的事？如果是，不值得封装。
2. **渐进式披露。** SKILL.md 是扉页 + 目录：只放主流程骨架（checklist、每步一句话 brief）和 Hard Gate。分支逻辑、详细操作规则、模式差异等内容下沉到 `references/`，由 SKILL.md 中的加载指令按需引入。判断标准：如果一段内容能用一句话讲清楚就内联；需要展开多段才能讲清楚就放 reference。
3. **脚本必须 CLI 化。** 禁止在 SKILL.md 中写相对路径（`bash scripts/foo.sh`），改用 CLI 命令（`mytool foo --date 2026-03-24`）。弱模型无法可靠解析相对路径。
4. **description 决定触发。** description 是模型决定是否激活 Skill 的唯一依据，必须精确描述触发场景和边界。
5. **脚本面向 Agent 设计。** 有 `--help`，输出结构化，错误消息告诉 Agent 下一步做什么，不要交互式 prompt。
6. **Skill 独立自治。** 不依赖同项目其他 Skill。

## Skill 目录结构

```
<skill-name>/
├── SKILL.md          # 必须：元数据（frontmatter）+ 触发场景 + CLI 命令文档
├── hooks.json        # 可选：Claude Code hook 声明（安装时自动合并）
├── scripts/          # 可选：脚本实现（不直接被模型调用）
├── references/       # 可选：给 Agent 按需加载的详细文档
└── tests/            # 可选：T1 静态检查
```

### hooks.json（可选）

Skill 可通过 `hooks.json` 声明所需的 Claude Code hooks。`omp install skill <name>` 时自动将 hooks 合并到 `~/.claude/settings.json`，`omp remove skill <name>` 时自动移除。

格式与 Claude Code settings.json 的 hooks 结构对齐，每个条目会自动附带 `_omp_skill` 标记用于精准卸载。

示例：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "omp-<skill> recall --source $PWD",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

## SKILL.md frontmatter 格式

```yaml
---
name: skill-name          # 必须与目录名一致，小写连字符
description: >-           # 触发描述，建议 1-3 句，明确 WHEN 和 boundary
  Use when ...
  Do NOT use when ...
---
```

## 5 种设计模式

每个 Skill 必须属于（或组合）以下模式之一。模式决定目录结构和 SKILL.md body 的写法：

| 模式 | 适用场景 | 核心文件 |
|------|---------|---------|
| **Tool Wrapper** | 让模型成为特定技术/库的专家 | `references/conventions.md` |
| **Generator** | 从模板生成结构化文档/代码 | `assets/<template>.md` + `references/style-guide.md` |
| **Reviewer** | 按标准检查内容，按严重程度分类 | `references/review-checklist.md` |
| **Inversion** | 先多轮收集需求，再行动 | `assets/<output-template>.md` |
| **Pipeline** | 严格的多步骤工作流，带检查点 | 各步骤按需加载 `references/` 和 `assets/` |

模式可以组合（如 Pipeline + Reviewer）。使用 `brainstorming`（Skill Gate）时会强制选择模式。

## 详细文档

| 场景 | 文档 |
|------|------|
| 首次写 SKILL.md，不确定格式 | [agent-skills-spec.md](agent-skills-spec.md) |
| 想提升 Skill 整体质量 | [agent-skills-best-practices.md](agent-skills-best-practices.md) |
| 研究如何让 Agent 加载和使用 Skill | [how-to-add-skills-to-agents.md](how-to-add-skills-to-agents.md) |
| 设计或优化 Skill 的脚本 | [how-to-use-scripts-in-skills.md](how-to-use-scripts-in-skills.md) |
| 优化 description 触发准确率 | [how-to-optimize-skill-descriptions.md](how-to-optimize-skill-descriptions.md) |
| 建立 Skill 的评估体系 | [how-to-evaluate-skill-output-quality.md](how-to-evaluate-skill-output-quality.md) |
| 项目内积累的 Skill 开发经验 | [skills-dev-guide.md](skills-dev-guide.md) |
| Claude Code Skill 开发完整手册 | [claude-skill-dev-guide.md](claude-skill-dev-guide.md) |
| 文件头规范（让 AI 快速理解文件） | [file-header-spec.md](file-header-spec.md) |
