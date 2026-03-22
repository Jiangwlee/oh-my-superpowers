# OpenclawSkills

<p align="center">
  <strong>Openclaw 智能体技能仓库</strong><br>
  一系列专为金融数据抓取、分析与研究设计的 AI 智能体技能。
</p>

<p align="center">
  <a href="README.md">English</a> |
  <a href="README.zh.md">简体中文</a>
</p>

---

## 概述

本仓库包含为 Openclaw 平台开发的**智能体技能（Agent Skills）**套件。每个技能都是一个独立的模块，使 AI 智能体能够执行专业任务，从金融市场分析到多智能体协作。

所有技能遵循 [Agent Skills 规范](https://github.com/agentskills/agentskills)，并利用 Openclaw 的内置工具进行浏览器自动化、代码执行和数据处理。

## 仓库结构

```
packages/                          # 共享基础设施包
└── ashare-data/                   # A 股数据采集库（pip install -e）

skills/                            # 智能体技能（各自独立自治）
├── ashare-assistant/              # A 股交易助手
├── agent-roundtable/              # 多智能体协作框架
├── github-researcher/             # GitHub 趋势研究
├── markdown-to-anything/          # Markdown 转换工具
└── openclaw-github-tracker/       # GitHub 项目情报

deployment/                        # 部署文档和 Docker 配置
├── README.md                     # ashare-platform 部署入口
└── docker/
    └── ashare-platform/
        └── docker-compose.yml
```

`packages/` 存放 skill 共用的 Python 基础设施包；`skills/` 存放各 skill 本体，每个 skill 独立自治；`deployment/` 现在存放 `ashare-platform` 的部署入口文档和 Docker 配置。

---

## 可用技能

### 📈 A股交易助手 (`ashare-assistant`)

**用途**：每日 A 股收盘后的市场复盘与次日交易计划生成。

**主要功能**：
- 通过 `ashare-data` 包自动采集数据（新闻、资金流向、舆情、趋势扫描、券商账户）
- 5 阶段 LLM 流水线：情绪分析 → 复盘报告 → 候选股 → 个股深研 → 交易计划
- 风险检查与决策日志
- 策略演进跟踪

**触发关键词**：复盘、今日回顾、明日计划、选股、大盘分析、板块、涨停

**架构分层**：

| 层次 | 目录 | 职责 |
|------|------|------|
| 数据层 | `packages/ashare-data/` | 定时采集，写入 `raw/` + `filtered/` |
| 分析层 | `skills/ashare-assistant/` | LLM 驱动的复盘、选股、交易计划 |

数据流向：`ashare-data → ~/.ashare-assistant/data/{DATE}/filtered/ → ashare-assistant`

---

### 🔄 智能体圆桌讨论 (`agent-roundtable`)

**用途**：多智能体协作讨论框架。

**主要功能**：
- 协调外部智能体（codex、opencode 等）围绕共同话题协作
- 使用 JSONL 格式的持久化会话日志
- 背景注入，支持上下文丰富的讨论
- 自动编排与收敛检测

**触发关键词**："roundtable"、"agent roundtable"、"multi-agent discussion"

---

### 🔍 GitHub 研究员 (`github-researcher`)

**用途**：GitHub 趋势分析与仓库深度研究。

**主要功能**：
- 通过浏览器自动化每日采集 GitHub Trending
- 用户审批的观察清单管理
- 多引擎深度分析（claude → codex → Openclaw）
- 仓库更新历史跟踪
- 本地代码缓存支持离线分析

---

### 📊 OpenClaw GitHub 追踪器 (`openclaw-github-tracker`)

**用途**：为 OpenClaw 提供的 GitHub 项目情报工作流。

**主要功能**：
- 每日从 GitHub Trending 页面发现热门项目
- 用户驱动的观察清单管理
- 首次深度项目档案生成
- 关注仓库的重要更新跟踪
- 面向内存系统的机器友好索引

---

## 快速开始

### 环境要求

- Python 3.10+
- Openclaw 平台或兼容的智能体运行时

### 安装共享包

```bash
pip install -e packages/ashare-data
```

### 使用技能

每个技能都包含详细的 `SKILL.md` 文档：

```bash
cat skills/<skill-name>/SKILL.md
```

### 运行测试

```bash
# 运行所有测试
python -m unittest discover -s skills/ashare-assistant/tests -p "test_*.py"

# 语法检查
python -m py_compile <file.py>
```

---

## 开发指南

### 技术栈

- **语言**: Python 3.10+（优先使用标准库）
- **测试**: unittest / pytest
- **HTML 解析**: html.parser（禁止使用正则表达式）

### 代码风格

- 导入排序：标准库 → 第三方库 → 本地模块
- 类型注解：使用 `str | None` 而非 `Optional[str]`
- 命名规范：模块/函数使用 snake_case，类使用 PascalCase
- 文档字符串：Google 风格
- 错误处理：失败时返回空集合，不抛出异常

### 添加新技能

1. 在 `skills/<skill-name>/` 下创建新目录
2. 遵循目录结构：`scripts/`、`tests/`、`references/`、`SKILL.md`
3. 编写全面的测试
4. 更新本 README

### 添加新包

1. 在 `packages/<package-name>/` 下创建新目录
2. 添加 `pyproject.toml`，若需要 CLI 则配置 `[project.scripts]`
3. 通过 `pip install -e packages/<package-name>` 安装

---

## GitHub 研究

开发新技能时，避免重复造轮子。先研究现有解决方案：

```bash
gh search repos <topic> --sort stars
```

研究发现存储在 `github_cache/` 目录中，并通过 `INDEX.md` 建立索引以便快速查阅。

---

## 部署

详见 [Deployment.md](Deployment.md)。

```bash
# 本地部署
cp -r skills/<skill-name>/ .claude/skills/<skill-name>/

# 远程部署
scp -r skills/<skill-name>/ root@tencent-vps:/path/to/skills/
```

**注意**：始终只在 `skills/` 或 `packages/` 目录中修改源码，部署目录是只读副本。

---

## 参考资料

- [Agent Skills 规范](https://github.com/agentskills/agentskills)
- [Openclaw 工具文档](https://docs.openclaw.ai/tools/browser)
- [技能开发指南](Skills-Dev-Guide.md)
- [ashare-data 包文档](packages/ashare-data/README.md)

---

<p align="center">
  为 Openclaw 平台而构建
</p>
