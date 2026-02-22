# OpenClaw vs OpenCode Skills 机制深度分析

- 研究时间: 2026-02-22
- 研究范围:
  - `github_cache/openclaw-repos/openclaw`
  - `github_cache/openclaw-repos/opencode`
- 研究目标:
  - 梳理两个项目在 skills 功能上的架构、核心模块、主要流程、关键决策/判断
  - 提炼 skills 机制的第一性原理与可迁移设计原则

---

## 1. 一句话结论

- `openclaw` 采用 **“治理优先的快照化技能系统”**: 先发现并严格资格过滤，再构建会话级 snapshot 注入系统提示，并通过 watcher/remote-node 触发版本刷新。
- `opencode` 采用 **“工具优先的按需加载技能系统”**: 统一索引技能目录，模型通过 `skill` tool 在需要时加载正文，权限在工具调用阶段裁决。

两者并非谁更先进，而是优化目标不同:
- `openclaw`: 更偏长期运行、多节点、多策略配置场景下的一致性与可控性。
- `opencode`: 更偏单机/开发者工作流中的轻量、低提示开销和高灵活性。

---

## 2. 架构总览

## 2.1 OpenClaw 架构分层

1. 发现层 (Discovery)
- 多来源扫描与合并（workspace、managed、bundled、agents、plugin extraDirs）。
- 代码: `src/agents/skills/workspace.ts:221`, `src/agents/skills/workspace.ts:324`

2. 解析层 (Parsing)
- `SKILL.md` frontmatter 解析，提取 OpenClaw metadata（requires/install/os/skillKey/primaryEnv 等）。
- 代码: `src/agents/skills/frontmatter.ts:21`, `src/agents/skills/frontmatter.ts:81`

3. 资格层 (Eligibility)
- 根据 config、allowlist、运行平台、远端节点能力、requires 条件判定 skill 是否可进入候选集合。
- 代码: `src/agents/skills/config.ts:70`

4. 快照层 (Snapshot)
- 将“可用技能集”固化为 session 可复用 snapshot（含 prompt、resolvedSkills、version、skillFilter）。
- 代码: `src/agents/skills/workspace.ts:446`

5. 注入层 (Prompt Injection)
- 把 `<available_skills>` 作为 mandatory section 注入系统提示，引导模型“先选再读”。
- 代码: `src/agents/system-prompt.ts:19`, `src/agents/system-prompt.ts:408`

6. 刷新层 (Refresh)
- 监听 `SKILL.md` 变动 + 远端节点能力变动，提升 snapshot version 并触发后续 turn 热刷新。
- 代码: `src/agents/skills/refresh.ts:132`, `src/auto-reply/reply/session-updates.ts:155`

7. 运营层 (Ops / Gateway / CLI)
- `skills.status`、`skills.bins`、`skills.install`、`skills.update`，以及 CLI list/info/check。
- 代码: `src/gateway/server-methods/skills.ts:57`, `src/cli/skills-cli.ts:19`

## 2.2 OpenCode 架构分层

1. 索引层 (Catalog Build)
- 扫描 `.opencode`、`.claude`、`.agents`、`config.skills.paths`、`config.skills.urls` 并构建 `Skill.state`。
- 代码: `packages/opencode/src/skill/skill.ts:52`

2. 远端拉取层 (Remote Discovery)
- 通过 `index.json` + skill files 下载到 cache，要求存在 `SKILL.md` 才视为有效。
- 代码: `packages/opencode/src/skill/discovery.ts:39`

3. 工具暴露层 (Tool Exposure)
- 在 `skill` tool description 中输出 `<available_skills>` 列表。
- 代码: `packages/opencode/src/tool/skill.ts:22`

4. 调用裁决层 (Permission Gate)
- 工具初始化时按 agent permission 过滤可见 skills；执行时 `ctx.ask(permission=skill)` 二次确认。
- 代码: `packages/opencode/src/tool/skill.ts:15`, `packages/opencode/src/tool/skill.ts:69`

5. 会话层 (Session Integration)
- 工具注册统一由 `ToolRegistry` 提供；model 在循环中拿到 tool schema 与描述。
- 代码: `packages/opencode/src/tool/registry.ts:106`, `packages/opencode/src/session/prompt.ts:781`

6. API/命令层 (Ops)
- `/skill` endpoint 列出技能；command 系统可把 skill 当命令源。
- 代码: `packages/opencode/src/server/server.ts:422`, `packages/opencode/src/command/index.ts:125`

---

## 3. 核心模块拆解

## 3.1 OpenClaw 核心模块

### A. `workspace.ts`（skills 主编排器）

职责:
- 技能发现、合并、过滤、prompt 生成、snapshot 生成、命令规格生成。

关键点:
- 发现限流: `maxCandidatesPerRoot` / `maxSkillsLoadedPerSource` / `maxSkillFileBytes`。
  - 见 `src/agents/skills/workspace.ts:229`。
- 来源优先级（后写覆盖）:
  - `extra < bundled < managed < ~/.agents/skills < <workspace>/.agents/skills < workspace/skills`
  - 见 `src/agents/skills/workspace.ts:370`。
- prompt 截断策略:
  - 先 count 限制，再按字符预算二分截断。
  - 见 `src/agents/skills/workspace.ts:471`。

### B. `config.ts`（资格判定策略）

职责:
- 定义 `shouldIncludeSkill`，将 metadata 与运行时环境联合计算 eligibility。

关键判定:
1. skill 显式禁用 (`skills.entries.<key>.enabled=false`)。
2. bundled allowlist 限制。
3. os 匹配（本地平台或远端平台）。
4. requires 的 bins/env/config/anyBins 满足性。
- 见 `src/agents/skills/config.ts:70`。

### C. `frontmatter.ts` + `types.ts`（技能语义模型）

职责:
- 把 `SKILL.md` 的 manifest 转为强类型元数据。

关键语义:
- `skillKey`、`primaryEnv`、`requires`、`install`、`user-invocable`、`disable-model-invocation`。
- 见 `src/agents/skills/frontmatter.ts:81`, `src/agents/skills/types.ts:19`。

### D. `refresh.ts`（热刷新控制）

职责:
- 监听技能文件变化，维护 version，并支持全局/工作区级增量刷新。

关键机制:
- 只监听 `SKILL.md`，减少 FD 压力。
- debounce 避免频繁抖动。
- 见 `src/agents/skills/refresh.ts:156`, `src/agents/skills/refresh.ts:169`。

### E. `skills-remote.ts`（远端节点能力并入）

职责:
- 将远端 node（特别是 mac 节点）的 bin 能力并入 eligibility 计算。

关键机制:
- 探测 `system.which` / `system.run` 能力。
- 收集技能 requires bins，远程探测后写入 cache。
- 能力变化触发 snapshot version bump。
- 见 `src/infra/skills-remote.ts:241`, `src/infra/skills-remote.ts:149`。

### F. `env-overrides.ts`（技能运行环境注入）

职责:
- 从 skill config 注入 env/apiKey 到进程环境（可逆恢复）。

关键决策:
- 永久屏蔽危险 env（如 `OPENSSL_CONF`）与 host 危险变量。
- 只对允许敏感键开口（`primaryEnv`/`requiredEnv`）。
- 见 `src/agents/skills/env-overrides.ts:17`, `src/agents/skills/env-overrides.ts:111`。

### G. `skill-commands.ts`（slash command 映射）

职责:
- 把 user-invocable skills 编译为聊天命令，并处理保留名冲突。

关键点:
- 支持 `/skill <name> ...` 与直接 `/name ...` 两种调用形式。
- 见 `src/auto-reply/skill-commands.ts:31`, `src/auto-reply/skill-commands.ts:109`。

## 3.2 OpenCode 核心模块

### A. `skill.ts`（统一技能目录索引）

职责:
- 在 `Instance.state` 生命周期内构建技能 map 与目录白名单。

关键点:
- 外部技能目录可以通过 flag 关闭: `OPENCODE_DISABLE_EXTERNAL_SKILLS`。
- duplicate name 后者覆盖前者并发 warning。
- 见 `packages/opencode/src/skill/skill.ts:52`, `packages/opencode/src/skill/skill.ts:106`。

### B. `discovery.ts`（远端技能分发协议）

职责:
- 从 URL 拉取 `index.json`，按文件列表下载到 cache 并形成可加载 skill 目录。

关键点:
- 协议最小化: `skills[].{name,description,files}`。
- 仅当 `SKILL.md` 存在才纳入结果。
- 见 `packages/opencode/src/skill/discovery.ts:10`, `packages/opencode/src/skill/discovery.ts:91`。

### C. `tool/skill.ts`（模型可见接口）

职责:
- 通过工具描述暴露 skills；执行时返回 `<skill_content>`。

关键点:
- description 内嵌 `<available_skills>`（名称、描述、location）。
- `execute` 返回 skill 正文 + base dir + 采样文件列表（最多10）。
- 见 `packages/opencode/src/tool/skill.ts:37`, `packages/opencode/src/tool/skill.ts:79`。

### D. `agent.ts`（技能目录读权限协同）

职责:
- 把技能目录加入 `external_directory` allowlist，避免后续资源访问被拦。
- 见 `packages/opencode/src/agent/agent.ts:54`。

### E. `tool/registry.ts` + `session/prompt.ts`（运行时集成）

职责:
- 注册 `SkillTool`，并在会话循环中统一提供给模型。
- 见 `packages/opencode/src/tool/registry.ts:106`, `packages/opencode/src/session/prompt.ts:781`。

### F. `server.ts` + `command/index.ts`（外部可观测性）

职责:
- `/skill` API 列表查询；命令系统将 skill 注入可调用命令集合。
- 见 `packages/opencode/src/server/server.ts:422`, `packages/opencode/src/command/index.ts:125`。

---

## 4. 主要流程（E2E）

## 4.1 OpenClaw E2E

### 流程 A: 会话首次进入
1. 解析 workspace + agent。
2. `buildWorkspaceSkillSnapshot()` 扫描并过滤技能。
3. snapshot 挂到 session store，后续 turn 复用。
4. system prompt 注入 skills mandatory section。
- 证据: `src/commands/agent.ts:315`, `src/agents/skills/workspace.ts:446`, `src/agents/system-prompt.ts:408`

### 流程 B: 运行时变更热刷新
1. watcher 监听 `SKILL.md` add/change/unlink。
2. bump snapshotVersion。
3. 下次回复前 `ensureSkillSnapshot()` 发现 version 过期，重建 snapshot。
- 证据: `src/agents/skills/refresh.ts:199`, `src/auto-reply/reply/session-updates.ts:157`

### 流程 C: 远端节点加入
1. 记录 node platform + command 能力。
2. 若为可执行系统命令的 mac 节点，则探测 skill requires bins。
3. 远端能力变化触发 snapshot 刷新。
- 证据: `src/infra/skills-remote.ts:144`, `src/infra/skills-remote.ts:241`

### 流程 D: 用户侧运维
- `skills.status` 看资格报告；`skills.bins` 输出依赖二进制；`skills.update` 回写配置。
- 证据: `src/gateway/server-methods/skills.ts:57`

## 4.2 OpenCode E2E

### 流程 A: 启动时建立技能目录索引
1. 扫描本地兼容目录（`.opencode/.claude/.agents`）。
2. 扫描 config paths。
3. 远端 URL pull 到 cache 并追加。
4. 构建 `skills[name] -> Info` map。
- 证据: `packages/opencode/src/skill/skill.ts:104`, `packages/opencode/src/skill/skill.ts:135`, `packages/opencode/src/skill/skill.ts:155`

### 流程 B: 模型按需加载
1. 模型从 `skill` tool description 看到 `<available_skills>`。
2. 调用 `skill({name})`。
3. 工具执行 permission ask 后返回 skill 正文。
- 证据: `packages/opencode/src/tool/skill.ts:22`, `packages/opencode/src/tool/skill.ts:69`

### 流程 C: 控制平面
- 通过 `/skill` API 获取技能列表，供 TUI/SDK 展示。
- 证据: `packages/opencode/src/server/server.ts:422`

---

## 5. 关键决策 / 判断点

## 5.1 OpenClaw 的关键决策

1. **是否进入候选集**
- 判断函数: `shouldIncludeSkill()`。
- 输入: skill metadata + config + remote eligibility。
- 风险控制: 防止“已安装但不可执行/不可用”的假阳性。

2. **是否注入模型可见列表**
- `disable-model-invocation=true` 的技能会保留在生态里，但不进入模型初始可见 prompt。
- 用途: 支持“后台可管理”与“模型不可主动调用”分离。

3. **是否刷新快照**
- 判据: `snapshot.version < getSkillsSnapshotVersion(workspace)`。
- 保证 prompt 与磁盘状态的最终一致性，而不是每 turn 全量扫描。

4. **是否允许敏感环境变量注入**
- 只允许明确 declared env 面向技能注入，且对危险键硬拦。
- 防止技能配置把主机运行时污染为不可预期状态。

5. **命令命名冲突怎么处理**
- skill 命令名 sanitize + de-dup（`name`, `name_2`...）。
- 保证 chat 命令空间稳定可用。

## 5.2 OpenCode 的关键决策

1. **重复技能名冲突策略**
- 后加载覆盖前加载，记录 warn。
- 实用优先，但可追踪。

2. **权限裁决时机**
- 可见性过滤在 tool init，执行时再 ask。
- 双层防线: “看得见”与“用得了”分离。

3. **远端分发协议复杂度**
- 采用 `index.json + files[]` 极简协议。
- 优点是易托管/易调试，代价是缺少 richer metadata 约束。

4. **模型上下文成本控制**
- 不预注入全文 skill，只注入工具描述 + 名单。
- 在 token 与能力之间选“按需加载”。

---

## 6. 对比分析（架构性差异）

| 维度 | OpenClaw | OpenCode |
|---|---|---|
| 核心理念 | 资格治理 + 快照一致性 | 工具按需加载 + 轻编排 |
| 发现来源 | 多源 + 插件 + managed + bundled + remote eligibility | 本地兼容目录 + paths + urls |
| 合并策略 | 明确优先级链 | 顺序覆盖（duplicate warn） |
| 模型注入策略 | 系统提示 mandatory skills section | `skill` 工具描述列可用技能 |
| 刷新机制 | watcher + version + session refresh | 以 state 生命周期为主（重建触发） |
| 资格判定 | os/requires/config/env/remote bins 全量判定 | 主要依赖权限和技能可解析性 |
| 运营面 | gateway methods + CLI status/install/update | `/skill` API + debug/tui |
| 安全侧 | env 注入安全拦截、allowBundled、snapshot gating | permission ask + tool级授权 |

---

## 7. 第一性原理思考

skills 机制的第一性原理可以抽象成:

1. **能力外部化**
- skill 不是“提示词片段”，而是“可验证、可发现、可治理的能力单元”。

2. **选择先于执行**
- 模型必须先知道“有哪些能力”，再决定是否加载；否则要么盲用，要么全量注入导致上下文浪费。

3. **资格先于可见**
- “可发现”不等于“可执行”。平台、依赖、权限、配置必须在执行前判定。

4. **一致性先于优化**
- 长会话场景下，skill 列表若不稳定，会直接导致策略漂移。snapshot/version 是解决该问题的工程化手段。

5. **最小暴露面**
- 默认只暴露必要信息（name/desc/location）；正文按需加载；敏感 env 严格白名单。

6. **可观测与可运维**
- 必须有 status/check/install/update 等操作面；否则技能系统不可调试、不可持续演进。

---

## 8. 可迁移设计建议

1. 若你在 OpenClaw 风格系统中继续演进
- 保持 snapshot/version 架构不变。
- 优先增强 eligibility explainability（为什么某 skill 不可用）。
- 将 remote capability 探测结果持久化并加入过期策略。

2. 若你在 OpenCode 风格系统中增强治理
- 引入轻量 snapshot（至少记录本次会话 skill catalog hash）。
- 为远端 URL skill 增加签名/校验与来源标识。
- 增加 `disable-model-invocation` 等细粒度 frontmatter 策略。

3. 对两者通用
- 强化冲突管理（duplicate name 的 deterministic 决策日志）。
- 将“技能命中”与“技能执行成功率”纳入遥测，反推 description 质量。

---

## 9. 关键证据索引（便于二次核对）

### OpenClaw
- 发现与合并: `src/agents/skills/workspace.ts:221`, `src/agents/skills/workspace.ts:370`
- snapshot 生成: `src/agents/skills/workspace.ts:446`
- 资格判定: `src/agents/skills/config.ts:70`
- frontmatter 解析: `src/agents/skills/frontmatter.ts:81`
- watcher: `src/agents/skills/refresh.ts:132`
- 会话刷新: `src/auto-reply/reply/session-updates.ts:155`
- system prompt 注入: `src/agents/system-prompt.ts:19`
- remote eligibility: `src/infra/skills-remote.ts:241`
- gateway methods: `src/gateway/server-methods/skills.ts:57`

### OpenCode
- 技能索引: `packages/opencode/src/skill/skill.ts:52`
- 远端拉取: `packages/opencode/src/skill/discovery.ts:39`
- skill tool 描述/执行: `packages/opencode/src/tool/skill.ts:22`
- 工具注册: `packages/opencode/src/tool/registry.ts:106`
- 会话集成: `packages/opencode/src/session/prompt.ts:781`
- API 列表: `packages/opencode/src/server/server.ts:422`
- 命令接入: `packages/opencode/src/command/index.ts:125`
- 配置与权限 schema: `packages/opencode/src/config/config.ts:656`, `packages/opencode/src/config/config.ts:676`

