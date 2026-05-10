# Doc-Type Catalog

`doc-type` 枚举的权威清单 + 每种类型的用途、默认规则、位置约定。
枚举源在 `scripts/schema.py`（DocType）；默认 `must-not-contain` 标签在 `scripts/default_rules.py`。

## 核心层（始终建议）

| doc-type | 文件位置 | 用途 | 默认 must-not-contain |
|---|---|---|---|
| `project` | `PROJECT.md` | 项目身份与开发约定的入口 | function-name, file-path, code-block, step-verb |
| `language` | `LANGUAGE.md` | 项目术语表 | function-name, file-path, code-block |
| `product` | `PRODUCT.md` | 产品定位、目标用户、核心价值 | function-name, file-path, code-block, step-verb |
| `architecture` | `docs/architecture/architecture.md` | 系统分层 / 模块边界 / 依赖方向 | function-name, file-path, code-block, step-verb |
| `adr` | `docs/architecture/decisions/NNNN-*.md` | 单条架构决策记录 | （无默认；ADR 是事实记录） |

## 按项目特征追加

| doc-type | 文件位置 | 探测信号 | 默认 must-not-contain |
|---|---|---|---|
| `design` | `DESIGN.md` | 含前端依赖的 `package.json` / `app/` `components/` `pages/` 之一 | function-name, step-verb |
| `ui` | `docs/architecture/ui/*.md` | 同 `design` | function-name, file-path |
| `contract` | `docs/architecture/contracts/*.md` | OpenAPI / proto / json-schema 文件 | step-verb |
| `module` | `docs/architecture/modules/*.md` | `src/` 顶层 ≥ 3 个大目录 | function-name, file-path, step-verb |
| `procedure` | `docs/architecture/procedures/*.md` | 用户勾选 | function-name, file-path |
| `cli` | `docs/architecture/cli/*.md` | 存在 `cli/` 或 `bin/` 含可执行入口 | function-name |
| `release` | `docs/architecture/release/*.md` | `CHANGELOG*` 或 git tag ≥ 3 | function-name, code-block |
| `concept` | `docs/architecture/concepts/*.md` | 用户勾选 | function-name, file-path, code-block, step-verb |

## 位置约束（L1 校验）

- `doc-type: project | product | language | design` → 项目根目录
- `doc-type: architecture` → `docs/architecture/architecture.md`
- `doc-type: adr` → `docs/architecture/decisions/`
- 其它 doc-type → 对应同名子目录

位置不匹配 → L1 报错。

## 模板

每种 doc-type 的 starter 模板见 `assets/<TYPE>.md.tmpl`。模板携带：
- 已填充 doc-type 与 purpose 占位
- 默认 `must-not-contain` / `update-when` / `source-of-truth-for`
- HTML 注释提示每节该写什么 / 不该写什么
