# OpenAI Skills (Codex) 深度分析

来源：`github_cache/skills_repos/openai-skills/`（30+ skills）

---

## 一、仓库组织结构：三层分类

OpenAI Skills 采用三层目录分类，这是 Anthropic Skills 没有的：

```
skills/
├── .system/       # 自动预装，无需安装（skill-creator, skill-installer）
├── .curated/      # 精选推荐，可按名字安装
└── .experimental/ # 实验性，需指定完整路径安装
```

**对我们的启示**：可借鉴此分层策略管理自己的 skill 库，按成熟度分级。

---

## 二、最大差异：agents/ 目录（平台 UI 元数据）

OpenAI Skills 独有 `agents/openai.yaml`，这是**平台读取的配置**，不是 Agent 读取的指令：

```yaml
interface:
  display_name: "GitHub Address Comments"      # UI 显示名（人类可读）
  short_description: "Address comments in a GitHub PR review"  # 25-64字符
  icon_small: "./assets/github-small.svg"      # 小图标路径
  icon_large: "./assets/github.png"            # 大图标路径
  brand_color: "#3B82F6"                       # 品牌色
  default_prompt: "Address all actionable GitHub PR review comments..."  # 触发模板

dependencies:
  tools:
    - type: "mcp"
      value: "linear"
      description: "Linear MCP server"
      transport: "streamable_http"
      url: "https://mcp.linear.app/mcp"       # MCP 依赖声明
```

**三个关键用途**：
1. **UI 展示**：为 Codex 界面提供可读名称、图标、描述
2. **默认提示词**：点击 skill chip 时自动插入的 prompt
3. **依赖声明**：告诉平台这个 skill 需要哪些 MCP 服务器

**注意**：`agents/` 目录中的文件由平台机器读取，不由 Agent 读取。

---

## 三、frontmatter 新增字段：metadata

OpenAI Skills 的 frontmatter 比 Anthropic 多一个 `metadata` 字段：

```yaml
---
name: skill-creator
description: Guide for creating effective skills...
metadata:
  short-description: Create or update a skill   # 与 agents/openai.yaml 对应
---
```

这是向后兼容的冗余字段，方便在不读取 `agents/` 目录时也能获得简短描述。

---

## 四、Skill 命名规范（更严格）

| 原则 | 说明 | 示例 |
|------|------|------|
| 工具命名空间前缀 | 工具名 + 动作 | `gh-address-comments`, `gh-fix-ci` |
| 服务命名空间前缀 | 服务名 + 动作 | `notion-spec-to-implementation`, `linear` |
| 动词优先 | 动作在前 | `develop-web-game`, `screenshot`, `yeet` |
| 长度限制 | ≤ 64字符 | — |
| 字符集 | 小写字母+数字+连字符 | — |

**命名空间前缀的价值**：当多个 skill 操作同一服务时（如多个 notion-xxx），前缀帮助 Agent 快速定位正确的 skill。

---

## 五、跨 Skill 协作模式

`gh-fix-ci` 中明确调用另一个 skill：

```markdown
6. Create a plan.
   - Use the `create-plan` skill to draft a concise plan and request approval.
```

这是**技能链（Skill Chaining）**模式：
- 主 skill 负责领域逻辑（分析 CI 失败）
- 子 skill 负责通用能力（制定计划）
- 通过 `If a plan-oriented skill (for example create-plan) is available, use it` 实现软依赖

**对应模式**：Anthropic Skills 未出现此模式，这是 OpenAI Skills 的独特创新。

---

## 六、沙盒权限提升模式

多个 skill 涉及网络/系统权限，使用专门的权限提升语法：

```markdown
# skill-installer
All of these scripts use network, so when running in the sandbox,
request escalation when running them.

# gh-address-comments
Prereq: ensure `gh` is authenticated, then run `gh auth status`
with escalated permissions.
If sandboxing blocks `gh auth status`,
rerun it with `sandbox_permissions=require_escalated`.
```

**三种权限处理策略**：
1. **事前声明**：在 Overview 说明"此 skill 需要网络权限"
2. **动态检测**：发现失败后提示用户提升权限重试
3. **组合命令**：将权限检查和实际操作合并为一条命令，减少权限提示次数

---

## 七、Prerequisite Check（前置检查）模式

技术类 skill 普遍采用前置检查段落，放在正文最前面：

```markdown
## Prerequisite check (required)

Before proposing commands, check whether `npx` is available:
```bash
command -v npx >/dev/null 2>&1
```
If it is not available, pause and ask the user to install Node.js/npm.
```

**前置检查三件套**：
1. **工具检测**：`command -v xxx` 检查是否安装
2. **认证检测**：`gh auth status`、`codex mcp login xxx`
3. **失败处理**：明确告知安装步骤，然后**停止**（不继续执行）

---

## 八、Quick Start 前置模式

多个 skill 在 Overview/Workflow 之前提供 Quick Start：

```markdown
## Quick start
1) Locate the spec with `Notion:notion-search`, then fetch it with `Notion:notion-fetch`.
2) Parse requirements using `reference/spec-parsing.md`.
3) Create a plan page with `Notion:notion-create-pages`.
```

**价值**：熟悉该 skill 的高级用户可跳过详细说明，直接执行。

---

## 九、MCP 集成模式（Linear、Notion、Figma）

MCP 集成 skill 的统一结构：

```markdown
### Step 0: Set up [Service] MCP (if not already configured)

1. Add the MCP:
   - `codex mcp add linear --url https://mcp.linear.app/mcp`
2. Enable remote MCP client:
   - Set `[features] rmcp_client = true` or run `codex --enable rmcp_client`
3. Log in with OAuth:
   - `codex mcp login linear`

After successful login, tell the user to restart Codex.
```

**MCP Skill 四段式**：
1. **Step 0：MCP 未配置时的设置流程**（自动跳过已配置的情况）
2. **Available Tools 列表**：直接列出所有可用工具名
3. **Practical Workflows**：常见使用场景示例
4. **Troubleshooting**：常见错误和解决方案

---

## 十、进度跟踪文件模式（develop-web-game）

`develop-web-game` 创新性地引入了 `progress.md` 跨会话上下文保持机制：

```markdown
## Progress Tracking

Create a `progress.md` file if it doesn't exist, and append TODOs,
notes, gotchas, and loose ends as you go so another agent can pick up seamlessly.

If a `progress.md` already exists, read it first (you may be continuing another agent's work).
Do not overwrite the original prompt; preserve it.
At the end of your work, leave TODOs and suggestions for the next agent.
```

**progress.md 规范**：
- 第一行：`Original prompt: <完整原始请求>`（永不覆盖）
- 追加：每次有意义的工作后追加 TODOs / 决策 / 注意点
- 供下一个 Agent 继续工作时快速上手

**对我们的价值**：长期、多轮次的复杂任务 skill（如 A股分析）可借鉴此模式，保持跨对话的工作连续性。

---

## 十一、脚本路径动态解析模式

多个 skill 使用环境变量定位脚本，而不是硬编码路径：

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PWCLI="$CODEX_HOME/skills/playwright/scripts/playwright_cli.sh"
export WEB_GAME_CLIENT="$CODEX_HOME/skills/develop-web-game/scripts/web_game_playwright_client.js"
```

**优点**：
- 适配不同平台的安装路径
- 一次设置，多处复用
- 明确表达脚本来自 skill 目录，而非系统路径

---

## 十二、Guardrails 段落模式

`playwright` skill 有专门的 Guardrails 章节：

```markdown
## Guardrails

- Always snapshot before referencing element ids like `e12`.
- Re-snapshot when refs seem stale.
- Prefer explicit commands over `eval` and `run-code` unless needed.
- Default to CLI commands and workflows, not Playwright test specs.
```

**Guardrails 的特点**：
- 用 bullet list 而非段落
- 混合正向（"Always/Prefer"）和负向（"Do not/Never"）规则
- 聚焦于"最容易犯的错误"，不是全面的规范

---

## 十三、多 OS 支持模式（screenshot）

`screenshot` skill 针对三个平台分别给出指令：

```markdown
## macOS and Linux (Python helper)
python3 <path>/scripts/take_screenshot.py

## Windows (PowerShell helper)
powershell -ExecutionPolicy Bypass -File <path>/scripts/take_screenshot.ps1

## Direct OS commands (fallbacks)
### macOS: screencapture -x output/screen.png
### Linux: scrot output/screen.png
```

**层次化降级策略**：
1. 优先用平台专属 helper 脚本
2. 如 helper 失败，提供原生 OS 命令作为 fallback

---

## 十四、Skill 与 Anthropic Skills 的对比

| 维度 | Anthropic Skills | OpenAI Skills |
|------|-----------------|---------------|
| agents/ 目录 | 无 | 有（UI元数据 + MCP依赖声明） |
| 命名规范 | 通用 | 工具/服务命名空间前缀 |
| 跨 Skill 调用 | 无 | 有（软依赖，"if available, use it"） |
| MCP 集成 | 指导性 | 完整配套（Step 0 设置 + 依赖声明） |
| 进度跟踪 | 无 | progress.md 跨会话机制 |
| 权限管理 | 无 | 沙盒权限提升显式处理 |
| 前置检查 | 隐式 | 显式 Prerequisite Check 段落 |
| 仓库分层 | 无 | .system / .curated / .experimental |

---

## 十五、可直接复用到 OpenclawSkills 的模式

1. **MCP 集成 Step 0**：在使用任何 MCP 服务前，先检测是否配置，未配置时给出完整设置步骤
2. **Prerequisite Check**：技术型 skill 开头加依赖检查段落
3. **progress.md 模式**：长期分析 skill（如 a-share-review-planner）引入跨对话进度跟踪
4. **脚本路径变量化**：`export SKILL_DIR="$OPENCLAW_HOME/skills/a-share-review-planner"`
5. **Guardrails 段落**：在 skill 末尾加"禁止事项"bullet list
6. **命名空间前缀**：操作同一领域的多个 skill 用前缀区分（如 `ashare-trend-scan`, `ashare-news-fetch`）
