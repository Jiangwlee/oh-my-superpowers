# Skills 开发指导（Openclaw）

本文基于以下来源整理：
- `AGENTS.md`
- `github_cache/anthropics-skills/README.md`
- `github_cache/anthropics-skills/template/SKILL.md`
- `github_cache/anthropics-skills/spec/agent-skills-spec.md`（指向 `https://agentskills.io/specification`）
- `github_cache/openai-skills/README.md`
- `github_cache/vercel-labs-skills/README.md`
- `github_cache/vercel-labs-skills/skills/find-skills/SKILL.md`
- `github_cache/openclaw/docs/tools/creating-skills.md`
- `github_cache/openclaw/docs/tools/skills.md`
- `github_cache/openclaw/skills/skill-creator/SKILL.md`

## 1. 目标与原则

- 目标：产出符合 AgentSkills/Openclaw 规范、可触发、可执行、可维护的技能。
- 原则：短小精确、触发明确、流程可落地、脚本优先复用、上下文开销可控。

## 2. 目录与命名规范

### 2.1 本项目目录约定

- 开发中的 skills 放在：`skills/`
- 外部优秀仓库缓存放在：`github_cache/`
- 经验沉淀文档放在：`Skills-Dev-Guide.md`（本文件）

### 2.2 单个 skill 推荐结构

```text
skills/<skill-name>/
  SKILL.md                # 必需
  scripts/                # 可选：可执行脚本
  references/             # 可选：按需加载文档
  assets/                 # 可选：模板/资源文件
```

### 2.3 命名建议

- `name` 使用小写 + 连字符：`my-skill-name`
- 目录名与 `name` 保持一致
- 避免过长、含义模糊的名字，优先“动作 + 领域”表达

## 3. SKILL.md 最小规范

最小可用模板：

```markdown
---
name: my-skill-name
description: Use when [触发条件 + 场景 + 边界]
---

# My Skill

## Overview
[一句话说明做什么]

## Workflow
[关键步骤，必要时给决策分支]

## Examples
- [用户表达 -> 你应该执行什么]
```

关键点：
- `name`、`description` 是触发与发现的核心元数据。
- `description` 重点写“何时使用（Use when...）”，而不是“怎么实现”。
- 正文写可执行步骤，少写泛泛方法论。

## 4. 高质量技能的共性（跨仓库提炼）

### 4.1 触发条件具体可检索

- 好的 `description` 会覆盖：
  - 场景关键词（如：`find a skill for X`）
  - 用户意图（如：想扩展能力、想安装现成能力）
  - 典型句式（如：`how do I do X`）

### 4.2 渐进披露，控制上下文成本

- `SKILL.md` 放流程主干，不塞过多大段参考材料。
- 详细内容移到 `references/`，在主文档中明确“何时读取”。
- 高频复用逻辑放 `scripts/`，优先“调用脚本”而不是每次重写。

### 4.3 先给决策，再给命令

- 推荐结构：`When to use` -> `Step-by-step` -> `Examples` -> `Guardrails`。
- 对多路径任务，用简单决策树/分支减少歧义。

### 4.4 强约束场景要给“护栏”

- 明确必须做/禁止做（例如：先 `--help`，不要盲读大脚本源代码）。
- 对风险工具给安全提示（命令注入、密钥泄露、越权执行）。

### 4.5 用例驱动，而不是说明书堆砌

- 用“用户说法 -> 触发 -> 操作”组织内容，提升模型命中率。
- 示例命令保持可直接执行，避免伪代码式无效示例。

## 5. Openclaw 适配要点（必须关注）

### 5.1 技能加载优先级

Openclaw 按以下优先级加载同名 skill：

1. `<workspace>/skills`（最高）
2. `~/.openclaw/skills`
3. bundled skills（最低）

### 5.2 可见性与 eligibility（门控）

- Openclaw 会按环境/配置/二进制可用性筛选技能。
- `metadata.openclaw.requires` 可声明：
  - `bins` / `anyBins`
  - `env`
  - `config`
- 不满足条件时，技能可能不会进入可用列表。

### 5.3 上下文预算意识

- 系统提示会注入“技能列表（name/description/path）”。
- 列表越长、描述越冗长，上下文占用越高。
- 所以 `description` 要短、准、可判定。

## 6. 开发流程（本项目推荐）

1. 明确问题：用户任务、触发语句、成功标准。
2. 定义触发：先写 `name` + `description`（Use when...）。
3. 设计正文：写最短可执行流程与边界条件。
4. 抽取复用：
   - 重复命令/逻辑 -> `scripts/`
   - 大块知识/规范 -> `references/`
5. 本地验证：
   - 检查 frontmatter 是否规范
   - 检查命令是否可运行
   - 检查是否有越权/注入风险
6. 部署测试：
   - 拷贝到 `/Users/mindora/clawd/skills`
   - 执行 `openclaw gateway restart`
   - 用真实提示语回归触发与执行

## 7. 质量检查清单（提交前）

- 结构：
  - 存在 `SKILL.md`
  - 目录名与 `name` 一致
- 元数据：
  - `name` 小写连字符
  - `description` 明确“何时使用”
- 内容：
  - 有清晰步骤，不空泛
  - 有示例触发语句
  - 有失败/异常处理建议
- 工程化：
  - 重复逻辑已抽脚本
  - 大文档已拆到 `references/`
  - 无无关文件噪音
- 安全：
  - 无明文密钥
  - 无不受控命令拼接
  - 高风险动作有确认/约束

## 8. 常见反模式

- `description` 只写功能，不写触发条件。
- `SKILL.md` 过长且无导航，导致命中后难执行。
- 所有细节堆在主文件，未做 `references/` 拆分。
- 示例不可执行，或依赖未声明二进制/环境变量。
- 未考虑 Openclaw 门控，导致技能“写了但不可用”。

## 9. 可复用模板（可直接复制）

```markdown
---
name: <skill-name>
description: Use when <用户意图/触发句式/适用边界>.
---

# <Skill Title>

## Overview
- 目标：
- 输入：
- 输出：

## When to Use
- 触发信号 1：
- 触发信号 2：
- 不适用场景：

## Workflow
1. 收集必要输入（缺失则先询问）
2. 选择路径（给出分支条件）
3. 执行核心步骤（命令/工具）
4. 校验结果并返回

## Guardrails
- 安全约束：
- 失败重试策略：

## References
- 需要时读取：`references/<topic>.md`

## Scripts
- 优先调用：`scripts/<tool>.sh --help`
```

## 10. 持续演进建议

- 每次新增/修改 skill 后，把经验回填到本文件。
- 优先记录“触发命中率提升”和“失败案例修复”两类经验。
- 对通用模式沉淀成模板，减少后续 skill 的重复设计成本。
