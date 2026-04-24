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
├── brainstorming/            # 场景路由：S1 开放讨论 / S2 skill-agent / S3 feature
├── skill-review/             # Skill 目录质量审查
├── agent-review/             # Pi Agent markdown 文件审查
├── code-review/              # 本地未提交/未推送代码改动审查
├── debug/                    # 可复现 bug 的系统化根因调试
├── handoff/                  # /compact 前生成上下文交接文件
├── insight/                  # 项目记忆系统：recall / capture / evaluate / list
├── evolution/                # 基于跨项目使用数据演进 skills 与 CLAUDE.md
├── deep-research/            # 多轮、多源、带验证的深度研究
├── omp-agents/               # 把任务委托给 omp run 注册的 Pi Agent
├── team/                     # 一次性 tmux 派发到 claude/codex/pi
├── round-table/              # 多 runtime 角色化圆桌辩论
├── web-operator/             # Chrome CDP 浏览、搜索、内容抽取
├── media-editor/             # 为 media-editor agent 提供归档/查询/提升
├── llm-wiki/                 # 基于 omp wiki 的 Karpathy 风格 markdown wiki
└── markdown-to-anything/     # Markdown 转 PDF/PNG 等格式

agents/                       # Pi Agent 定义（+ agents.json 注册表）
├── reviewer.md               # 通用质量审查官（自动选择审查路径）
├── researcher.md             # 通用研究员（多轮深度研究）
├── oss-researcher.md         # 开源代码研究分析师
├── media-editor.md           # AI 领域媒体编辑（X.com / Reddit）
├── ux-engineer.md            # UX 工程师（前端审计 + 设计）
└── wps-assistant.md          # WPS 文档助理

cli/                          # typer CLI 模块（每个 tool 一个，由 omp <tool> 路由）
└── <tool>/main.py

bin/
└── omp                       # oh-my-superpowers CLI

docs/
├── specs/                    # 开发规范（稳定，长期有效）
│   ├── 00_skills/            # Skills 规范、最佳实践、设计模式
│   ├── 01_agents/            # Pi Agent 框架参考
│   └── 02_framework/         # 架构设计、安装规范
└── brainstorming/            # S3 设计文档（specs/）+ S1 讨论记录（discussions/）
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
# "我需要设计一个 skill"    → 路由到 S2（skill-agent 场景）
# "我需要设计一个 agent"    → 路由到 S2（skill-agent 场景）
# "加功能 X" / "重构 Y"    → 路由到 S3（产出设计文档与实现计划）
# "我们聊聊 / 探索一下 ..."  → 路由到 S1（开放讨论）
```

## 可用 Skills

| Skill | 模式 | 用途 |
|-------|------|------|
| `brainstorming` | Router + Pipeline | 场景路由（S1 开放讨论 / S2 skill-agent / S3 feature）；S3 为 feature 工作产出设计文档与实现计划 |
| `skill-review` | Reviewer + Pipeline | Skill 目录质量审查 |
| `agent-review` | Reviewer | Pi Agent markdown 文件的规范与设计审查 |
| `code-review` | Reviewer | 本地未提交/未推送代码改动的质量审查 |
| `debug` | Pipeline | 可复现 bug 的系统化根因调试 |
| `handoff` | Pipeline | `/compact` 前生成 `.handover.md` 与压缩指令 |
| `insight` | Pipeline | 项目记忆系统：recall / capture / evaluate / list |
| `evolution` | Pipeline | 基于跨项目使用数据演进 skills 与 CLAUDE.md |
| `deep-research` | Pipeline | 多轮、多源、带验证的深度研究 |
| `omp-agents` | Router | 通过 `omp run` 把任务委托给注册的 Pi Agent |
| `team` | Tool Wrapper | 一次性 tmux 派发任务到 claude/codex/pi |
| `round-table` | Tool Wrapper | 多 runtime 角色化圆桌辩论 |
| `web-operator` | Tool Wrapper | Chrome CDP 浏览器自动化、搜索、内容抽取 |
| `media-editor` | Pipeline | 为 media-editor agent 提供归档/查询/提升能力 |
| `llm-wiki` | Pipeline + Tool Wrapper | 基于 `omp wiki` 的 Karpathy 风格 markdown wiki 工作流 |
| `markdown-to-anything` | Pipeline | Markdown 转 PDF、PNG 等格式 |

## 可用 Agents

定义在 `agents/`，由 `agents/agents.json` 注册（绑定默认模型与 skill 集合）。

| Agent | 角色 | 用途 |
|-------|------|------|
| `reviewer` | 通用质量审查官 | 根据被审对象自动选择 skill-review / agent-review / code-review |
| `researcher` | 通用研究员 | 多轮跨源研究、事实归纳、观点梳理 |
| `oss-researcher` | 开源代码研究分析师 | 解答开源项目实现问题，沉淀分层 Obsidian 知识库 |
| `media-editor` | AI 领域媒体编辑 | 探索 X.com / Reddit AI 内容，归档生成简报 |
| `ux-engineer` | UX 工程师 | 前端 UI 审计与设计（基于 impeccable skill 集合）|
| `wps-assistant` | WPS 文档助理 | 在 WPS / 金山文档空间内定位文档与回答问题 |

## omp 命令

```
omp install <skill|agent> <name> [--global]   安装 skill 或 agent（symlink）
omp remove  <skill|agent> <name> [--global]   卸载
omp list    [skill|agent] [--global]          列出已安装 skills 与 agents
omp run     <agent> [--model M] [--mode …] <prompt>
                                              运行 Pi Agent（text/stream/json/interactive）
omp test    skill <name>                      运行 skill 的 T1 静态测试
omp upgrade                                   拉取最新版并重新注册命令
```

Tool 子命令（每个路由到 `cli/<tool>/main.py`，使用 `omp <tool> --help` 查看）：

```
omp deep-research         初始化与构建 deep-research 工作区
omp evolution             扫描 sessions / 查看演进历史
omp handoff               compaction lifecycle 上下文交接
omp insight               从 AI 对话中提取 memory 并提炼洞察
omp media-editor          归档 / 查询 / 提升 media items
omp round-table           多 AI 圆桌讨论
omp skill-review          skill 目录的机械一致性检查
omp team                  一次性 tmux agent 编排
omp web-operator          浏览器自动化、搜索、内容抽取
omp wiki                  Karpathy 风格 markdown wiki
```

Skill 安装为 symlink，同时写入 `.agents/skills/`（Pi）和 `.claude/skills/`（Claude Code）。
Agent 通过 `omp install agent <name>` 安装（同样基于 symlink）。

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
