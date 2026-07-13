# AXI Principles — Static Review Checklist

Purpose: The 10 AXI principles as a source-review checklist. Per principle: what it means, the violation signals in source, where to look, severity, and the fix direction. Applies only to agent-facing CLIs (consumed by an agent via shell).
Sections: 严重度定义 | 通读定位 | 原则 1–10

## 严重度定义

- **blocking** — 歧义源。会让 agent 在错误数据上自信推进，或反复重试来消歧、耗尽轮次。正确性问题。
- **advisory** — token 效率 / 人机工程优化。不产生错误结果，但更贵、更易在噪声中跑偏。
- **unverified** — 源码未覆盖到该点，无法判定。报告中如实标注，不算违规。

元原则贯穿全部：**agent 通过 shell 读文本消费输出，最大失败模式是「输出有歧义」。** 每条原则堵一种歧义。判据始终是「agent 读到这个输出，会不会误解、或需要再问一次？」

## 通读定位

先在源码里定位这三处，后续多数原则都落在这里：

- **命令分发层**：arg/flag 解析、子命令路由、未知命令/flag 处理。
- **输出边界**：写 stdout 的唯一/主要位置，序列化格式（JSON？TOON？彩色表格？）。
- **错误与退出**：抛错/catch、写 stderr 还是 stdout、`process.exit` / exit code 设置点。

参考实现（可选对照标杆）：若本机存在 `~/Github/axi/packages/axi-sdk-js/src/`，可对照 `output.ts`（TOON 编码收口）、`cli.ts`（分发 + 未知命令 + home view）、`errors.ts`（`AxiError` + exit code 映射）；不存在则跳过，不影响裁定。

## 原则 1 — Token-efficient output（TOON）

意图：stdout 用 TOON（Token-Oriented Object Notation）而非冗长 JSON；在输出边界转换，内部保持 JSON。

违规信号：
- 直接 `JSON.stringify(data, null, 2)` / pretty JSON 写 stdout。
- 彩色表格、ASCII art、人类装饰性排版写 stdout（agent 要额外解析）。
- TOON 编码散落在多个业务函数里，而非收口在单一渲染边界。

定位：输出边界的序列化调用。

严重度：advisory。但注意边界——TOON 只在**窄 schema + 多行同构**时省 token；宽 schema（多字段/嵌套/布尔/时间戳）下 TOON 可能反而更贵，此时不强上 TOON 不算违规。

修复：把序列化收口到唯一渲染函数，列表/表格输出转 TOON；单对象/嵌套详情按可读性权衡。

## 原则 2 — Minimal default schemas

意图：列表每项默认 3–4 字段（id/title/status 量级），不是 10；长文本进详情不进列表。

违规信号：
- 列表命令默认 return 整个对象 / 全字段。
- 长文本字段（body/description/content）出现在列表项里。
- 默认 limit 过低（如 30）逼 agent 翻页；应设到覆盖常见场景（如 <100 就默认 100）。
- 无 `--fields` 之类让 agent 显式索取额外字段的入口。

定位：list/collection 类子命令的字段选择与默认 limit。

严重度：advisory。

修复：裁到最小可决策字段集；长文本移到 detail；提高默认 limit 到常见上限；加 `--fields`。

## 原则 3 — Content truncation

意图：详情大字段默认截断，并告诉 agent 如何取全量。

违规信号：
- detail 把大字段**整个省略**（逼 agent 去 hunt）。
- 大字段**全量塞入**、无截断。
- 有截断但**缺三件套**之一：截断预览、`(truncated, N chars total)` 总量标注、仅在真截断时给的 `--full` 逃生口。

定位：detail/view 类子命令的大字段处理。

严重度：advisory。

修复：截断到 500–1500 字 + 标总量 + 真截断时提示 `--full`；绝不整字段省略。

## 原则 4 — Pre-computed aggregates

意图：把 agent 常见的下一步数据内联，消灭 follow-up 调用（follow-up 调用比多几行输出贵得多）。

违规信号：
- 列表只给当前页，不给**总数**（agent 会翻页确认「是否见全」）。缺 `count: N of M total`。
- 常见下一步状态未内联（如 PR 的 `checks: 3/3 passed`、`comments: 7`），逼 agent 再调一次。

定位：list 输出的计数字段；detail 输出的派生状态字段。

严重度：advisory（但省的是最贵的 round-trip）。

修复：列表带总数；内联 backend 能廉价提供的派生摘要（是摘要不是全量数据）。

## 原则 5 — Definitive empty states

意图：空结果显式说明「就是空」并带上下文，让 agent 明确命令成功了。

违规信号：
- 空结果打印空白 / 空数组 / 什么都不输出（agent 无法区分：挂了？参数错？真没有？→ 换 flag 重试）。
- 空态输出与「出错」输出长得一样，无法区分。

定位：list/search 命令在结果为空时的分支。

严重度：**blocking**（歧义直接触发无谓重试）。

修复：输出带上下文的零态，如 `tasks: 0 closed tasks found in this repository`，明确成功。

## 原则 6 — Structured errors & exit codes（信息量最大，含多子项）

### 6a. 未知 flag/参数要「响」（fail loud）— **最危险**

违规信号：
- arg parser **静默忽略**未知 flag（agent 拿到「看起来被过滤、其实没过滤」的输出后自信推进——比报错更糟）。
- 未知 flag 不报错、不退非零。

定位：flag 解析处是否有「未知即拒绝」逻辑；是否按子命令各自的合法 flag 集校验。

严重度：**blocking**。

修复：拒绝未知 flag，exit 2，错误里**内联列出该命令合法 flag 或直接附 `--help`**（让 agent 一轮自纠）；重命名/移除的 flag 给定向提示（`--status 已改名，用 --state`）。

### 6b. 错误走 stdout，不泄漏底层报错

违规信号：
- 错误写 **stderr**（agent 读数据在 stdout，读不到错误）。
- 错误格式与正常输出不一致（agent 要两套 parser）。
- **原样漏出**底层依赖的 API error / stack trace / 依赖工具名。

定位：catch 块、错误打印语句、是否引用了被包裹工具的原始报错。

严重度：**blocking**。

修复：错误用与正常输出同一套结构化格式打到 stdout；翻译错误、抽取可执行含义、丢弃噪声；错误信息只引用本 CLI 的命令，不得泄漏底层工具名。

### 6c. 幂等 mutation

违规信号：对已处于目标态的操作（关已关的 issue）返回**非零退出码 / 报错**，逼 agent 当失败重试。

定位：mutation 命令对「状态已满足」的处理。

严重度：advisory。

修复：返回 exit 0 + `#42 already closed (no-op)`；非零退出码只留给「意图真的无法满足」。

### 6d. 无交互 prompt

违规信号：缺必填值时**弹交互 prompt** 等输入；被包裹工具的 prompt 未被压掉。

定位：是否有 readline/inquirer/`prompt()`；是否透传了子进程的交互。

严重度：**blocking**（agent 无法应答，会挂起/超时）。

修复：每个操作仅靠 flag 即可完成；缺值立即结构化报错；压掉被包裹工具的 prompt。

### 6e. 退出码语义 + 通道纪律

违规信号：
- 退出码无语义（成功也可能非零，或错误恒为 0）。应为 `0`=成功（含 no-op）｜`1`=错误｜`2`=用法错。
- 进度/日志（`Fetching...`）混进 **stdout**（agent 会当数据解析）。

定位：`process.exit`/exit code 设置点；所有写 stdout 的 `console.log`。

严重度：**blocking**（进度混入 stdout / 退出码错乱都会误导 agent）。

修复：exit code 三档语义化；stdout 只放结构化数据+错误，进度/调试全走 stderr。

## 原则 7 — Ambient context via session integrations

意图：通过 session hook 在会话开始就注入紧凑 dashboard，让 agent 无需主动调用即见状态；hook 为主、可安装 skill 为辅。

违规信号：
- 无 SessionStart hook 安装入口，agent 每次都要盲调。
- hook 从普通命令**偷偷安装**，而非用户显式 setup 命令。
- 只硬编码单一 agent（应默认支持 Claude Code / Codex / OpenCode）。
- 注入的 dashboard 过重（每 session 都加载，需极简）。

定位：是否有 setup/install-hook 命令；hook 注册位置；home view 体量。

严重度：advisory。

修复：提供显式 setup 命令装 SessionStart hook（幂等、可修路径、可移植 binary 名）；默认支持三家 agent；dashboard 极简；另出可安装 skill 作次路径。

## 原则 8 — Content first

意图：无参调用 CLI 展示**实时数据**（home view），不是 help 手册。

违规信号：无参调用打印 usage/help 文本（agent 得再调一次才拿到数据）。

定位：无参数时的分支。

严重度：advisory。

修复：无参调用跑 home view，输出当前工作目录相关的实时状态 + 少量 next-step 提示。

## 原则 9 — Contextual disclosure

意图：每次输出附几个逻辑下一步（`help[]`），让 agent 靠用发现 CLI 表面积。

违规信号：
- list/mutation 输出无 next-step 提示。
- 提示用**猜的具体值**而非占位符（`<id>`），会误导 agent。
- 自足输出（detail/count/confirmation）还硬塞建议（噪声）。
- 提示未携带当前消歧 flag（`--repo` 等）；错误时给「see --help」而非具体修复命令。

定位：各命令输出末尾的 help/suggestions 组装。

严重度：advisory。

修复：list/mutation 带 2–3 个相关、可执行、带占位符的下一步；自足输出省略建议；错误给具体修复命令。

## 原则 10 — Consistent way to get help

意图：home view 先自报身份（bin 绝对路径 + 一句话描述）；每个子命令 `--help` 给简洁完整参考。

违规信号：
- home view 不含 `bin:`（home 折叠 `~`）+ `description:`。
- 子命令无 `--help`，或 `--help` dump 整个 CLI 手册（应只给该子命令：flag+默认、必填参数、2–3 示例）。
- `--help` 未被无条件放行。

定位：home view 头部；各子命令 help 实现。

严重度：advisory。

修复：home view 顶部加 bin+description；每子命令给聚焦的 `--help`；`--help` 永远放行。
