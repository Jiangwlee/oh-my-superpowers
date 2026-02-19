# About

本项目开发了一系列满足Openclaw规范的Skills.

## 规范

1.[Agent Skills](https://github.com/agentskills/agentskills): Openclaw遵从的Skills规范

## Openclaw特有机制

1.[Tools](https://docs.openclaw.ai/tools/browser): Openclaw有一些内置tools，其中browser可以用来访问需要Javascript渲染的网页。

## 开发建议

1.开发Skills内置脚本Scripts时，**禁止**使用正则表达式解析html。因为html很容易变化，造成解析不稳定。

## 研究与学习

1.在开发过程中多参考github上的优秀skills项目，比如：
- https://github.com/anthropics/skills
- https://github.com/openai/skills
- https://github.com/vercel-labs/skills

2.将学习到的经验存储在 `guides/` 目录，`Skills-Dev-Guide.md` 作为索引文件：

| 文件 | 内容 |
|------|------|
| [Skills-Dev-Guide.md](Skills-Dev-Guide.md) | 索引入口，含快速问答导航 |
| [guides/skill-structure.md](guides/skill-structure.md) | 目录结构、命名规范、SKILL.md 最小规范 |
| [guides/skill-quality-patterns.md](guides/skill-quality-patterns.md) | 高质量模式、提交前检查清单、常见反模式 |
| [guides/skill-template.md](guides/skill-template.md) | 可复用模板、description 写法参考 |
| [guides/dev-workflow.md](guides/dev-workflow.md) | 开发流程、部署步骤、持续演进建议 |
| [guides/openclaw-adaptation.md](guides/openclaw-adaptation.md) | Openclaw 门控、加载优先级、部署命令 |
| [guides/superpowers-architecture.md](guides/superpowers-architecture.md) | superpowers 项目分析：多平台适配、引导程序机制、可复用设计模式 |

3.学习过程中可以下载优秀的github项目至本地，研究项目代码。下载的github项目临时存储到`github_cache`目录

## 部署与测试

1.开发阶段
- 开发阶段的skills保存至`skills`目录

2.本地部署与远程部署参考`Deployment.md`
