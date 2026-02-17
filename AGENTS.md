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

2.将学习到的经验存储在：`Skills-Dev-Guide.md`

3.学习过程中可以下载优秀的github项目至本地，研究项目代码。下载的github项目临时存储到`github_cache`目录

## 部署与测试

1.开发阶段
- 开发阶段的skills保存至`skills`目录

2.部署与测试
- 将待测试的skills拷贝至当前主机Openclaw skills目录: `/Users/mindora/clawd/skills`
- 重启Openclaw Gateway: `openclaw gateway restart`
