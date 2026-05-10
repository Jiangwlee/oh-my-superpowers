# Lint Rules

`omp docs-contract lint` 三层校验。L1+L2 默认随 `lint` 一起跑；L3 须 `--semantic`（PR4 上线）。

## L1 结构 lint

| 规则 | 严重度 | 说明 |
|---|---|---|
| `L1.frontmatter.invalid` | HIGH | frontmatter YAML 错、缺必填字段、未知字段、未知 doc-type、字段类型不匹配 |
| `L1.location.mismatch` | HIGH | doc-type 与文件位置不符（PROJECT.md 必须在根目录、ADR 必须在 `docs/architecture/decisions/` 等） |
| `L1.defer-to.broken` | MEDIUM | `defer-to` 中的路径不存在（路径相对**当前文档所在目录**解析） |
| `L1.sot.duplicate` | CRITICAL | 同一个 `source-of-truth-for` 标签被多个文件声称（双 SoT） |
| `L1.skeleton.missing` | HIGH | 核心层缺文件（`project` / `language` / `product` / `architecture` 任一未带 contract frontmatter） |

## L2 模式 lint

| 规则 | 严重度 | 命中信号 |
|---|---|---|
| `L2.function-name` | MEDIUM | `foo()` / `module.bar()` / `Foo.bar()` 形式的函数调用片段 |
| `L2.file-path` | MEDIUM | `src/...` `./...` `*.py` `*.tsx` 等带扩展名的文件路径 |
| `L2.code-block` | MEDIUM | ` ``` ` 围栏代码块 |
| `L2.step-verb` | MEDIUM | "先 X 再 Y" / "Step N" / "then ... next" / "1. 然后" 等过程动词 |

L2 触发条件：文档 frontmatter 的 `must-not-contain` 列表中含对应 label。`docs/.docs-contract.yml` 的 `must_not_contain_extra` 可按文件追加。未知 label 静默忽略（向前兼容）。

## 行内豁免

```html
<!-- docs-contract: allow-<label> -->
```

放在违规段**之前**；作用范围到下一空行。例如：

```markdown
<!-- docs-contract: allow-code-block -->
术语表中需要少量代码示例，因此本段豁免：

```yaml
example: value
```
```

豁免必须**显式标注**，让审计可追溯：lint 报告会列出已豁免的位置，但不报为 finding。

## 配置文件

`docs/.docs-contract.yml`（项目级，可选）：

```yaml
# 在默认 must-not-contain 上叠加 per-file 规则
must_not_contain_extra:
  PROJECT.md: ["TODO", "FIXME"]
# fnmatch 通配符路径（相对项目根）；命中即跳过整个文件
exempt_paths:
  - docs/architecture/archived/**
# L3 触发：on-diff（git 检测到变更时） / manual（仅 --semantic）
semantic_lint:
  trigger: on-diff
  model: ${OMP_DEFAULT_MODEL_PI}
```

未知字段：忽略并报 warning（不报错）。

## 退出码

- 全部 finding 严重度 ≤ MEDIUM：`exit 0`
- 任一 finding 是 CRITICAL 或 HIGH：`exit 1`（CI / pre-commit 据此中断）
