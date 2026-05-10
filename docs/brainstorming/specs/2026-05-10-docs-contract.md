# docs-contract — Design Spec

- **Date**: 2026-05-10
- **Scenario**: S2 (skill design)
- **Status**: Approved (pending implementation)

## 1. 定位

为已运行一段时间的 MVP 项目**补建文档骨架**，并通过 contract frontmatter + 三层 lint 防止文档腐化。

**In scope**：骨架候选探测、勾选式确认、骨架文件生成、contract frontmatter schema、L1/L2/L3 lint、配置文件 schema。

**Out of scope**：需求澄清、设计对话、架构改进、代码/backlog 全局漂移审计、新项目初始化、自动改写文档。

## 2. 设计模式

**Inversion + Generator + Reviewer 组合**：

- **Inversion**：探测项目特征 → 列骨架候选 → 用户勾选
- **Generator**：按勾选结果生成骨架文件（带 contract frontmatter）
- **Reviewer**：lint 三层

不是 Pipeline —— 用户驱动而非全自动。

## 3. CLI 接口（草案，PR2 阶段走 CLI Checklist 落实最终命名）

```
omp docs-contract scaffold        # Inversion + Generator：探测 + 勾选 + 生成
omp docs-contract lint            # L1 + L2（默认）
omp docs-contract lint --semantic # 追加 L3
omp docs-contract inventory       # 仅盘点现有文档，不改文件
```

CLI 子命令最终命名以 PR2 阶段事实核对（`omp --help` / 读 `cli/`）后为准。

## 4. 骨架两层

**核心层（始终建议）**：

- `PROJECT.md`
- `LANGUAGE.md`
- `PRODUCT.md`
- `docs/architecture/architecture.md`
- `docs/architecture/decisions/`

**按项目特征追加**：

| 候选 | 探测信号 |
|---|---|
| `DESIGN.md` + `docs/architecture/ui/` | `package.json` 含前端依赖 / 存在 `app/` `components/` `pages/` |
| `docs/architecture/contracts/` | 存在 OpenAPI / proto / json-schema 文件 |
| `docs/architecture/modules/` | `src/` 顶层 ≥ 3 个大目录 |
| `docs/architecture/procedures/` | 用户勾选（探测困难） |
| `docs/architecture/cli/` | 存在 `cli/` 或 `bin/` 目录且含 CLI 入口 |
| `docs/architecture/release/` | 存在 `CHANGELOG*` 或 git tag ≥ 3 |

探测仅供建议；最终由用户勾选确认。

## 5. Contract Frontmatter Schema

**必需 3 字段**：

- `doc-type`: enum
- `purpose`: 一句话
- `must-not-contain`: list（默认值由 doc-type 决定）

**可选 4 字段**：

- `must-contain`: list
- `update-when`: list
- `source-of-truth-for`: list（参与 SoT 唯一性校验）
- `defer-to`: list of file paths（参与链路有效性校验）

`doc-type` 枚举值由 `scripts/schema.py` **单一定义**，lint 与模板共同 import。

## 6. Lint 三层

| 层 | 实现 | 触发 | 输出 |
|---|---|---|---|
| **L1 结构** | `scripts/lint.py` 静态校验 frontmatter 合规、SoT 唯一、defer-to 链路、doc-type/位置匹配、骨架完整性 | 默认随 `lint` 跑 | 报告 |
| **L2 模式** | `scripts/lint.py` regex 检测函数名/路径/代码块/步骤动词；支持行内豁免 `<!-- docs-contract: allow-X -->` | 默认随 `lint` 跑 | 报告 + 行内建议 |
| **L3 语义** | `omp dispatch` 调 Pi（`--no-session`），降级 Claude（`--no-session-persistence`） | (a) 仅在 git diff 检测到文档变更后跑；(b) 用户显式 `--semantic` | 报告 |

L1+L2 零 LLM、毫秒-秒级、CI 可跑。L3 按需触发。

**禁 `--fix` / `--auto-rewrite`**。

## 7. 配置

`docs/.docs-contract.yml`（项目级覆盖）：

```yaml
# 可选；缺省走 default-rules（硬编码在 scripts/default_rules.py）
must_not_contain_extra:
  PROJECT.md: ["TODO", "FIXME"]
exempt_paths:
  - docs/architecture/archived/**
semantic_lint:
  trigger: on-diff   # on-diff | manual
  model: ${OMP_DEFAULT_MODEL_PI}
```

未知字段忽略不报错（forward-compatible）。

## 8. Skill 目录布局

```
skills/docs-contract/
├── SKILL.md                          # < 100 行；扉页 + 目录 + Hard Gate
├── scripts/
│   ├── schema.py                     # doc-type enum + frontmatter schema 单一定义
│   ├── default_rules.py              # must-not-contain 默认规则（硬编码）
│   ├── lint.py                       # L1+L2 入口
│   └── semantic_lint.py              # L3 入口（调 omp dispatch）
├── references/
│   ├── contract-schema.md            # frontmatter 字段详解
│   ├── doc-type-catalog.md           # 每个 doc-type 的 purpose / must-not-contain 默认
│   ├── lint-rules.md                 # L1/L2/L3 规则与豁免语法
│   └── inventory-migration.md        # 存量项目盘点 → 迁移流程
└── assets/
    ├── PROJECT.md.tmpl
    ├── LANGUAGE.md.tmpl
    ├── PRODUCT.md.tmpl
    ├── DESIGN.md.tmpl
    ├── architecture.md.tmpl
    └── decisions/0000-template.md

cli/docs-contract/main.py             # typer app（PR2 落实）

tests/skills/docs-contract/           # 测试统一放这里
```

## 9. Redline Checklist

| # | Redline | Source |
|---|---|---|
| 1 | description 只做语义触发，一句话；禁列具体限制领域、反面案例、workflow 细节、执行指令 | feedback_skill_description / feedback_skill_description_principle |
| 2 | description 与正文都禁止引用其他 skill 名 | feedback_skill_self_contained |
| 3 | SKILL.md < 100 行，扉页 + 目录 + Hard Gate；分支下沉 references/ | docs/specs/00_skills/README.md |
| 4 | SKILL.md 正文不写"because/原因解释" | feedback_skill_md_no_rationale |
| 5 | skills/docs-contract/ 内禁任何测试文件；测试统一放 tests/skills/docs-contract/ | feedback_no_tests_in_skill_dir |
| 6 | 必须明确属于 5 种设计模式之一或组合 | docs/specs/00_skills/README.md |
| 7 | SKILL.md 禁相对路径脚本调用；lint 必须 CLI 化 | docs/specs/00_skills/README.md / PROJECT.md |
| 8 | CLI 必须自包含；不得以"实现脆弱"为由要求用户手动介入 | feedback_cli_must_be_self_contained |
| 9 | 新增 CLI 子命令前必须事实核对三步；脚本走 $OMP_HOME 引用 | PROJECT.md §omp CLI 架构 |
| 10 | LLM 调用：Pi 优先（--no-session），Claude 降级（--no-session-persistence）；模型走 OMP_DEFAULT_MODEL_PI 优先级 | feedback_pi_first_citizen / feedback_headless_no_session |
| 11 | 不蚕食 brainstorming 的 design dialogue 职责 | skills/brainstorming/SKILL.md |
| 12 | 不蚕食 grill-me 的访谈循环职责 | skills/grill-me/SKILL.md |
| 13 | 沿用 LANGUAGE.md，禁引入 CONTEXT.md/UBIQUITOUS_LANGUAGE.md/GLOSSARY.md 等别名 | mindora-ui & auto-wechat 实践 |
| 14 | 不蚕食 project-cleanup 的全局漂移审计；本 skill 只管骨架内部契约 | 用户确认 |
| 15 | 文档/SKILL 不自称 ubiquitous-language 继任者 | mattpocock-skills/skills/deprecated/README.md |
| 16 | description 必须明示触发边界："MVP 已运行 + 想升级正式项目"；不为新项目 / 已有完整骨架的项目重复触发 | 用户确认 |
| 17 | frontmatter schema 最小必需 3 + optional 4；演进新字段必须 optional + 默认值 | 防过度设计 |
| 18 | doc-type 枚举单一定义源（scripts/schema.py），lint 与模板共同 import | design-guard 通用红线 |
| 19 | docs/.docs-contract.yml 配置 forward-compatible：未知字段忽略不报错 | IRON RULE #4 ≠ 用户配置可被静默丢弃 |
| 20 | L2 能用规则解决的禁下放 L3；三层职责显式列表 + lint.py 内部分文件 | 用户确认 |
| 21 | lint 只产报告 + 建议；禁 --fix / --auto-rewrite | 用户确认 |
| 22 | 存量项目骨架补建：必须先 inventory → 映射 → 标注缺漏冗余 → 保留用户已有内容；禁直接 overwrite | feedback_cli_must_be_self_contained 扩展 |

## 10. PR 拆分 + Reconciliation

### PR 1 — Skill 骨架 + Schema + Templates

**Touches**: `skills/docs-contract/SKILL.md` `scripts/schema.py` `scripts/default_rules.py` `references/*` `assets/*` `tests/skills/docs-contract/test_schema.py`

| Redline | Respected by |
|---|---|
| #1, #2 | description 一句话 + Use when/Do NOT use when；正文不出现其他 skill 名 |
| #3 | 详细 frontmatter 字段 → references/contract-schema.md；模板 → assets/；rule 详解 → references/lint-rules.md |
| #4 | SKILL.md 每条 step 只写动作 |
| #5 | 测试落 `tests/skills/docs-contract/` |
| #6 | SKILL.md 顶部声明 "Inversion + Generator + Reviewer" |
| #13 | 模板与 default rules 写死 `LANGUAGE.md`，不出现别名 |
| #15 | description / README 不提 mattpocock |
| #17 | `schema.py` 三必需四可选 |
| #18 | doc-type enum 仅在 `scripts/schema.py` 定义 |
| #22 | 模板生成器 "skip if exists" 默认行为 |

**Risks**: 模板里的 contract frontmatter 示例可能被 Agent 当成"该写多详细"的参照 → 模板要短小克制。

### PR 2 — CLI app + L1 Lint

**Touches**: `cli/docs-contract/main.py` `scripts/lint.py`（L1 部分）`tests/skills/docs-contract/test_lint_l1.py`

| Redline | Respected by |
|---|---|
| #7 | SKILL.md 命令表全部 `omp docs-contract …` |
| #8 | `scaffold` 探测 + 生成全自动；用户只勾选清单 |
| #9 | PR2 开工前先跑 `omp --help` / 读 `cli/web-operator/main.py` 等参考实现 / 写命令层次图，记入 PR description |
| #14 | L1 只校验骨架内部；不读 src/ 不读 backlog.md |
| #16 | `scaffold` 检测到已存在 contract frontmatter 时报错并建议跑 `lint`，不重复生成 |
| #19 | `_load_config` 用 schema 白名单 + 未知字段 warning 而非 error |
| #21 | `lint.py` 不暴露 `--fix`；`scaffold` 对已存在文件默认 skip，覆盖需 `--force` 显式 |

**Risks**: `scaffold` 探测启发式可能误判 → `--dry-run` 默认输出探测结果让用户审核。

### PR 3 — L2 Pattern Lint

**Touches**: `scripts/lint.py`（L2 部分）`scripts/default_rules.py`（扩充）`references/lint-rules.md` `tests/skills/docs-contract/test_lint_l2.py`

| Redline | Respected by |
|---|---|
| #14 | L2 只扫骨架文档内文本；不交叉验代码 |
| #20 | regex 能命中的不下放 L3；L2 模式集合在 `default_rules.py` 内列举 |
| #21 | 仅产报告 + 行内位置建议 |

**Risks**: 误报。豁免语法 `<!-- docs-contract: allow-code-block -->` 一开始就要内置，否则用户被误报淹没。

### PR 4 — L3 Semantic Lint

**Touches**: `scripts/semantic_lint.py` `cli/docs-contract/main.py`（追加 `--semantic` flag）`tests/skills/docs-contract/test_lint_l3.py`

| Redline | Respected by |
|---|---|
| #10 | 通过 `omp dispatch` 调 Pi（`--no-session`），降级 Claude（`--no-session-persistence`）；模型走 OMP_DEFAULT_MODEL_PI 优先级 |
| #20 | L3 仅做：What/Why vs How 段落判定、术语跨文档一致性、过时检测；明确不做 regex 能解决的事 |
| 预算控制 | 触发模式 (a) on-diff + (b) 显式 `--semantic`；cron 由用户自行配置，本 skill 不内置 |

**Risks**: LLM 输出不稳定 → 必须给 LLM 结构化输出 schema（每条违规：file/line/category/severity/suggestion），不接受散文报告。

### PR 5 — Inventory & Migration

**Touches**: `cli/docs-contract/main.py`（追加 `inventory` 子命令）`scripts/inventory.py` `references/inventory-migration.md` `tests/skills/docs-contract/test_inventory.py`

| Redline | Respected by |
|---|---|
| #8 | `inventory` 全自动产报告，用户不需手动归类 |
| #16 | inventory 是 scaffold 的前置，输出 "已存在 / 应新增 / 冗余" 三类清单 |
| #22 | inventory 只读不写；scaffold 用 inventory 输出决定 skip 哪些 |

**Risks**: 现有项目的"非骨架"文档（README、CHANGELOG）可能被误归"冗余" → inventory 默认豁免清单要包含这些。

## 11. 已确认的设计取舍

| 决策 | 选择 |
|---|---|
| 本 skill 是否考虑装在 oh-my-superpowers 自身 | 否（用户不会装） |
| `must-not-contain` 默认规则集存放 | 硬编码在 `scripts/default_rules.py`（演进慢但版本一致） |
| L3 触发模式 | (a) on-diff 自动 + (b) `--semantic` 手动；不内置 cron |

## 12. 不在本 spec 范围（明确 defer）

- 与 CI 集成（用户自行挂 pre-commit / GH action）
- L3 cron 调度（用户自行配置）
- 多语言文档支持（暂只考虑中英混合 markdown）
- 骨架模板的可定制（v1 模板硬编码；v2 再考虑 `~/.docs-contract/templates/` 覆盖）

## 13. 验收标准

- **PR1 完成后**：能 `omp install skill docs-contract`，SKILL.md < 100 行，T1 测试通过
- **PR2 完成后**：`omp docs-contract scaffold` 在 auto-wechat 上跑能识别现有文档并提议补建 LANGUAGE.md（已有）+ contracts/（缺）
- **PR3 完成后**：在 mindora-ui 的 `docs/architecture/` 上能查出至少一处 "How 下沉" 违规
- **PR4 完成后**：L3 在同样位置能给出比 L2 更细的"What vs How"判定
- **PR5 完成后**：inventory 输出能和 PR2 的 scaffold 联动（scaffold 默认 consume inventory 结果）
