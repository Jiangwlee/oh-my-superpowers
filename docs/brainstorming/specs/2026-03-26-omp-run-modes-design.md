# omp run 四模式重构（text / stream / json / interactive）

> 将 `omp run` 重构为四种显式运行模式：默认最终文本、彩色流式文本、原始 JSON 事件流、以及直接进入 Pi TUI，降低 `pi` 命令使用复杂度，同时为未来 Web 集成保留清晰边界。

## 目录

- [设计方案](#设计方案)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 背景与目标

当前 [bin/omp](/home/bruce/Projects/oh-my-superpowers/bin/omp) 的 `run` 命令只有一种非交互行为：内部固定调用 `pi --mode json --no-session ... -p`，再由 `omp` 把 JSON 事件转成“人类文本”。这种实现混淆了三种不同需求：最终文本输出、流式过程可观测性、以及原始机器事件流。与此同时，用户还希望新增直接进入 Pi TUI 的交互模式，以避免手写冗长的 `pi` 参数。

本次重构目标是把 `omp run` 明确拆成四种模式：`text`、`stream`、`json`、`interactive`。其中 `text` 保持默认且语义纯粹，只输出最终 assistant 文本；`stream` 提供彩色、分层、可观测的流式终端输出；`json` 原样透传 `pi --mode json` 以供 Web 或其他宿主消费；`interactive` 则直接打开 Pi TUI，并可带首条 prompt 自动发出。

**成功标准：**
- `omp run <agent> [prompt...]` 默认走真正的 `pi --print` text mode
- `omp run <agent> --mode stream [prompt...]` 能持续输出彩色流式文本，且长任务可观测
- `omp run <agent> --mode json [prompt...]` 原样透传 `pi` JSON 事件流，不做包装
- `omp run <agent> --mode interactive [prompt...]` 能进入 Pi TUI，并支持可选首条 prompt
- 不再需要 `omp run -v` 或其他“附加 verbosity”开关

### 架构

**整体结构：**

`omp run` 仍负责三件事，不扩张为 agent backend：
- 从 `agents/agents.json` 读取 agent、model、skills
- 从 agent frontmatter 提取 `tools` 与 system prompt
- 按选定 mode 翻译成对应的 `pi` 命令并执行

**命令接口：**

```bash
omp run <agent> [--mode text|stream|json|interactive] [--model MODEL] [prompt...]
```

**模式与底层映射：**

| mode | 目标用户 | 底层调用 | stdout 语义 |
|------|----------|----------|-------------|
| `text` | 终端脚本 / 默认使用 | `pi --print` | 最终 assistant 文本 |
| `stream` | 人类终端 / 长任务观察 | `pi --mode json --print` | `omp` 格式化后的彩色流式文本 |
| `json` | Web / 机器集成 | `pi --mode json --print` | 原始 JSON lines |
| `interactive` | 人类持续交互 | `pi` interactive mode | Pi TUI |

**`stream` 数据流：**

```text
pi --mode json --print
    ↓
stdout JSON line stream
    ↓
omp event parser
    ↓
stream renderer
    ├── header/footer
    ├── assistant text streaming
    ├── tool start/end summary
    └── usage aggregation
    ↓
human-readable colored stdout
```

**`stream` 渲染规则：**

- Header：启动时输出时间、agent 名、model、tools、cwd、session/no-session
- Assistant 文本：按 `text_delta` 连续流出，前缀采用 `[agent-name]`
- Tool 事件：不显示原始 `toolcall_delta` 或 `tool:update`，只在工具完成时输出单行摘要
- Tool 单行样式：工具行整体向内缩进两个字符，状态符号使用 `✓` / `✗`，tool 名为浅灰，参数与正文摘要统一为灰色弱化
- 空行策略：正文与工具行不依赖空行分隔，只保留 header 与正文之间、footer 之前的必要留白；assistant 正文内部换行原样保留，但消息尾随空白要延迟到下一事件到来时再决定是否压缩为单换行
- Footer：输出完成状态、耗时、tool 次数、错误次数、累计 token usage

### 关键决策

- **四模式显式并列，而不是 `text + -v`**：`text`、`stream`、`json`、`interactive` 是四种不同消费协议，不是一个输出等级旋钮。用 `mode` 明确表达，比叠 `-v` 更清晰。
- **`json` 保持原样透传**：用户已经确认 `omp` 的定位是 launcher 而非 backend，因此 `omp` 不为 `json` 设计二次协议，也不承担 Web 契约层。
- **`stream` 是展示层，不是协议层**：新增的流式人类输出建立在 `pi --mode json` 之上，但只选择少数高价值事件进行文本化，不把全部 JSON 变成“彩色 JSON”。
- **`text` 回归真正的 final-only 语义**：默认输出必须与 `pi --print` 一致，避免继续维持“内部吃 JSON 再转文本”的混合语义。
- **`interactive` 接管到 Pi TUI 而非继续 `-p`**：进入 TUI 时不再走 `pi -p`。若提供 prompt，则交给 Pi 作为首条消息自动发送，这与 Pi 原生行为一致。
- **累计 token usage 以整次 run 为单位**：`pi` 在多个 assistant message 上分别附带 `usage`。`stream` footer 必须累计整次 run，而不是只展示最后一条 assistant message 的 usage。
- **颜色与信息层次是 `stream` 的一等需求**：`stream` 中只有状态符号和 agent 前缀使用强调色，tool 名、参数和正文摘要默认降到灰阶，避免在长任务中抢夺视觉焦点。
- **尾随换行的决策必须延迟到下一事件**：只有同一条 assistant 流继续追加时才保留原始尾随换行；一旦切换到新 message 或 tool 行，尾随双换行必须压成单换行。这样既保留 Markdown 正文结构，又避免 message/tool 之间出现额外留白。

---

## 行动原则

- **TDD: Red → Green → Refactor**：先用最小可复现命令验证四种 mode 行为，再改实现。**禁止：** 先重构 `run()` 再补验证脚本与行为检查。
- **Break, Don't Bend**：删除旧的“默认 JSON 转文本”实现，不保留 `-v` 兼容层。**禁止：** 在代码或 help 中保留 `verbose`、`legacy stream`、`deprecated mode` 等兼容残留。
- **Zero-Context Entry**：`bin/omp` 的头部注释和 `run()` 帮助必须让读者立即理解四种模式差异。**禁止：** 文档和帮助里只写 mode 名称，不写语义边界。
- **Explicit Contract**：`text`、`stream`、`json`、`interactive` 的 stdout 行为必须在代码与帮助文本中明确声明。**禁止：** 通过隐式默认或注释外约定表达 mode 语义。
- **First Principles over Analogy**：设计围绕“launcher 减少 `pi` 命令复杂度”和“长任务可观测”两个根本需求，而不是模仿其他 CLI。**禁止：** 因为别的工具有某个 flag 就照搬类似抽象。
- **Minimum Blast Radius**：只修改 `omp run` 相关路径，不借机重构 install/list/test 等命令。**禁止：** 顺手清理与本次模式重构无关的 CLI 代码。

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 修改 | `bin/omp` | 重构 `run` 命令为四模式，新增 `stream` 渲染层，删除旧 `_stream_verbose()` 逻辑 |
| 修改 | `docs/specs/02_framework/README.md` | 补充 `omp run` 四模式的规范索引入口 |
| 修改 | `docs/specs/02_framework/installation.md` | 更新 `omp run` 命令示例与模式说明 |
| 新增 | `docs/brainstorming/specs/2026-03-26-omp-run-modes-design.md` | 本设计文档 |

### 任务步骤

#### Task 1: `omp run` 四模式命令重构

**Files:**
- 修改: `bin/omp`

- [x] **Step 1: 写行为验证清单**

  先固定四个关键场景：

  ```bash
  omp run reviewer hello
  omp run reviewer --mode stream hello
  omp run reviewer --mode json hello
  omp run reviewer --mode interactive hello
  ```

  验证点：
  - `text`：stdout 只有最终文本
  - `stream`：stdout 为彩色流式文本，长任务中间有输出
  - `json`：stdout 为原始 JSON lines
  - `interactive`：进入 TUI，首条 prompt 自动发送

- [x] **Step 2: 提取 `pi` 命令构造逻辑**

  在 `bin/omp` 中新增统一的 run 配置解析与命令构造函数，职责包括：
  - 读取 agent、model、skills
  - 提取 frontmatter `tools`
  - 提取 system prompt
  - 根据 `mode` 生成 `pi` 命令

  目标是让四种模式共享同一份 agent preset 解析逻辑，只在“输出模式”层面分流。

- [x] **Step 3: 实现 `text` / `json` / `interactive` 三条直接路径**

  约束：
  - `text` 直接透传 `pi --print`
  - `json` 直接透传 `pi --mode json --print`
  - `interactive` 直接 exec 到 Pi interactive mode
  - 不复用旧 `_stream_verbose()` 代码

- [x] **Step 4: 验证基础三模式**

  ```bash
  omp run reviewer Reply with exactly PONG.
  omp run reviewer --mode json Reply with exactly PONG.
  omp run reviewer --mode interactive Reply with exactly PONG.
  ```

  预期：
  - `text` 最终只输出 `PONG`
  - `json` 输出 session / message / agent_end 等 JSON 事件
  - `interactive` 打开 TUI 并发送首条消息

- [ ] **Step 5: 提交**

  ```bash
  git add bin/omp
  git commit -m "feat: add explicit run modes for omp agents"
  ```

#### Task 2: `stream` 彩色流式渲染层

**Files:**
- 修改: `bin/omp`

- [x] **Step 1: 用工具场景写手工验收用例**

  ```bash
  omp run reviewer --mode stream "Read AGENTS.md and summarize the CLI rules."
  ```

  验收点：
  - assistant 文本能连续流出
  - tool start / done / error 颜色区分明显
  - 工具事件插入时不会打断文本到不可读
  - footer 能显示累计 token usage

- [x] **Step 2: 实现 `stream` 事件聚合与渲染**

  需要的内部组件：
  - header 渲染
  - assistant 文本流控制
  - tool 参数摘要
  - tool 结果摘要
  - usage 累计器
  - footer 渲染

  事件映射范围最终收敛为：
  - `session`
  - `message_update` 中的 `text_delta`
  - `tool_execution_start`
  - `tool_execution_end`
  - `message_end`（仅用于 usage 聚合）
  - `agent_end`

- [x] **Step 3: 设计输出风格**

  默认风格要求：
  - 时间、agent、model、cwd、usage：dim
  - assistant 文本：主色
  - tool 完成/失败状态符号：`✓` 绿色，`✗` 红色
  - tool 名、参数、正文摘要：浅灰/灰色
  - 文本模式采用“连续文本 + 单行工具摘要插入 + 继续文本”的混合风格

- [x] **Step 4: 验证长任务可观测性**

  ```bash
  omp run reviewer --mode stream "Use tools to inspect agents/ and docs/specs/, then summarize the agent system."
  ```

  预期：
  - 在任务执行中持续有输出，而不是只在结束时一次性输出
  - tool 失败时有明显错误块
  - footer 展示耗时、tool 次数、错误次数、累计 tokens

- [ ] **Step 5: 提交**

  ```bash
  git add bin/omp
  git commit -m "feat: add stream mode for omp run"
  ```

#### Task 3: 文档更新

**Files:**
- 修改: `docs/specs/02_framework/README.md`
- 修改: `docs/specs/02_framework/installation.md`

- [x] **Step 1: 识别过时文档**

  检查以下内容是否需要更新：
  - `omp run` 示例是否仍只描述单一非交互模式
  - 是否仍引用旧的 verbose/JSON 转文本行为
  - 是否缺少 `stream` 模式说明

- [x] **Step 2: 更新文档内容**

  只更新本次变更直接影响的部分：
  - `omp run` 四模式说明
  - 示例命令
  - `stream` 与 `json` 的适用场景区分

- [ ] **Step 3: 提交**

  ```bash
  git add docs/specs/02_framework/README.md docs/specs/02_framework/installation.md
  git commit -m "docs: update omp run mode documentation"
  ```

### 实施结果

- 已完成 [bin/omp](/home/bruce/Projects/oh-my-superpowers/bin/omp) 四模式重构
- 已完成 [docs/specs/02_framework/README.md](/home/bruce/Projects/oh-my-superpowers/docs/specs/02_framework/README.md) 与 [docs/specs/02_framework/installation.md](/home/bruce/Projects/oh-my-superpowers/docs/specs/02_framework/installation.md) 的同步更新
- 已完成 `stream` 终端排版收敛：
  - assistant 前缀改为 `[agent-name]`
  - tool 行改为两空格缩进的单行摘要
  - `✓` / `✗` 使用绿/红，tool 名与正文摘要使用灰阶
  - `tool:update` 不再显示
  - message/tool 之间的双空行通过“尾随换行延迟决策”机制压成单换行
- 已验证：
  - `./.venv/bin/python -m py_compile bin/omp`
  - `bin/omp run reviewer Reply with exactly PONG.`
  - `bin/omp run reviewer --mode json Reply with exactly PONG.`
  - `bin/omp run reviewer --mode stream "Read AGENTS.md and summarize the CLI rules in one sentence."`
  - `omp run reviewer --mode stream "Review SKILL.md"`（在 `skills/agent-review` 目录下复验换行行为）
  - `bin/omp run reviewer --mode interactive Reply with exactly PONG.`

### 待办收尾

- 尚未提交 commit
- 如需继续打磨，仅剩 `stream` 观感的细节优化，不影响四模式主语义
