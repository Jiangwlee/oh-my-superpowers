# Contract Schema

每个骨架文档头部都带一段 YAML frontmatter，称为 **contract block**。它声明文档自身的契约：写什么、不写什么、何时更新、为谁负责。

## 字段

| 字段 | 必需 | 类型 | 说明 |
|---|:--:|---|---|
| `doc-type` | ✓ | enum | 文档类别，决定默认规则与位置约束。枚举值见 `doc-type-catalog.md`。 |
| `purpose` | ✓ | string | 一句话说明本文件的存在理由。 |
| `must-not-contain` | ✓ | list[string] | 禁止物标签清单。L2 lint 据此扫描；标签语义见 §pattern labels。 |
| `must-contain` | | list[string] | 必含物标签或片段。L1/L2 校验。 |
| `update-when` | | list[string] | 触发更新的条件清单（描述性文本）。供人审阅。 |
| `source-of-truth-for` | | list[string] | 本文件作为权威源的领域标签。**全项目内必须唯一** —— L1 校验。 |
| `defer-to` | | list[string] | 当问题不属本文件时引导到的位置。值是文件路径或目录；L1 校验路径存在性。 |

未声明字段 = lint 报 unknown field 错误（防 typo）。新增字段必须 optional + 默认值。

## Pattern Labels（用于 `must-not-contain`）

L2 lint 把以下标签翻译成正则 / AST 检测：

| label | 命中信号 |
|---|---|
| `function-name` | camelCase / snake_case 标识符且与 `src/` 实际符号匹配 |
| `file-path` | `src/...`、`./...`、`*.tsx?`、`*.py:line` 等 |
| `code-block` | ` ``` ` fenced block |
| `step-verb` | "先 X 再 Y"、"Step 1/2/3"、"then ... next" |

每种 doc-type 的默认标签集见 `doc-type-catalog.md`。

## SoT 唯一性（关键约束）

`source-of-truth-for` 在整个项目内必须唯一。任意两个文件声称同一领域 → L1 立即报错。

**Why**：双 SoT 是文档腐化的头号成因。本字段把 SoT 关系显式化、机器可校验。

## 行内豁免

需要破例时在文档内写：

```html
<!-- docs-contract: allow-<label> -->
```

豁免作用域为单段（到下一空行）。`allow-X` 必须解释**为什么**。lint 报告里会列出所有豁免，作为审计线索。

## 配置文件

`docs/.docs-contract.yml`（可选）：

```yaml
must_not_contain_extra:
  PROJECT.md: ["TODO"]
exempt_paths:
  - docs/architecture/archived/**
semantic_lint:
  trigger: on-diff   # on-diff | manual
  model: ${OMP_DEFAULT_MODEL_PI}
```

未知字段：忽略 + warning（forward-compatible）。
