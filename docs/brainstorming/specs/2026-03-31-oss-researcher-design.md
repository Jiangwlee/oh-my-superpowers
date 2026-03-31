# oss-researcher Agent 设计

一个 Pi Agent，接收关于开源项目的自然语言问题，定位源码，提炼答案，沉淀为 Obsidian 分层知识库。

## Contents

- [设计方案](#设计方案)
  - [Agent 身份](#agent-身份)
  - [Skill 依赖](#skill-依赖)
  - [五阶段工作流](#五阶段工作流)
  - [Obsidian 文档结构](#obsidian-文档结构)
  - [文档格式规范](#文档格式规范)
- [行动原则](#行动原则)
- [行动计划](#行动计划)
  - [文件结构](#文件结构)
  - [任务分解](#任务分解)

---

## 设计方案

### Agent 身份

- **角色**：开源代码研究分析师
- **专业领域**：针对特定开源项目的实现机制问题，从源码提炼可复用的知识文档
- **判断点**：
  - 从问题关键词推断目标 GitHub repo（无法枚举所有项目名变体）
  - 决定分析深度（哪些文件/章节与问题相关，何时停止）
  - 判断已有文档是否足够新鲜，是否需要重新分析
- **签名输出**：Obsidian L3 问题答案文档 + 精简结论（3-5 句，附文档路径）

**Pi Frontmatter：**

```yaml
---
name: oss-researcher
description: >-
  Use when you have a specific question about how an open-source project works
  (architecture, implementation details, specific feature).
  Do NOT use when you want general documentation lookup, web search,
  or broad technology comparisons.
tools: bash, read, write, grep, ls
model: claude-sonnet-4-6
---
```

**Trigger Eval：**
- 应触发：`"pi coding agent 如何实现 skill 加载？"` / `"langchain memory 模块怎么设计的？"`
- 不应触发：`"什么是 RAG？"` / `"python 有哪些好的 web 框架？"`

---

### Skill 依赖

无外部 Skill 依赖。

`obsidian-markdown` 是 `~/.claude/skills/` 下的 Claude Code skill，Pi runtime 无法通过 `@skills/` 路径加载。Obsidian 格式规范（frontmatter、wikilinks、callouts）直接内联在 agent system prompt 中作为"文档规范"章节。

**`agents.json` 注册：**

```json
"oss-researcher": {
  "agent": "@agents/oss-researcher.md",
  "model": "claude-sonnet-4-6"
}
```

---

### 五阶段工作流

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4
 解析       Registry   代码获取   渐进分析   写入 Vault
```

**Phase 0：查询解析**

从用户输入提取：
- `project_keywords`：用于匹配 registry（如 "pi coding agent" → `pi-mono`）
- `question_slug`：问题语义 slug（如 "如何实现 skill 加载" → `skill-loading`）

**Phase 1：Registry 查询**

读 `~/Obsidian/OSS Research/_registry.md`：

```
命中 → 获取本地路径 + 上次 commit hash → Phase 2
未命中 → 推断 GitHub URL → 输出给用户确认 → 写入 registry → Phase 2
       （headless 场景：无用户确认时，使用推断 URL 继续，不写 registry，
         在最终输出中提示用户手动确认并补充 registry 条目）
```

**Phase 2：代码获取 + 新鲜度检查**

```bash
# 未 clone
git clone <url> ~/Github/<repo-name>

# 已 clone
cd ~/Github/<repo-name> && git pull
CURRENT=$(git log -1 --format=%H)
```

对比 `CURRENT` 与 registry commit：
- 相同 → 直接读 Vault 已有文档，跳过分析
- 不同 → 将相关文档标记为 `status: stale` → Phase 3

**Phase 3：渐进式分析（三步披露）**

```
Step A: 读所有已有文档的 frontmatter（不读正文）
        → 获得 layer/scope/status 映射

Step B: 读相关文档的 ## Contents（TOC）
        → 判断哪些章节需要深入

Step C: 按需读具体章节 + 代码文件
        → 仅读与问题直接相关的最小文件集
```

约束：
- 缺少 L1 时，必须先建 L1 概览文档再继续（**不可跳层**）
- 超出分析范围时，强制输出"分析边界"说明未覆盖的范围

**Phase 4：写入 Vault**

按需创建或更新 L1/L2/L3 文档，更新 registry commit hash，输出结论：

```
✓ 已分析 pi-mono @ commit a3f1c2
答案：...（核心结论，3-5 句）
文档：~/Obsidian/OSS Research/pi-mono/qa/skill-loading.md
```

---

### Obsidian 文档结构

```
~/Obsidian/OSS Research/
├── _registry.md                        ← 项目映射表（全局唯一）
├── <project>/
│   ├── overview.md                     ← L1：项目概览（一次性建立）
│   ├── modules/
│   │   └── <module>.md                 ← L2：模块分析（按需建立，可复用）
│   └── qa/
│       └── <slug>.md                   ← L3：具体问题答案
└── ...
```

**`_registry.md` 格式：**

```markdown
# OSS Research Registry

| project | keywords | github_url | local_path | commit |
|---------|----------|------------|------------|--------|
| pi-mono | pi coding agent, pi-mono | github.com/xxx/pi-mono | ~/Github/pi-mono | a3f1c2 |
```

---

### 文档格式规范

所有三层文档共同约束：
1. **frontmatter 必须**包含：`project`, `layer`, `scope`, `status`（fresh/stale）, `commit`, `date`, `tags`
2. **正文第一节必须是 `## Contents`**（TOC），供渐进式披露 Step B 使用
3. **wikilinks** 用于层间引用：L3 必须链接对应 L2，L2 必须链接 L1
4. **callouts** 标记两类特殊内容：
   - `> [!note] Key Finding` — 回答问题的关键代码或逻辑
   - `> [!warning] 分析边界` — 本次未覆盖的范围

**L1 概览（`overview.md`）核心章节：**
Architecture · Core Modules · Entry Points · Tech Stack

**L2 模块（`modules/<module>.md`）核心章节：**
Overview · Data Flow · Key Data Structures · Source References

**L3 问答（`qa/<slug>.md`）核心章节：**
Answer · Evidence · Limitations

---

## 行动原则

### 1. Zero-Context Entry（零上下文入口）[默认]

每个文档前 20 行（frontmatter + TOC）必须让读者无需任何外部知识即可判断相关性。这是渐进式披露的物理基础。

**禁止：** 文档无 frontmatter；文档无 ## Contents；正文没有结构。

### 2. Break, Don't Bend（断裂优于弯曲）[默认]

registry 记录错误时，直接修正条目，不建兼容层。stale 文档直接重写，不做版本叠加。

**禁止：** 保留旧文档内容并追加新内容；用注释区分新旧分析。

### 3. Minimum Blast Radius（最小影响半径）[任务专属]

每次运行只回答一个具体问题，只更新受影响的文档层级。不在单次运行中重写整个项目的知识库。

**禁止：** 单次运行重建多个不相关的 L2 文档；借问题入口批量更新未过期的文档。

### 4. Progressive Disclosure（渐进式披露）[任务专属]

分析从元数据开始，逐层深入，不一次性读取全部内容。每一步的深入必须有上一步的判断依据。

**禁止：** 未读 frontmatter 直接 grep 源码；未读 TOC 直接读全文；未建 L1 直接写 L3。

---

## 行动计划

### 文件结构

```
agents/
└── oss-researcher.md              ← 新建：Pi Agent 定义

agents/agents.json                 ← 修改：注册 oss-researcher

skills/omp-agents/references/      ← 修改：更新 Agent 速查表

~/Obsidian/OSS Research/
└── _registry.md                   ← 新建：初始化空 registry
```

### 任务分解

**Task 1：创建 `agents/oss-researcher.md`**

内容结构（顺序）：
1. Pi frontmatter（name, description, tools, model）
2. 角色声明（一句话）
3. 行动原则（渐进式披露、不可跳层、分析边界强制输出）
4. Phase 0-4 工作流（每个 Phase 含触发条件 + 操作步骤 + 输出）
5. 文档规范章节（inline Obsidian 格式：frontmatter 字段、wikilinks 用法、callouts 规范、三层文档模板）
6. 最终输出格式模板

**Task 2：更新 `agents/agents.json`**

在现有 JSON 中追加：
```json
"oss-researcher": {
  "agent": "@agents/oss-researcher.md",
  "model": "claude-sonnet-4-6"
}
```

**Task 3：初始化 `~/Obsidian/OSS Research/_registry.md`**

创建空 registry，包含表头和使用说明注释。

**Task 4：更新 omp-agents 速查表**

在 `skills/omp-agents/SKILL.md` 的 High-Frequency Agents 表中追加：
```
| `oss-researcher` | 开源项目代码研究与知识库沉淀 | "pi-mono 如何加载 skill？", "langchain memory 模块怎么设计的？" |
```

**Task 5：T1 静态检查**

验证项：
- [ ] `agents/oss-researcher.md` frontmatter 字段完整（name/description/tools/model）
- [ ] description 包含 `Use when` 和 `Do NOT use when`
- [ ] system prompt 无相对路径引用
- [ ] tools 列表最小化（bash, read, write, grep, ls）
- [ ] `agents.json` JSON 语法合法
