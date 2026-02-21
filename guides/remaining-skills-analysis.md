# 剩余 5 个 Skills 项目深度分析

来源：`github_cache/skills_repos/`（vercel-labs-skills / github-explorer-skill / instagit / MinerU-PDF-parser-openclaw-skill / x-research-skill）

---

## 一、vercel-labs-skills — Skills 生态的包管理器

### 本质

这不是一个 skill 集合，而是整个 skills 生态的 **CLI 包管理工具**（`npx skills`）。
它自带 1 个 meta-skill（`find-skills`），核心价值在于：
1. 跨 40+ AI 平台安装/管理 skills
2. 定义了 skills 生态的标准发布协议

### 多平台适配架构

两类 agent 目录策略：

| 类型 | Skills 目录 | 代表 Agent |
|------|-------------|-----------|
| **Universal** | `.agents/skills/`（共享） | OpenCode, Codex, Amp, Gemini-CLI, GitHub Copilot |
| **Non-Universal** | Agent 专属目录（符号链接） | Claude Code (`.claude/skills/`), OpenClaw (`skills/`), Cursor, Windsurf |

**OpenClaw 的特殊路径检测**（按优先级）：
```
~/.openclaw/skills  → ~/.clawdbot/skills  → ~/.moltbot/skills
```

### 安装模式：符号链接 vs 拷贝

- **推荐**：符号链接（`--copy` 不加即为 symlink）
  → 单一真实源，所有 agent 共享同一份 skill 文件，更新时一处修改即生效
- **备选**：拷贝（`--copy` 标志）
  → 独立副本，适合符号链接不支持的环境（如某些 Docker 配置）

### Plugin Manifest 发现协议

skill 仓库中可放 `.claude-plugin/` 目录来声明 skills 的位置：

```json
// .claude-plugin/marketplace.json（多 plugin 目录）
{
  "metadata": { "pluginRoot": "./plugins" },
  "plugins": [
    { "source": "./skill-a", "skills": ["./SKILL.md"] },
    { "source": "./skill-b" }
  ]
}

// .claude-plugin/plugin.json（单 plugin）
{
  "skills": ["./SKILL.md"]
}
```

**安全保护**：路径遍历攻击防护 —— 所有路径必须以 `./` 开头，且严格检查是否 containedIn 根目录。

### find-skills：Meta-Skill 模式

description 完整示例（覆盖多种用户触发句式）：
```
Helps users discover and install agent skills when they ask questions like
"how do I do X", "find a skill for X", "is there a skill that can...",
or express interest in extending capabilities.
```

**关键设计**：description 枚举了 5+ 种用户说话方式（问句 + 陈述 + 感叹），最大化触发覆盖率。

### 技能发现 CLI 流程（find-skills skill 内容）

```
理解需求 → npx skills find [query] → 展示结果 + 安装命令 + skills.sh 链接 → 提议安装
```

"无结果时"的兜底处理（避免体验断崖）：
```
未找到相关 skill → 用一般能力直接协助 → 建议用 `npx skills init` 自建
```

---

## 二、github-explorer-skill — 生产级调研 Skill 的完整范本

### 整体架构

这是本次研究中结构最复杂、工程化程度最高的单一 skill：

```
github-explorer-skill/
└── SKILL.md    # 自包含，但引用了外部 skills 作为依赖
```

### 独特模式一：跨 Skill 依赖声明表

在 skill 末尾用表格明确声明依赖关系：

```markdown
## Dependencies

| 依赖 | 类型 | 用途 |
|------|------|------|
| `web_search` | 内置工具 | Brave Search 检索 |
| `search-layer` | Skill | 多源搜索 + 意图感知评分 |
| `content-extract` | Skill | 高保真内容提取（反爬站点降级方案） |
```

**意义**：相比 OpenAI skills 的软依赖（"if available, use it"），这是更强的**显式依赖声明**，让用户在安装时就知道需要哪些前置 skill。

### 独特模式二：SPA 反模式警告 + 强制 API 规则

```markdown
**⚠️ GitHub 页面抓取规则（强制）**：
GitHub repo 页面是 SPA（客户端渲染），`web_fetch` 只能拿到导航栏壳子，
**禁止用 web_fetch 抓 github.com 的 repo 页面**。一律使用 GitHub API。
```

这是一个**技术陷阱警告**模式：提前指出"看起来能用但其实不行"的做法，并给出正确替代方案。

### 独特模式三：分级降级协议（Extraction Upgrade）

遇到以下情况时，必须从 `web_fetch` 升级为 `content-extract`：
1. **域名黑名单**：微信/知乎/小红书
2. **结构复杂**：大量 LaTeX 公式、复杂表格
3. **内容缺失**：返回空内容或 Challenge 页面

```
web_fetch → content-extract → MinerU-HTML（最终 fallback）
```

**设计价值**：LLM 不需要知道降级的技术细节，只需遵循规则，底层 skill 负责实现。

### 独特模式四：输出自检清单（强制前置）

在输出报告前必须逐条检查：

```markdown
## ⚠️ 输出自检清单（强制，每次输出前逐条核对）

- [ ] 标题链接：`# [Project Name](GitHub URL)` 格式，可点击跳转
- [ ] 标题空行：每个粗体标题前后各有一个空行
- [ ] Telegram 空行：列表末尾与下一标题之间有盲文空格 ⠀ 行
- [ ] Issue 链接：精选 Issue 每条都有完整 `[#号 标题](完整URL)` 格式
- [ ] 竞品链接：每个竞品都附 `[名称](GitHub/官网链接)`
- [ ] 无空泛描述：没有"评价很高"等概括性描述
```

这是 **output verification checklist** 模式，确保 LLM 不会漏掉格式要求（类似 superpowers 的 `verification-before-completion`）。

### 独特模式五：Telegram 渲染修复

发现 Telegram 会吞掉列表末尾的空行，用盲文空格（U+2800）解决：

```markdown
- 列表最后一项

⠀
**下一个标题**
```

**启示**：为特定输出渠道的渲染 bug 提供内嵌修复方案，而不是依赖用户手动处理。

### 独特模式六：意图感知搜索集成

```bash
python3 skills/search-layer/scripts/search.py \
  --queries "<project> review" \
  --mode deep \
  --intent exploratory \
  --num 5
```

search-layer v2 根据 `--intent` 类型使用不同的评分权重，7 种意图类型：
`factual` / `status` / `comparison` / `tutorial` / `exploratory` / `news` / `resource`

---

## 三、x-research-skill — CLI 驱动的 agentic 搜索范本

### 设计哲学

所有搜索操作通过独立 CLI 工具执行，LLM 扮演**策略决策者**而非**执行者**：

```
LLM: 分解问题 → 选择参数 → 解读结果
CLI: bun run x-search.ts [command] [options]  ← 实际执行层
```

### Skill 文件结构

```
x-research-skill/
├── SKILL.md        # 研究策略 + CLI 用法
├── x-search.ts     # CLI 入口（TypeScript）
├── lib/
│   ├── api.ts      # X API 封装
│   ├── cache.ts    # 15分钟文件缓存
│   └── format.ts   # Telegram + Markdown 格式化
├── data/
│   ├── watchlist.json   # 监控账号列表
│   └── cache/           # 自动管理的缓存目录
└── references/
    └── x-api.md         # X API 端点参考（不放在 SKILL.md 里）
```

### CLI 命令设计

| 命令 | 功能 |
|------|------|
| `search` | 关键词搜索，支持 `--sort`、`--since`、`--min-likes` 等过滤 |
| `profile` | 用户主页最新推文 |
| `thread` | 完整对话线程（by root tweet ID）|
| `tweet` | 单条推文详情 |
| `watchlist` | 账号监控列表管理 + 批量检查 |
| `cache clear` | 清除缓存 |

**Quick Mode**（`--quick`）：1页 + 最多10条 + 自动噪音过滤 + 1小时缓存 + 成本摘要 → 常规查询默认用此模式。

### 研究循环（Agentic Research Loop）

```
1. 分解问题 → 3-5 个搜索查询
2. 执行搜索 → 评估信噪比 → 调整参数
3. 追踪高质量线程（thread 命令）
4. 深入挖掘链接内容（web_fetch）
5. 按主题分组综合 → 保存到 drafts/
```

### Watchlist + Heartbeat 模式

维护一个关键账号列表，在定时任务（heartbeat）中批量检查：

```bash
bun run x-search.ts watchlist check   # 检查所有监控账号的最新动态
```

**设计原则**：只在内容"真正有趣/可操作"时才汇报，避免噪音报告。

### 噪音过滤启发式规则

```markdown
- 太多噪音？→ 加 `-is:reply`，用 `--sort likes`，缩窄关键词
- 太少结果？→ 用 OR 扩展，去掉限制性操作符
- 加密垃圾？→ 加 `-$ -airdrop -giveaway -whitelist`
- 只要专家观点？→ 用 `from:` 或 `--min-likes 50`
- 只要实质内容？→ 搜索 `has:links`
```

### 引用格式规范

```markdown
### [主题标题]

[1-2句总结]

- @username: "[关键引用]" (NL, NI) [Tweet](url)
```

NL = likes 数，NI = impressions 数 → 用量化数据替代"评价很高"等空泛表述。

---

## 四、MinerU-PDF-parser-openclaw-skill — 最小化工具封装范本

### 设计特点

极简主义：这个 skill 只做一件事（PDF 解析），内容精炼到极致：

```
MinerU-PDF-parser-openclaw-skill/
├── SKILL.md              # 极简概述 + Quick Start + 引用条件
├── references/
│   └── mineru-cli.md     # CLI 参数文档
└── scripts/
    └── mineru_parse.sh   # 可配置的封装脚本（200行）
```

### 条件引用声明

```markdown
## When to read references
If flags differ from your wrapper or you need advanced defaults
(backend/method/device/threads/format mapping), read:
- `references/mineru-cli.md`
```

明确告诉 LLM **只在遇到特定问题时才读 reference file**，而不是每次都加载。这是三层渐进加载原则的完美实践。

### 全环境变量覆盖模式

脚本中所有 CLI 标志都有对应的环境变量覆盖：

```bash
MINERU_CMD=~/.local/bin/mineru       # 命令路径
MINERU_INPUT_FLAG=-p                  # 输入标志
MINERU_OUTPUT_FLAG=-o                 # 输出标志
MINERU_FORMAT_FLAG=--format           # 格式标志
MINERU_FORMAT_VALUE_MD=markdown       # 格式值
MINERU_EXTRA_ARGS=...                 # 额外参数
```

**价值**：不同 MinerU 安装版本可能 flag 不同，环境变量覆盖让脚本适配任何安装，无需修改脚本本身。

### 脚本工程化标准（可复用）

```bash
#!/usr/bin/env bash
set -euo pipefail  # 严格模式：遇错退出、未定义变量报错、管道失败报错

# 先检查命令是否存在
if ! command -v "$cmd" >/dev/null 2>&1; then
  echo "MinerU CLI not found: $cmd" >&2
  exit 1
fi
```

这个脚本是**工具型 skill 的标准封装模板**：详细的 `--help`、完整的环境变量覆盖、严格模式、明确的错误提示。

---

## 五、instagit (analyze-git-repo) — MCP 服务型 Skill 范本

### 独特之处：MCP Server + Skill 双形态

```
instagit/
├── skills/
│   └── analyze-git-repo/
│       ├── SKILL.md           # Skill 内容（LLM 读）
│       └── references/
│           └── examples.md   # 详细 prompting 示例
├── server.json                # MCP 服务清单（平台/注册表读）
└── src/                       # MCP Server 实现
```

**server.json**（MCP 服务清单）：
```json
{
  "name": "io.github.instagitai/instagit",
  "description": "MCP server for Instagit — AI-powered Git repository analysis",
  "packages": [{
    "registryType": "npm",
    "identifier": "instagit",
    "transport": { "type": "stdio" },
    "environmentVariables": [{
      "name": "INSTAGIT_API_KEY",
      "isRequired": false
    }]
  }]
}
```

这类似 OpenAI skills 的 `agents/openai.yaml`，但面向的是 MCP 注册表（而非 Codex UI）。

### 零摩擦上手设计

```json
{
  "mcpServers": {
    "instagit": {
      "command": "npx",
      "args": ["-y", "instagit@latest"]
    }
  }
}
```

**无需 API key** — 首次使用时自动注册匿名 token，存储在 `~/.instagit/token.json`。

**设计原则**：降低初始摩擦（zero-config start），再通过升级路径引导用户注册（pay wall 后置）。

### 定价信息内嵌 Skill

```markdown
## Pricing
- **FREE:** $0 forever — 2M tokens/mo, standard speed, public repos
- **PRO:** $20/mo — 20M tokens/mo, fast mode
- **MAX:** $200/mo — 40M tokens/mo, reasoning model
```

在 skill 里直接说明定价层级，让 LLM 能告知用户升级路径（而非让用户自己去网站查）。

### 多客户端安装说明

单一 Quick Start 段覆盖所有主流客户端（Claude Code、Claude Desktop、Cursor、VS Code），使用同一份 JSON 配置——因为 MCP 协议是标准化的。

### Prompting Examples 分离到 references/

```markdown
For detailed examples across architecture, integration, debugging, migration,
security, and code quality — see [references/examples.md](references/examples.md).
```

**原因**：examples.md 内容多且稳定，不需要每次触发 skill 就加载。SKILL.md 只展示最关键的 3 个示例。

---

## 六、跨项目发现：新模式汇总

| 模式 | 来源 | 描述 |
|------|------|------|
| **依赖声明表** | github-explorer | 用表格明确声明依赖的 skill + 内置工具，比软依赖更显式 |
| **SPA 陷阱警告** | github-explorer | 提前标注"看起来能用但其实不行"的技术坑 |
| **分级降级协议** | github-explorer | web_fetch → content-extract → MinerU 自动降级链 |
| **输出自检清单** | github-explorer | 输出前必须逐条核对的强制 checklist |
| **渠道渲染修复** | github-explorer | 针对特定平台（Telegram）的渲染 bug 内嵌修复 |
| **意图感知搜索** | github-explorer | `--intent` 参数按任务类型调整搜索评分权重 |
| **Watchlist + Heartbeat** | x-research | 维护监控账号列表 + 定时触发检查 |
| **CLI 驱动研究循环** | x-research | LLM 做策略，CLI 做执行，研究结果存档到 drafts/ |
| **全环境变量覆盖** | MinerU | 所有 CLI flag 都有对应 env var，适配不同安装环境 |
| **条件引用声明** | MinerU | "When to read references" 明确加载时机 |
| **MCP + Skill 双形态** | instagit | `server.json`（平台读）+ `SKILL.md`（LLM 读）并存 |
| **零摩擦上手** | instagit | 自动注册匿名 token，无需 API key 即可使用 |
| **定价内嵌 Skill** | instagit | skill 中说明免费/付费层级，让 LLM 能引导升级 |
| **Universal / Non-Universal 分层** | vercel-labs | 共享目录 vs 专属目录 + 符号链接的多平台安装策略 |
| **Plugin Manifest 协议** | vercel-labs | `.claude-plugin/` 目录声明 skill 路径，支持多 plugin 目录 |
| **Meta-Skill（find-skills）** | vercel-labs | 用于发现和安装其他 skills 的 skill，兜底处理"无结果"场景 |

---

## 七、可直接复用到 OpenclawSkills 的模式

1. **输出自检清单**：a-share-review-planner 的分析报告末尾加 Pre-flight Checklist，确保 LLM 输出前核对链接/格式
2. **分级降级协议**：网页抓取失败时明确降级路径（web_fetch → browser → 报错）
3. **依赖声明表**：在需要外部工具的 skill 里加 Dependencies 表格
4. **Watchlist + Heartbeat**：选股基础池（东方财富人气榜前200）可用 watchlist 模式维护和监控
5. **全环境变量覆盖**：封装 a-share-trend-scanner 脚本时，所有路径/参数通过环境变量注入
6. **CLI 快速模式**（`--quick`）：分析类 skill 提供"快速模式"（简版报告），适合日常粗筛场景
7. **条件引用声明**：skill 中明确写"在 X 情况下才需要读 references/X.md"，减少默认加载量
