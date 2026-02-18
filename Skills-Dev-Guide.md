# Skills 开发指导索引

本文件是开发经验的索引，详细内容存储在 `guides/` 目录。

---

## 基础规范

| 主题 | 文件 | 说明 |
|------|------|------|
| 目录结构与命名 | [guides/skill-structure.md](guides/skill-structure.md) | 单个 skill 的推荐目录结构、命名规范、SKILL.md 最小规范 |
| 质量模式与反模式 | [guides/skill-quality-patterns.md](guides/skill-quality-patterns.md) | 高质量 skill 的共性、提交前检查清单、常见反模式 |
| 可复用模板 | [guides/skill-template.md](guides/skill-template.md) | 可直接复制的 SKILL.md 模板、description 写法参考 |

## 流程与部署

| 主题 | 文件 | 说明 |
|------|------|------|
| 开发流程 | [guides/dev-workflow.md](guides/dev-workflow.md) | 从需求到部署的完整步骤、持续演进建议 |
| Openclaw 适配 | [guides/openclaw-adaptation.md](guides/openclaw-adaptation.md) | 加载优先级、门控机制、上下文预算、部署命令 |

## 优秀项目分析

| 项目 | 文件 | 说明 |
|------|------|------|
| superpowers | [guides/superpowers-architecture.md](guides/superpowers-architecture.md) | 目录结构、多平台适配、SessionStart 引导程序机制、using-superpowers 逐行解析、可复用设计模式 |

---

## 快速索引：常见问题

- **如何写触发条件？** → [skill-structure.md](guides/skill-structure.md) + [skill-template.md](guides/skill-template.md)
- **如何控制 context 成本？** → [skill-quality-patterns.md](guides/skill-quality-patterns.md) §渐进披露
- **如何让 skill 在每次会话自动激活？** → [superpowers-architecture.md](guides/superpowers-architecture.md) §SessionStart Hook
- **如何让一个引导 skill 驱动多个 skill？** → [superpowers-architecture.md](guides/superpowers-architecture.md) §引导程序机制
- **如何适配多个 AI 平台？** → [superpowers-architecture.md](guides/superpowers-architecture.md) §多平台适配策略
- **部署到 Openclaw 怎么做？** → [openclaw-adaptation.md](guides/openclaw-adaptation.md)
