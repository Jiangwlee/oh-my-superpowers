# llm-wiki / omp wiki Design
#
# 用途：Karpathy-consistent LLM Wiki 方案设计文档
# 目录：设计方案 / 假设与风险登记 / 行动原则 / 行动计划

> 将 Karpathy 的 LLM Wiki 理论工程化为一个全局 markdown 知识系统：`omp wiki` 提供能力层，`llm-wiki` skill 提供 agent SOP 层。

## 目录

- [设计方案](#设计方案)
- [假设与风险登记](#假设与风险登记)
- [Spike 计划](#spike-计划)
- [Spike 结果](#spike-结果)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 背景与目标

当前目标不是做一个新的“项目文档系统”或“SaaS 知识平台”，而是忠实实现 Karpathy 的 LLM Wiki 理论：把原始资料放入 `raw/`，由 LLM 增量编译成可导航的 markdown wiki，再围绕编译后的 wiki 完成查询、linting 和输出归档。成功标准是：任意 coding agent 在读取 `llm-wiki` skill 后，都能通过统一的 `omp wiki` CLI 使用同一套知识管理工作流，而不依赖 `pi`、数据库或项目本地挂接目录。

### 架构

系统分为两层：

| 层 | 形态 | 职责 |
|---|---|---|
| 能力层 | `omp wiki` CLI | 管理 `raw/`、编译 `wiki/`、返回导航状态、读取 wiki 页面、执行 lint |
| SOP 层 | `skills/llm-wiki/` | 告诉 `claude/codex/pi` 何时 `ingest`、何时 `compile`、如何优先读 wiki 而不是 raw、何时 `lint` 与 `archive` |

数据流固定为：

```text
source input
→ omp wiki ingest
→ raw/
→ omp wiki compile
→ wiki/sources + wiki/concepts + wiki/maps + wiki/index.md + wiki/log.md
→ agent reads compiled wiki
→ omp wiki lint / omp wiki archive
```

全局目录采用 filesystem-first 结构：

```text
<wiki_home>/
├── raw/
├── wiki/
│   ├── AGENTS.md
│   ├── index.md
│   ├── log.md
│   ├── sources/
│   ├── concepts/
│   ├── maps/
│   └── outputs/
└── state.json
```

默认 `wiki_home` 为 `~/.local/share/oh-my-superpowers/wiki/`，允许通过环境变量或显式参数覆盖。

### 关键决策

- **以 Karpathy 理论为 source of truth**：后续命令、目录、SOP 设计都必须服从 `raw -> compile -> wiki -> query/lint/archive` 主链，而不是围绕某个现有实现的便利性打补丁。
- **`omp wiki` 不内置 runtime-specific agent orchestration**：不迁移 `pi` subprocess、`query`、`chat` 等 runtime 绑定逻辑，避免 CLI 重新变成 agent wrapper。
- **查询主对象是编译后的 wiki，不是 raw**：`raw/` 只服务 ingest、回溯、重新编译和调试；日常导航和综合默认只读 `wiki/`。
- **不创建项目本地 `.wiki`**：知识系统是全局的，不往 repo 里写挂接目录或 `.gitignore`；项目语义仅作为 frontmatter metadata 或 `--project` 参数进入系统。
- **不维护项目级书单或入口页**：避免双索引和同步脆弱性；如果材料带项目归属，则通过 metadata 表达，而不是第二套目录结构。
- **v1 只保留最小 CLI 原语**：`init / ingest / compile / nav / read / lint`，可选 `archive`。不保留过细的 `evidence/links/index/inspect` API 化原语。
- **`llm-wiki` 是 Pipeline + Tool Wrapper skill**：skill 只封装 SOP 与命令契约，不拥有实现脚本或运行时编排能力。
- **Obsidian 是查看前端，不是系统后端**：`wiki/` 必须保持 Obsidian-compatible markdown，但系统核心仍是文件系统与 CLI，而不是 Obsidian 插件生态。

---

## 假设与风险登记

| # | 假设/赌注 | 类别 | 错了的代价 | 处理 |
|---|----------|------|-----------|------|
| A1 | Karpathy 理论的最小可实现闭环可以只靠 `init / ingest / compile / nav / read / lint` 支撑 | 🟡 | v1 命令面不足，后续需补 `archive` 或更细原语 | 先按最小集实现，若真实使用受阻再补命令 |
| A2 | 仅用 `AGENTS.md` + `index.md` + `log.md` 足以支撑中小规模 wiki 导航 | 🟡 | wiki 成长后检索和导航性能下降 | 预留后续接入 `qmd` 等搜索后端，但不进 v1 |
| A3 | 不做项目本地配置仍能覆盖主要使用场景 | 🟢 | 只是使用时多传一个 `--project` 或依赖 git repo 推导 | v1 接受该成本 |
| A4 | 从 `knowledge-agent` 迁移时，原有 markdown 处理、索引更新、原子写入逻辑可脱离 `pi` 独立复用 | 🟡 | 迁移量高于预期，需重写更多代码 | 在实现阶段优先迁核心纯函数模块 |

---

## Spike 计划

无。当前设计的关键约束来自已读文档与现有代码结构，不存在必须先跑可丢弃代码才能回答的 🔴 风险。

---

## Spike 结果

无。

---

## 行动原则

- **TDD: Red → Green → Refactor**：先为 `omp wiki` 的目录契约、命令输出和迁移逻辑写失败测试，再实现最小代码。 **禁止：** 先写实现再补测试。
- **Break, Don't Bend**：`knowledge-agent` 中凡是 `pi` 绑定的接口直接删除或重写，不做兼容层，不保留旧 `kb-agent query/chat` 语义。 **禁止：** 引入 `legacy`、`v1/v2`、兼容别名。
- **Zero-Context Entry**：`cli/wiki/main.py`、`scripts/common.py`、`SKILL.md` 和本文档必须在开头明确职责和边界。 **禁止：** 让后续 agent 需要翻多个文件才能知道系统主链。
- **First Principles over Analogy**：设计理由必须追溯到 Karpathy 理论和当前需求，而不是照搬某个社区实现的目录或命令长相。 **禁止：** 因“看起来像标准 wiki 平台”而引入多余层。
- **Explicit Contract**：目录结构、frontmatter、命令输入输出、环境变量都要显式声明。 **禁止：** 隐式项目挂接、魔法默认值、未说明的副作用。
- **Minimum Blast Radius**：实现阶段先交付最小闭环，再考虑 `archive`、搜索后端、MCP 等扩展。 **禁止：** 在首个 PR 中混入 SaaS、数据库、MCP、复杂 project scoping。

---

## 行动计划

### 文件结构设计

#### Plan A: `omp wiki` CLI 能力层

| 操作 | 文件路径 | 职责 |
|------|----------|------|
| 新增 | `cli/wiki/main.py` | `omp wiki` 命令路由，暴露 `init / ingest / compile / nav / read / lint` |
| 新增 | `skills/llm-wiki/scripts/common.py` | `wiki_home` 解析、路径 helpers、state 读写、repo 名推导 |
| 新增 | `skills/llm-wiki/scripts/init.py` | 初始化 `<wiki_home>/raw`、`wiki/`、`AGENTS.md`、`index.md`、`log.md`、`state.json` |
| 新增 | `skills/llm-wiki/scripts/ingest.py` | URL / text / file 导入到 `raw/` |
| 新增 | `skills/llm-wiki/scripts/compile.py` | `raw/` 增量编译成 `wiki/sources`、`concepts`、`maps`、更新 `index.md` 和 `log.md` |
| 新增 | `skills/llm-wiki/scripts/nav.py` | 返回 wiki 状态与入口信息 |
| 新增 | `skills/llm-wiki/scripts/read.py` | 读取编译后的 wiki 页面 |
| 新增 | `skills/llm-wiki/scripts/lint.py` | 健康检查，v1 先 report-only |
| 新增 | `skills/llm-wiki/tests/test_init.py` | 初始化目录与文件契约测试 |
| 新增 | `skills/llm-wiki/tests/test_nav.py` | `nav` 输出与状态统计测试 |
| 新增 | `skills/llm-wiki/tests/test_read.py` | `read` 只读取 `wiki/` 的行为测试 |
| 新增 | `skills/llm-wiki/tests/test_ingest_compile.py` | `ingest -> compile -> wiki/sources` 闭环测试 |

#### Plan B: `llm-wiki` Skill SOP 层

| 操作 | 文件路径 | 职责 |
|------|----------|------|
| 新增 | `skills/llm-wiki/SKILL.md` | skill 触发条件、统一入口、查询与维护 SOP |
| 新增 | `skills/llm-wiki/references/cli.md` | `omp wiki` 命令和参数说明 |
| 新增 | `skills/llm-wiki/references/workflow.md` | `ingest -> compile -> nav/read -> answer` 工作流 |
| 新增 | `skills/llm-wiki/references/linting.md` | lint 场景与解释规则 |
| 新增 | `skills/llm-wiki/references/archive.md` | 何时把输出归档回 wiki |
| 新增 | `skills/llm-wiki/tests/test_skill.sh` | `SKILL.md` 静态检查与关键文案存在性测试 |

### 任务步骤

#### Task 1: 搭建 `omp wiki` 路由骨架

**Files:**
- 新增: `cli/wiki/main.py`
- 测试: `skills/llm-wiki/tests/test_init.py`

- [ ] **Step 1: 写失败测试** (~3 min)

  验证 `omp wiki --help` 暴露 `init / ingest / compile / nav / read / lint` 六个命令。

- [ ] **Step 2: 运行测试确认失败** (~1 min)

```bash
pytest skills/llm-wiki/tests/test_init.py -v
# 预期：FAIL
```

- [ ] **Step 3: 实现** (~5 min)

  - 入口: `def main() -> None`
  - 关键逻辑: 使用 `typer` 建立 `wiki` tool，命令层只做参数解析与脚本转发
  - 边界情况: 未提供参数时显示 help

- [ ] **Step 4: 运行测试确认通过** (~1 min)

```bash
pytest skills/llm-wiki/tests/test_init.py -v
# 预期：PASS
```

#### Task 2: 实现全局 wiki 初始化契约

**Files:**
- 新增: `skills/llm-wiki/scripts/common.py`
- 新增: `skills/llm-wiki/scripts/init.py`
- 修改: `cli/wiki/main.py`
- 测试: `skills/llm-wiki/tests/test_init.py`

- [ ] **Step 1: 写失败测试** (~3 min)

  验证 `init` 创建：
  - `raw/`
  - `wiki/AGENTS.md`
  - `wiki/index.md`
  - `wiki/log.md`
  - `state.json`

- [ ] **Step 2: 运行测试确认失败** (~1 min)

```bash
pytest skills/llm-wiki/tests/test_init.py -v
# 预期：FAIL
```

- [ ] **Step 3: 实现** (~5 min)

  - 函数签名: `def ensure_wiki_home(path: Path) -> None`
  - 关键逻辑: 解析 `WIKI_HOME`，幂等创建目录和初始文件
  - 边界情况: 已存在时不覆盖用户数据

- [ ] **Step 4: 运行测试确认通过** (~1 min)

```bash
pytest skills/llm-wiki/tests/test_init.py -v
# 预期：PASS
```

#### Task 3: 迁移 `ingest` 能力到 `raw/`

**Files:**
- 新增: `skills/llm-wiki/scripts/ingest.py`
- 修改: `cli/wiki/main.py`
- 测试: `skills/llm-wiki/tests/test_ingest_compile.py`

- [ ] **Step 1: 写失败测试** (~3 min)

  验证 URL/text ingest 后，`raw/` 中生成对应文件，且不直接写入 `wiki/`。

- [ ] **Step 2: 运行测试确认失败** (~1 min)

```bash
pytest skills/llm-wiki/tests/test_ingest_compile.py -v
# 预期：FAIL
```

- [ ] **Step 3: 实现** (~5 min)

  - 函数签名: `def ingest_source(source: str, *, kind: str, project: str | None) -> Path`
  - 关键逻辑: URL 通过现有提取能力转 markdown/text；text 直接落盘；file 先做占位失败提示
  - 边界情况: 内容为空时在边界报错，不创建脏文件

- [ ] **Step 4: 运行测试确认通过** (~1 min)

```bash
pytest skills/llm-wiki/tests/test_ingest_compile.py -v
# 预期：PASS
```

#### Task 4: 迁移最小 `compile` 闭环

**Files:**
- 新增: `skills/llm-wiki/scripts/compile.py`
- 修改: `cli/wiki/main.py`
- 测试: `skills/llm-wiki/tests/test_ingest_compile.py`

- [ ] **Step 1: 写失败测试** (~3 min)

  验证 compile 后至少产出：
  - `wiki/sources/*.md`
  - 更新 `wiki/index.md`
  - 更新 `wiki/log.md`

- [ ] **Step 2: 运行测试确认失败** (~1 min)

```bash
pytest skills/llm-wiki/tests/test_ingest_compile.py -v
# 预期：FAIL
```

- [ ] **Step 3: 实现** (~5 min)

  - 函数签名: `def compile_wiki(*, model: str | None = None) -> list[Path]`
  - 关键逻辑: 先迁移可复用的 markdown 摘要与索引更新逻辑；runtime-specific agent orchestration 不迁移
  - 边界情况: 无新 raw 时返回空 touched list

- [ ] **Step 4: 运行测试确认通过** (~1 min)

```bash
pytest skills/llm-wiki/tests/test_ingest_compile.py -v
# 预期：PASS
```

#### Task 5: 实现 `nav` 与 `read`

**Files:**
- 新增: `skills/llm-wiki/scripts/nav.py`
- 新增: `skills/llm-wiki/scripts/read.py`
- 修改: `cli/wiki/main.py`
- 测试: `skills/llm-wiki/tests/test_nav.py`
- 测试: `skills/llm-wiki/tests/test_read.py`

- [ ] **Step 1: 写失败测试** (~3 min)

  验证：
  - `nav` 返回 wiki 根状态、入口文件、sources/concepts/maps 计数
  - `read` 只能读 `wiki/` 下页面，默认不读 `raw/`

- [ ] **Step 2: 运行测试确认失败** (~1 min)

```bash
pytest skills/llm-wiki/tests/test_nav.py skills/llm-wiki/tests/test_read.py -v
# 预期：FAIL
```

- [ ] **Step 3: 实现** (~5 min)

  - `def build_nav() -> dict[str, object]`
  - `def read_wiki_page(path: str) -> str`
  - 关键逻辑: `nav` 暴露 `index.md`、`log.md`、目录计数；`read` 校验目标必须位于 `wiki/`
  - 边界情况: 缺页时报错，不自动降级去读 raw

- [ ] **Step 4: 运行测试确认通过** (~1 min)

```bash
pytest skills/llm-wiki/tests/test_nav.py skills/llm-wiki/tests/test_read.py -v
# 预期：PASS
```

#### Task 6: 实现 report-only `lint`

**Files:**
- 新增: `skills/llm-wiki/scripts/lint.py`
- 修改: `cli/wiki/main.py`
- 测试: `skills/llm-wiki/tests/test_nav.py`

- [ ] **Step 1: 写失败测试** (~3 min)

  验证 `lint` 至少能发现缺失索引项、坏链接或空目录状态，并以结构化结果输出。

- [ ] **Step 2: 运行测试确认失败** (~1 min)

```bash
pytest skills/llm-wiki/tests/test_nav.py -v
# 预期：FAIL
```

- [ ] **Step 3: 实现** (~5 min)

  - 函数签名: `def lint_wiki() -> list[dict[str, str]]`
  - 关键逻辑: v1 只报告问题，不做 discover-and-fix
  - 边界情况: 空 wiki 返回空 issues，而不是报错

- [ ] **Step 4: 运行测试确认通过** (~1 min)

```bash
pytest skills/llm-wiki/tests/test_nav.py -v
# 预期：PASS
```

#### Task 7: 编写 `llm-wiki` skill

**Files:**
- 新增: `skills/llm-wiki/SKILL.md`
- 新增: `skills/llm-wiki/references/cli.md`
- 新增: `skills/llm-wiki/references/workflow.md`
- 新增: `skills/llm-wiki/references/linting.md`
- 新增: `skills/llm-wiki/references/archive.md`
- 测试: `skills/llm-wiki/tests/test_skill.sh`

- [ ] **Step 1: 写失败测试** (~3 min)

  验证 `SKILL.md` 含有：
  - frontmatter `name: llm-wiki`
  - “Start from the wiki, not raw”
  - `omp wiki` 统一入口

- [ ] **Step 2: 运行测试确认失败** (~1 min)

```bash
bash skills/llm-wiki/tests/test_skill.sh
# 预期：FAIL
```

- [ ] **Step 3: 实现** (~5 min)

  - `SKILL.md` 只写触发边界、统一入口、查询/ingest/lint/archive SOP
  - 详细命令与规则下沉到 `references/`
  - 明确 `omp wiki` 是能力层，`llm-wiki` 是 SOP 层

- [ ] **Step 4: 运行测试确认通过** (~1 min)

```bash
bash skills/llm-wiki/tests/test_skill.sh
# 预期：PASS
```

#### Task 8: 从 `knowledge-agent` 中迁移纯函数模块

**Files:**
- 修改: `skills/llm-wiki/scripts/common.py`
- 修改: `skills/llm-wiki/scripts/compile.py`
- 修改: `skills/llm-wiki/scripts/ingest.py`
- 测试: `skills/llm-wiki/tests/test_ingest_compile.py`

- [ ] **Step 1: 识别可迁移模块** (~3 min)

  筛出仅依赖文件系统和 markdown 处理的逻辑，例如原子写入、slug 生成、索引更新。

- [ ] **Step 2: 迁移并清理 runtime 依赖** (~5 min)

  去掉 `pi`、`presets`、`agent` 相关接口，仅保留纯能力逻辑。

- [ ] **Step 3: 回归测试** (~2 min)

```bash
pytest skills/llm-wiki/tests/test_ingest_compile.py -v
# 预期：PASS
```

#### Task 9: 完成核查

**目的：** 防止 agent 虚报“任务完成”而实际存在遗漏或偏差。

- [ ] **Step 1: 对照 spec 逐 Task 核查**

  打开本文档的“任务步骤”列表，逐一确认每个 Task 的每个 Step 均已完成。

- [ ] **Step 2: 对照 spec 设计方案验证无偏差**

  重新阅读本文档“设计方案”章节，确认：
  - `omp wiki` 仍然是能力层，而非 runtime wrapper
  - 查询仍默认面向 `wiki/` 而非 `raw/`
  - 未引入项目本地 `.wiki`、数据库或兼容层

- [ ] **Step 3: 向用户汇报**

  输出格式：

  ```
  ## 完成核查报告
  - 已完成 Tasks: X / X
  - 未完成 Steps（如有）: [列举]
  - 与 spec 偏差（如有）: [列举]
  - 结论: ✅ 全部完成，无偏差 / ⚠️ 存在问题（见上）
  ```

#### Task 10: 文档更新

**Files:**
- 修改: `README.md`
- 修改: `PROJECT.md`
- 修改: 与 `llm-wiki` / `omp wiki` 相关的引用文档

- [ ] **Step 1: 识别需要更新的文档**

  检查以下位置是否有过时内容：
  - `README.md` 中的 tool 列表与架构说明
  - `PROJECT.md` 中的项目结构、CLI 示例
  - 任何引用旧 `knowledge-agent` 或旧设计边界的文档

- [ ] **Step 2: 更新文档内容**

  只更新因本次变更而过时的部分，不做无关改动。

- [ ] **Step 3: 提交**

```bash
git add README.md PROJECT.md docs/brainstorming/specs/2026-04-18-llm-wiki-design.md
git commit -m "docs: add llm-wiki design spec"
```
