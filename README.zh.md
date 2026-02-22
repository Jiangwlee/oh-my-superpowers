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

## 可用技能

### 📈 A股复盘与交易计划 (`a-share-review-planner`)

**用途**：每日 A 股收盘后的市场复盘与次日交易计划生成。

**主要功能**：
- 多源数据采集（新闻、板块资金流向、市场情绪、趋势扫描）
- 五阶段结构化分析工作流
- 自动生成 PDF 报告并通过 Telegram 推送
- 风险检查与决策验证
- 策略演进跟踪

**触发关键词**："复盘"、"今日回顾"、"明日计划"、"选股"、"大盘分析"、"板块"、"涨停"

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

## 快速开始

### 环境要求

- Python 3.10+
- Openclaw 平台或兼容的智能体运行时

### 目录结构

```
skills/
├── a-share-review-planner/    # A股 市场分析
├── agent-roundtable/          # 多智能体协作
├── github-researcher/         # GitHub 研究工作流
└── openclaw-github-tracker/   # GitHub 项目情报
```

### 使用技能

每个技能都包含详细的 `SKILL.md` 文档：

```bash
# 阅读技能文档
cat skills/<skill-name>/SKILL.md

# 运行技能测试
python -m unittest discover -s skills/<skill-name>/tests -p "test_*.py"
```

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

### 测试

```bash
# 运行所有测试
python -m unittest discover -s skills -p "test_*.py"

# 运行特定技能测试
python -m unittest skills.a_share_review_planner.tests.test_taoguba_fetchers

# 语法检查
python -m py_compile <file.py>
```

### 添加新技能

1. 在 `skills/<skill-name>/` 下创建新目录
2. 遵循目录结构：`scripts/`、`tests/`、`references/`、`SKILL.md`
3. 编写全面的测试
4. 更新本 README

## GitHub 研究

开发新技能时，避免重复造轮子。先研究现有解决方案：

```bash
# 搜索相关项目
gh search repos <topic> --sort stars

# 缓存项目以供深度分析
# （参见 github-researcher 技能的工作流）
```

研究发现存储在 `github_cache/` 目录中，并通过 `INDEX.md` 建立索引以便快速查阅。

## 部署

技能部署到智能体特定的目录：

```bash
# 本地部署
cp -r skills/<skill-name>/ .claude/skills/<skill-name>/
cp -r skills/<skill-name>/ .agents/skills/<skill-name>/

# 远程部署
scp -r skills/<skill-name>/ user@host:/path/to/skills/
```

**注意**：始终只在 `skills/` 目录中修改源码。部署目录是只读副本。

## 贡献指南

1. Fork 本仓库
2. 创建功能分支
3. 遵循 `AGENTS.md` 中的编码规范
4. 为新功能编写测试
5. 提交 Pull Request

## 许可证

[在此添加许可证信息]

## 参考资料

- [Agent Skills 规范](https://github.com/agentskills/agentskills)
- [Openclaw 工具文档](https://docs.openclaw.ai/tools/browser)
- [技能开发指南](Skills-Dev-Guide.md)

---

<p align="center">
  为 Openclaw 平台而构建
</p>
