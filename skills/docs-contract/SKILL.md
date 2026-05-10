---
name: docs-contract
description: >-
  Build a documentation skeleton with maintenance contracts for a project
  that already has running MVP code but lacks a sustainable doc structure.
  Use when scaffolding project docs (PROJECT/LANGUAGE/PRODUCT/DESIGN/
  architecture/ADR), adding contract frontmatter to existing docs, or
  migrating from MVP doc state to long-term form. Do NOT use for brand-new
  empty projects, design dialogue, code architecture refactoring, or global
  doc/code drift audits.
---

# docs-contract

为已运行一段时间的 MVP 项目补建文档骨架，建立 contract frontmatter 维护契约 + 三层 lint，防止文档腐化。

**Design pattern**: Inversion + Generator + Reviewer 组合。

**核心原则**：所有骨架文档只承载 What 与 Why；How 由代码与 commit 承载。

## Hard Gate

| Condition | Action |
|---|---|
| 项目尚未启动 MVP / 全新空项目 | Stop. 本 skill 不适用。 |
| 已存在 docs-contract 骨架（核心层文件均带 contract frontmatter） | Lint instead, do not re-scaffold. |
| 用户未确认骨架候选清单 | Do not generate any file. |
| 已存在文件需被改写 | Skip by default; require explicit force. |

## 骨架两层

**核心层（始终建议）**：

- `PROJECT.md`、`LANGUAGE.md`、`PRODUCT.md`
- `docs/architecture/architecture.md`、`docs/architecture/decisions/`

**按项目特征追加**：`DESIGN.md`、`docs/architecture/{ui,contracts,modules,procedures,cli,release,concepts}/`。
探测信号见 `references/doc-type-catalog.md`。

## Contract Block

每个骨架文件头部带这段 YAML frontmatter：

```yaml
---
doc-type: <enum>
purpose: <one sentence>
must-not-contain: [<label>, ...]
# optional:
must-contain: [...]
update-when: [...]
source-of-truth-for: [...]
defer-to: [<file path>, ...]
---
```

字段语义、必需 / 可选区分、SoT 唯一性约定见 `references/contract-schema.md`。
`doc-type` 枚举与每种类型默认规则见 `references/doc-type-catalog.md`。

## Lint

三层校验（实现按 PR 渐进上线）：

| 层 | 范围 |
|---|---|
| **L1 结构** | frontmatter 合规、SoT 唯一、defer-to 链路、骨架完整性 |
| **L2 模式** | 文档内禁止物的 regex / AST 检测；行内豁免支持 |
| **L3 语义** | What/Why vs How 段落判定、术语跨文档一致性、过时检测 |

L1+L2 默认随 lint 一起跑；L3 按需触发。豁免语法与配置文件 schema 见 `references/contract-schema.md`。

## Storage

- 骨架文件落项目根 / `docs/` 既有结构（不在本 skill 目录内）
- 项目级配置：`docs/.docs-contract.yml`（可选，未知字段忽略）
- 默认规则集：`scripts/default_rules.py`（硬编码）

## CLI

| 命令 | 作用 |
|---|---|
| `omp docs-contract scaffold --root <dir>` | 默认 dry-run，列骨架候选 + 现状 |
| `omp docs-contract scaffold --root <dir> --apply` | 写盘；已存在文件默认 skip，`--force` 覆盖 |
| `omp docs-contract scaffold ... --include LANGUAGE,DESIGN` | 强制纳入；`--exclude` 反向 |
| `omp docs-contract lint --root <dir>` | L1 结构校验 + L2 模式（L2 在 PR3 上线） |
| `omp docs-contract lint --root <dir> --semantic` | 追加 L3 语义校验（PR4 上线） |
| `omp docs-contract inventory --root <dir>` | 盘点现有文档（PR5 上线） |

## References

| 需要做什么 | 读取文件 |
|---|---|
| 理解 contract frontmatter 字段与校验规则 | `references/contract-schema.md` |
| 选 doc-type / 看每种类型用途与默认规则 | `references/doc-type-catalog.md` |
