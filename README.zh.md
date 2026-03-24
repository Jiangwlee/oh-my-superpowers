# oh-my-superpowers

<p align="center">
  <strong>Pi Agent + Skills 开发套件</strong><br>
  用于构建、审查和部署 Pi / Claude Code Agent Skills 的开发框架。
</p>

<p align="center">
  <a href="README.md">English</a> |
  <a href="README.zh.md">简体中文</a>
</p>

---

## 概述

oh-my-superpowers 聚焦两件事：

1. **Skills** — 独立的工具封装单元，给 Agent 提供真实能力
2. **Agents** — 有身份的角色，由 Skills 驱动完成任务

本项目提供元 Skills、开发规范和 CLI 工具，覆盖 Skill/Agent 的设计、构建、审查和安装全流程。

## 项目结构

```
skills/                       # Skill 单元（各自独立）
├── agent-brainstorming/      # Agent 设计工作流
├── skill-brainstorming/      # Skill 设计工作流
├── skill-review/             # Skill 质量审查工具
└── markdown-to-anything/     # Markdown 转 PDF/PNG 等格式

agents/                       # Pi Agent 定义
└── skill-review.md           # Skill 质量审查官

bin/
└── omp                       # oh-my-superpowers CLI

docs/
├── specs/                    # 开发规范（稳定，长期有效）
│   ├── 00_skills/            # Skills 规范、最佳实践、设计模式
│   ├── 01_agents/            # Pi Agent 框架参考
│   └── 02_framework/         # 架构设计、安装规范
└── design/                   # 设计文档（brainstorming 输出）
```

## 快速开始

### 安装

```bash
# Bootstrap：将项目 symlink 到 ~/.oh-my-superpowers，注册 omp 命令
./install.sh
```

### 安装 Skill

```bash
# 局部安装（当前项目）
omp install skill skill-review
omp install skill agent-brainstorming

# 全局安装（所有项目可用）
omp install skill skill-review --global
```

### 查看已安装的 Skills

```bash
omp list           # 局部
omp list --global  # 全局
```

### 设计新 Skill 或 Agent

```bash
# 在 Claude Code 或 Pi 中触发对应工作流
# "我需要设计一个 skill"   → skill-brainstorming 激活
# "我需要设计一个 agent"   → agent-brainstorming 激活
```

## 可用 Skills

| Skill | 模式 | 用途 |
|-------|------|------|
| `agent-brainstorming` | Inversion + Pipeline | Agent 设计工作流（含身份审问门控） |
| `skill-brainstorming` | Inversion + Pipeline | Skill 设计工作流（含模式选择门控） |
| `skill-review` | Reviewer + Pipeline | Skill 目录质量审查 |
| `markdown-to-anything` | Pipeline | Markdown 转 PDF、PNG 等格式 |

## 可用 Agents

| Agent | 角色 | 用途 |
|-------|------|------|
| `skill-review` | Skill 质量审查官 | 全面审计 Skill 目录：规范合规性、设计质量、证据质量 |

## omp 命令

```
omp run   agent <name> --model <m> <prompt>   运行 Pi Agent（实时流式输出）
omp list  [--global]                          列出已安装 Skills 和可用 Agents
omp install skill <name> [--global]           安装 Skill（局部或全局）
omp remove  skill <name> [--global]           卸载 Skill
omp test skill <name>                         运行 Skill 的 T1 测试
omp help                                      显示帮助
```

Skill 安装为 symlink，同时写入 `.agents/skills/`（Pi）和 `.claude/skills/`（Claude Code）。
Agent 直接从源码运行，无需安装步骤。

## 架构

四层模型，职责分明：

```
Tools/Scripts   CLI 化的可执行单元（bash/python/node）
    ↑
Skills          SKILL.md + references/ — 告知 Agent WHEN 和 WHAT
    ↑
Agents          Pi frontmatter + system prompt — 有身份的角色编排
    ↑
CLI             omp — 安装、卸载、测试
```

**Agent 身份原则**：Agent 必须能映射到一个明确的角色（职业/职能）。如果无法回答"你是谁？"，它是 Skill，不是 Agent。

完整设计见 [docs/specs/02_framework/architecture.md](docs/specs/02_framework/architecture.md)。

## 开发

设计前必读：
- Skills：[docs/specs/00_skills/README.md](docs/specs/00_skills/README.md)
- Agents：[docs/specs/01_agents/README.md](docs/specs/01_agents/README.md)
- 框架：[docs/specs/02_framework/README.md](docs/specs/02_framework/README.md)

### 技术栈

| 层 | 技术 |
|----|------|
| 脚本 | Bash / Python 3.10+ / Node.js or Bun |
| 测试 | unittest/pytest（T1）· `pi -p` / `claude -p`（T2 E2E）· LLM-as-judge（T3）|
| 包管理 | uv（Python）· npm or bun（Node）|
| Agent 运行时 | Pi（核心）· Claude Code（开发辅助）|
| 安装 | symlink via omp |
