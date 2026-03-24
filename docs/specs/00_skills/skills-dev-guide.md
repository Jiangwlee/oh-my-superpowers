# Skills 开发指导索引

## 核心原则（必须先读）

Skill 是给 LLM 执行的菜谱，不是给人看的项目变更说明。

### 菜谱里必须写

1. 目标成品：最终要产出的文件或结果。
2. 材料检查：开做前必须确认的输入是否就绪。
3. 固定步骤：按顺序执行的操作流程。
4. 完成判定：每一步“做到什么算完成”。
5. 关键约束：硬规则、禁止事项、失败处理。

### 菜谱里禁止写

1. 修改历史、迁移背景、设计动机回顾。
2. 上下游实现细节（例如“数据由哪个模块生成”）。
3. 新旧方案对比、兼容性叙述、过渡性说明。
4. 与当前执行无关的架构介绍和概念解释。

一句话判断：**凡是不能直接帮助 LLM 完成当次任务执行的内容，都不应进入 SKILL.md。**

本文件是按**开发场景**组织的技巧检索手册。
遇到具体问题时，直接找到对应场景，跳转到研究文件的精确章节。

详细研究文件在 `guides/` 目录。

---

## 一、Skill 元数据设计

### 如何写 description（触发条件）？
- 公式：`[能力全景] + "Use when" + [场景列表 (1)(2)...]`
- description 是**唯一触发机制**，body 中写"When to Use"无效（触发前不可见）
- 覆盖用户多种说话方式：问句 + 陈述 + 感叹
- **禁止**在 description 中写工作流摘要（LLM 会跳过读 body） → CSO 陷阱
- → [anthropics-skills-analysis.md §description公式](guides/anthropics-skills-analysis.md)
- → [superpowers-skill-patterns.md §CSO](guides/superpowers-skill-patterns.md)
- → [remaining-skills-analysis.md §find-skills Meta-Skill](guides/remaining-skills-analysis.md)

### 如何选择命名规范？
- 小写连字符，工具/服务前缀优先：`gh-fix-ci`, `ashare-trend-scan`
- 同领域多个 skill 加命名空间前缀区分
- → [openai-skills-analysis.md §命名规范](guides/openai-skills-analysis.md)

---

## 二、Skill 内容结构

### 如何控制 context 成本（三层渐进加载）？
- 层1：frontmatter（始终在 context，~100词）
- 层2：SKILL.md body（触发后加载，建议 <500 行）
- 层3：scripts/ references/ assets/（按需加载）
- → [anthropics-skills-analysis.md §三层渐进加载](guides/anthropics-skills-analysis.md)

### SKILL.md body 应该放什么内容？
- 工作流主干 + 核心约束
- 不放大段参考材料（移到 references/）
- 不放重复逻辑（移到 scripts/）
- → [anthropics-skills-analysis.md §三层渐进加载](guides/anthropics-skills-analysis.md)

### 如何控制 LLM 的指令自由度？
- 高自由度：多种方法都可行 → 文字指令 + 方向性建议
- 中自由度：有推荐模式 → 伪代码 / 参数化脚本
- 低自由度：操作脆弱易错 → 具体脚本 + 严格步骤
- → [anthropics-skills-analysis.md §自由度设计](guides/anthropics-skills-analysis.md)

### 如何量化 Skill 的 Token 目标？
- Getting-started 类：每个 <150 词
- 常加载 skill：全部 <200 词
- 其他 skill：<500 词；超出必须拆 references/
- → [superpowers-skill-patterns.md §量化Token目标](guides/superpowers-skill-patterns.md)

---

## 三、references/ 目录设计

### 如何组织 references/ 目录？
- 按业务领域拆分（finance.md / sales.md）
- 或按技术变体拆分（aws.md / gcp.md）
- 参考文件**只有1层深度**，直接从 SKILL.md 链接
- 参考文件 >100 行时，顶部加目录
- → [anthropics-skills-analysis.md §资源目录设计模式](guides/anthropics-skills-analysis.md)

### 如何声明参考文件的加载时机（条件引用）？
- 在 SKILL.md 中明确写"在 X 情况下才需要读 references/X.md"
- 示例：`If flags differ from your wrapper..., read: references/mineru-cli.md`
- 减少默认加载量，节省 context
- → [remaining-skills-analysis.md §条件引用声明](guides/remaining-skills-analysis.md)

### 如何避免 @ 语法的 context 浪费？
- ❌ `@skills/testing/SKILL.md`（强制立刻加载，消耗 200k+ context）
- ✅ `REQUIRED SUB-SKILL: Use superpowers:test-driven-development`（按需）
- → [superpowers-skill-patterns.md §@ 语法禁忌](guides/superpowers-skill-patterns.md)

---

## 四、scripts/ 目录设计

### 如何封装外部 CLI 工具为脚本？
- 黑盒原则：LLM 先运行 `--help`，不读源码
- 全环境变量覆盖：每个 CLI flag 都有对应 `ENV_VAR` 可覆盖
- 脚本开头：`set -euo pipefail` + 命令存在性检查
- → [anthropics-skills-analysis.md §scripts黑盒执行](guides/anthropics-skills-analysis.md)
- → [remaining-skills-analysis.md §全环境变量覆盖](guides/remaining-skills-analysis.md)

### 如何在 SKILL.md 中引用脚本？
- **直接写相对路径**，不加任何路径变量：`python scripts/foo.py`
- LLM 从系统上下文知道 skill 目录位置，能自行推理出完整路径
- ❌ 错误：`export SKILL_DIR="..."` + `python3 $SKILL_DIR/scripts/foo.py`
- ✅ 正确：`python scripts/foo.py`（与 Anthropic 官方 pptx/xlsx/docx skill 一致）
- 脚本内部需跨文件引用时，用 `pathlib.Path(__file__).resolve().parent` 自定位，不依赖外部变量
- 传入 skill 自身配置文件（如 `config.json`）时同理，脚本通过 `__file__` 自定位后读取，无需在 SKILL.md 中传 `--config` 参数

---

## 五、工作流设计

### 如何选择工作流组织模式？
- 多步骤任务 → 顺序工作流（编号步骤）
- 有分支任务 → 条件工作流（创建/编辑分支）
- 需用户持续参与 → 三阶段交互（收集→打磨→验证）
- 工具/方法选择 → 决策树
- → [anthropics-skills-analysis.md §工作流组织模式](guides/anthropics-skills-analysis.md)

### 如何绘制流程图？
- 用 Graphviz/DOT 语法，不用 ASCII 或 Mermaid
- 仅用于"不用图就容易犯错"的决策点
- 线性步骤用编号列表，参考材料用表格
- 终态节点用 `[shape=doublecircle]`
- → [superpowers-skill-patterns.md §Graphviz/DOT流程图](guides/superpowers-skill-patterns.md)

### 如何声明 Skill 链的终态（防止跳步）？
- 流程图和文字**双重声明**终态
- 示例：`The terminal state is invoking writing-plans. Do NOT invoke any other skill.`
- → [superpowers-skill-patterns.md §Skill链终态声明](guides/superpowers-skill-patterns.md)

---

## 六、LLM 行为控制

### 如何让 LLM 严格遵守规则（说服心理学）？
- Authority + Commitment + Social Proof 组合，合规率 33% → 72%
- Authority：`YOU MUST`、`No exceptions`、`<HARD-GATE>`
- Commitment：`Announce at start: I'm using...`、TodoWrite 打卡
- Social Proof：`Every time`、`Always`、`X without Y = failure`
- **禁止** Liking 原则（谄媚，破坏诚实反馈）
- → [superpowers-skill-patterns.md §说服心理学](guides/superpowers-skill-patterns.md)

### 如何设置不可逾越的硬约束？
- 用 `<HARD-GATE>` 标签包裹约束内容
- 与 `<EXTREMELY-IMPORTANT>` 组合，信号强度最高
- → [superpowers-skill-patterns.md §HARD-GATE标签](guides/superpowers-skill-patterns.md)

### 如何写 Iron Law（铁律）？
- 格式：`NO [需禁止的行为] WITHOUT [必须先做的前置步骤] FIRST`
- 配套：封堵"遵循精神"的理由；No exceptions 列表；合理化借口表；Red Flags 列表
- → [superpowers-skill-patterns.md §Iron Law模式](guides/superpowers-skill-patterns.md)

### 如何写合理化借口表（封堵规避话术）？
- 先跑基准测试，收集 LLM 的规避话术，然后逐条写进 skill
- 格式：`| 借口 | 现实 |` 对照表
- → [superpowers-skill-patterns.md §合理化借口表](guides/superpowers-skill-patterns.md)

### 如何强制 LLM 输出前自检？
- 在 skill 末尾加强制 Checklist，每次输出前逐条核对
- 覆盖：链接格式、空行规则、量化数据替代空泛描述
- → [remaining-skills-analysis.md §输出自检清单](guides/remaining-skills-analysis.md)

### 如何设置 Guardrails（护栏）？
- 专门的 Guardrails 段落，用 bullet list
- 混合正向（Always/Prefer）和负向（Do not/Never）规则
- 聚焦"最容易犯的错误"
- → [openai-skills-analysis.md §Guardrails段落](guides/openai-skills-analysis.md)

---

## 七、输出格式设计

### 如何设计输出模板？
- 严格模板（API 响应、固定格式报告）：`ALWAYS use this exact template`
- 弹性指引（依上下文适应）：`Here is a sensible default, use your best judgment`
- 示例驱动（风格高度依赖理解）：Input/Output 对照示例
- → [anthropics-skills-analysis.md §输出模式设计](guides/anthropics-skills-analysis.md)

### 如何强制 LLM 基于模板输出（而非从零重建）？
- 在 skill 中明确：`STEP 0: READ THE TEMPLATE FIRST`
- 指定"保留 FIXED 部分，只替换 VARIABLE 部分"
- → [anthropics-skills-analysis.md §模板优先原则](guides/anthropics-skills-analysis.md)

### 如何为特定平台修复渲染问题？
- Telegram 会吞掉列表末尾的空行 → 插入盲文空格 `⠀`（U+2800）
- 针对平台渲染 bug 内嵌修复，不依赖用户手动处理
- → [remaining-skills-analysis.md §Telegram渲染修复](guides/remaining-skills-analysis.md)

### 如何设置手机友好的字体大小？（目标设备：iPhone 17，460 PPI）

字号设计依路径不同，分三种场景：

**场景 A：SVG summary-card（画布 1080×1920 px，全屏查看）**
- 设计基准：SVG px 单位即物理像素，iPhone 17 全屏显示放大约 1.12×
- medium（默认）：`body 44px`，`h1 66px`，`h2 55px`，`h3 48px`，`meta 34px`
- small：body 36px；large：body 52px
- 标题按比例派生：`h1 = body × 1.50`，`h2 = body × 1.25`，`h3 = body × 1.09`

**场景 B：HTML → Chrome → PDF（750px 视口，3x DPR，A4 输出）**
- 设计基准：CSS px 在 3x DPR 下渲染，保证 PDF 中文可读
- medium（默认）：`body 28px`，`line-height 1.65`，`h1 calc(body*1.75)`，`h2 calc(body*1.42)`，`h3 calc(body*1.21)`
- small：body 24px；large：body 32px
- 表格：`font-size: body * 0.82`；meta/label：`font-size: body * 0.79`
- 参考实现：`skills/markdown-to-anything/scripts/report_render.py`

**场景 C：HTML → Chrome → PNG（750px 视口，3x DPR，截图）**
- 与场景 B 相同字号体系，但 `padding` 可适当加大：`padding: 28px 22px 48px`
- body < 24px（CSS px）在 3x DPR 截图缩放后难以阅读，勿低于此值

---

## 八、跨 Skill 协作

### 如何引用其他 Skill 作为依赖（显式 vs 软依赖）？
- 软依赖（OpenAI 风格）：`If create-plan skill is available, use it`
- 显式依赖声明表（github-explorer 风格）：用表格列出 skill + 工具 + 用途
- REQUIRED SUB-SKILL（superpowers 风格）：`REQUIRED SUB-SKILL: Use superpowers:xxx`
- → [openai-skills-analysis.md §跨Skill协作](guides/openai-skills-analysis.md)
- → [remaining-skills-analysis.md §依赖声明表](guides/remaining-skills-analysis.md)
- → [superpowers-skill-patterns.md §计划文档内嵌REQUIRED SUB-SKILL](guides/superpowers-skill-patterns.md)

### 如何在计划文档中嵌入执行引导？
- 在计划文档 header 写：`REQUIRED SUB-SKILL: Use superpowers:executing-plans`
- 确保下一个 session 的 LLM 立刻知道用哪个 skill，无需人工提醒
- → [superpowers-skill-patterns.md §计划文档内嵌REQUIRED SUB-SKILL](guides/superpowers-skill-patterns.md)

### 如何给用户提供 Plan → Execution 的路径选择？
- 方案1：Subagent-Driven（当前 session，子代理实现每个任务）
- 方案2：Parallel Session（新 session + worktree，批量执行+检查点）
- → [superpowers-skill-patterns.md §Plan→Execution双轨选择](guides/superpowers-skill-patterns.md)

---

## 九、Subagent 子代理设计

### 如何写高质量的子代理 Prompt？
- Focused（一个清晰问题域）
- Self-contained（全部上下文自包含，不让子代理读文件）
- Specific about output（明确期望返回格式）
- 有约束（`Do NOT change production code`、`Fix tests only`）
- → [superpowers-skill-patterns.md §Agent Prompt质量标准](guides/superpowers-skill-patterns.md)

### 如何将子代理提示词模板化？
- 抽离为独立文件：`implementer-prompt.md` / `spec-reviewer-prompt.md`
- 模板中留 placeholder，主 skill 负责填充
- 示例：`[FULL TEXT of task — paste it here, don't make subagent read file]`
- → [superpowers-skill-patterns.md §Subagent Prompt模板化](guides/superpowers-skill-patterns.md)

### 如何设计两阶段代码评审（顺序不可颠倒）？
- Spec Compliance Review 先（做了要求的事？有没有过度实现？）
- Code Quality Review 后（做得好吗？代码质量？）
- Red Flag：先做质量评审 → 可能质量很好但漏实现 spec
- → [superpowers-skill-patterns.md §两阶段评审模式](guides/superpowers-skill-patterns.md)

---

## 十、Skill 验证与测试

### 如何用 TDD 方法创作 Skill（Skill TDD）？
- RED：运行基准场景（无 skill，记录 LLM 如何失败/找借口）
- GREEN：写最小 skill 修复观察到的失败
- REFACTOR：关闭新发现的漏洞（封堵新借口）
- → [superpowers-skill-patterns.md §Skill TDD](guides/superpowers-skill-patterns.md)

### 如何设计压力测试场景（测试 Skill 在压力下的合规性）？
- 3+ 种压力叠加：时间、沉没成本、疲劳、经济、权威、社会评判
- 强制 A/B/C 选择（不允许模糊回答）
- → [superpowers-skill-patterns.md §压力测试场景设计](guides/superpowers-skill-patterns.md)

### 如何用元测试（Meta-Testing）定位 Skill 问题？
- "你读了 skill 但还是选了错误答案。这个 skill 怎么改写才能让正确答案显而易见？"
- 三种响应 → 三种修复：加 Iron Law / 直接加入建议 / 让关键点更突出
- → [superpowers-skill-patterns.md §Meta-Testing元技术](guides/superpowers-skill-patterns.md)

### Skill 提交前检查清单
- → [skill-quality-patterns.md §质量检查清单](guides/skill-quality-patterns.md)

---

## 十一、前置条件与错误处理

### 如何做前置依赖检查（Prerequisite Check）？
- 在正文最前面加 `## Prerequisite check (required)` 段落
- 工具检测：`command -v xxx`；认证检测：`gh auth status`
- 失败处理：明确安装步骤，然后**停止**（不继续执行）
- → [openai-skills-analysis.md §Prerequisite Check](guides/openai-skills-analysis.md)

### 如何处理 SPA 页面抓取陷阱？
- 提前标注"看起来能用但其实不行"的技术坑（如 GitHub 是 SPA，web_fetch 只拿到壳）
- 给出强制替代方案（必须用 GitHub API）
- → [remaining-skills-analysis.md §SPA陷阱警告](guides/remaining-skills-analysis.md)

### 如何设计分级降级协议（Extraction Fallback）？
- web_fetch → content-extract → MinerU-HTML 三级降级
- 触发条件：域名黑名单（微信/知乎）、结构复杂、内容缺失
- → [remaining-skills-analysis.md §分级降级协议](guides/remaining-skills-analysis.md)

### 如何设计沙盒权限提升？
- 事前声明"此 skill 需要网络权限"
- 动态检测：发现失败后提示用户提升权限重试
- → [openai-skills-analysis.md §沙盒权限提升](guides/openai-skills-analysis.md)

---

## 十二、MCP 服务集成

### 如何集成 MCP 服务（Step 0 模式）？
- Step 0：检测是否已配置，未配置时给出完整设置步骤（配置好自动跳过）
- Available Tools 列表 → Practical Workflows → Troubleshooting
- → [openai-skills-analysis.md §MCP集成模式](guides/openai-skills-analysis.md)

### 如何创建 MCP Server + Skill 双形态？
- `server.json`（MCP 注册表读，声明 npm 包 + 环境变量）
- `SKILL.md`（LLM 读，说明配置方法 + 使用示例）
- 零摩擦上手：自动注册匿名 token，无需 API key 即启动
- → [remaining-skills-analysis.md §instagit MCP+Skill双形态](guides/remaining-skills-analysis.md)

---

## 十三、跨会话连续性

### 如何保持跨会话工作连续性（progress.md 模式）？
- 首行记录原始 prompt（永不覆盖）
- 每次有意义工作后追加 TODOs / 决策 / 注意点
- 下一个 Agent 开始时先读此文件
- → [openai-skills-analysis.md §进度跟踪文件](guides/openai-skills-analysis.md)

### 如何让 Skill 在每次会话自动激活（SessionStart Hook）？
- → [superpowers-architecture.md §SessionStart Hook](guides/superpowers-architecture.md)

### 如何用一个引导 Skill 驱动多个 Skill？
- 引导程序模式：一个 using-xxx skill 作为入口，按需加载其他 skill
- → [superpowers-architecture.md §引导程序机制](guides/superpowers-architecture.md)

---

## 十四、定期任务与实时数据获取

### 如何设计 Watchlist + Heartbeat 定期监控？
- 维护 watchlist.json（监控目标列表，持久化）
- Heartbeat 触发 `watchlist check`，批量检查所有目标
- 单目标失败不中断整体（try-catch 在循环内部）
- 只汇报"真正有价值"的内容（LLM 判断，非规则过滤）
- → [x-research-architecture.md §Watchlist+Heartbeat](guides/x-research-architecture.md)

### 如何设计 CLI 驱动的实时数据研究循环？
- LLM 做策略（分解查询、评估信噪比）
- CLI 做执行（实际 API 调用、缓存、格式化）
- 研究结果存档（--save 到 drafts/）
- → [x-research-architecture.md §Agentic研究循环](guides/x-research-architecture.md)
- → [remaining-skills-analysis.md §x-research-skill](guides/remaining-skills-analysis.md)

### 如何实现文件缓存（防重复请求）？
- MD5 哈希缓存键（query + params）
- 差异化 TTL（快速模式1h，普通模式15min）
- 后置过滤不影响缓存键（过滤 ≠ 不同请求）
- → [x-research-architecture.md §文件缓存系统](guides/x-research-architecture.md)

### 如何追踪 API 调用成本？
- 记录 raw 读取量（过滤前），按计费逻辑估算
- 输出到 stderr（不污染正文输出）
- → [x-research-architecture.md §成本追踪](guides/x-research-architecture.md)

### 如何设计速率限制保护？
- 固定间隔：多页请求间自动 sleep
- 429 精准处理：读 `x-rate-limit-reset` header，告知精确等待时间
- → [x-research-architecture.md §速率限制保护](guides/x-research-architecture.md)

---

## 十五、多平台部署与适配

### 如何适配多个 AI 平台？
- Universal Agent（共享 `.agents/skills/`）vs Non-Universal（专属目录+符号链接）
- OpenClaw 路径：`~/.openclaw/skills` → `~/.clawdbot/skills` → `~/.moltbot/skills`
- → [superpowers-architecture.md §多平台适配策略](guides/superpowers-architecture.md)
- → [remaining-skills-analysis.md §vercel-labs Universal/Non-Universal分层](guides/remaining-skills-analysis.md)

### 如何部署到 Openclaw？
- → [openclaw-adaptation.md](guides/openclaw-adaptation.md)

### 如何支持多 OS？
- 分平台给出命令，先 helper 脚本，fallback 原生 OS 命令
- → [openai-skills-analysis.md §多OS支持](guides/openai-skills-analysis.md)

---

## 十六、禁止事项速查

| 反模式 | 正确做法 | 参考 |
|--------|----------|------|
| description 写工作流摘要 | description 只写触发条件 | [superpowers-skill-patterns.md §CSO](guides/superpowers-skill-patterns.md) |
| body 里写"When to Use" | 移到 description | [anthropics-skills-analysis.md](guides/anthropics-skills-analysis.md) |
| SKILL.md 塞满细节不拆分 | 细节拆到 references/ | [anthropics-skills-analysis.md](guides/anthropics-skills-analysis.md) |
| 直接读大脚本源码 | 先 --help，黑盒调用 | [anthropics-skills-analysis.md](guides/anthropics-skills-analysis.md) |
| 创建 README/CHANGELOG 等 | 只保留 Agent 工作所需文件 | [anthropics-skills-analysis.md](guides/anthropics-skills-analysis.md) |
| 用 @ 语法强制加载引用文件 | REQUIRED SUB-SKILL 声明 | [superpowers-skill-patterns.md](guides/superpowers-skill-patterns.md) |
| 引用文件嵌套多层 | 最多1层，直接从 SKILL.md 链 | [anthropics-skills-analysis.md](guides/anthropics-skills-analysis.md) |
| 从零重建有模板的输出 | 先读模板，基于模板修改 | [anthropics-skills-analysis.md](guides/anthropics-skills-analysis.md) |
| 用 web_fetch 抓 GitHub 页面 | 使用 GitHub API | [remaining-skills-analysis.md](guides/remaining-skills-analysis.md) |
| 说服原则用 Liking（喜好） | 只用 Authority+Commitment+Social Proof | [superpowers-skill-patterns.md](guides/superpowers-skill-patterns.md) |
| SKILL.md 用 $SKILL_DIR 变量调用脚本 | 直接写相对路径 `python scripts/foo.py` | [Skills-Dev-Guide.md §如何在 SKILL.md 中引用脚本](Skills-Dev-Guide.md) |
| 脚本调用时传 `--config skill/config.json` | 脚本用 `__file__` 自定位读 config | [Skills-Dev-Guide.md §如何在 SKILL.md 中引用脚本](Skills-Dev-Guide.md) |

---

## 研究文件完整列表

| 文件 | 内容摘要 |
|------|---------|
| [guides/anthropics-skills-analysis.md](guides/anthropics-skills-analysis.md) | 三层渐进加载、description公式、自由度设计、资源目录模式、工作流类型、输出模式、10大反模式 |
| [guides/openai-skills-analysis.md](guides/openai-skills-analysis.md) | agents/目录、命名空间前缀、跨Skill协作、MCP Step0、progress.md、沙盒权限、Prerequisite Check、Guardrails |
| [guides/superpowers-architecture.md](guides/superpowers-architecture.md) | 目录结构、多平台适配、SessionStart Hook、引导程序机制、using-superpowers 逐行解析 |
| [guides/superpowers-skill-patterns.md](guides/superpowers-skill-patterns.md) | 说服心理学、Iron Law、CSO、HARD-GATE、Skill链终态、Subagent Prompt模板、两阶段评审、Skill TDD、压力测试、Meta-Testing |
| [guides/remaining-skills-analysis.md](guides/remaining-skills-analysis.md) | 依赖声明表、SPA陷阱、分级降级、输出自检清单、Telegram修复、Watchlist模式、全环境变量覆盖、MCP+Skill双形态 |
| [guides/x-research-architecture.md](guides/x-research-architecture.md) | CLI驱动架构、速率限制、文件缓存、差异化TTL、成本追踪、Watchlist+Heartbeat、Agentic研究循环 |
| [guides/skill-structure.md](guides/skill-structure.md) | 单个 skill 的目录结构、命名规范、SKILL.md 最小规范 |
| [guides/skill-quality-patterns.md](guides/skill-quality-patterns.md) | 高质量 skill 共性、提交前检查清单、常见反模式 |
| [guides/skill-template.md](guides/skill-template.md) | 可直接复制的 SKILL.md 模板、description 写法参考 |
| [guides/dev-workflow.md](guides/dev-workflow.md) | 从需求到部署的完整步骤、持续演进建议 |
| [guides/openclaw-adaptation.md](guides/openclaw-adaptation.md) | 加载优先级、门控机制、上下文预算、部署命令 |
