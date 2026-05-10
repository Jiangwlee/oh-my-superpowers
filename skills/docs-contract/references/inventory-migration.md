# Inventory & Migration

把已运行的 MVP 项目过渡到 docs-contract 维护契约的标准流程。

## 四类清单

`omp docs-contract inventory` 把每个骨架候选位置归入下表之一：

| 类别 | 含义 | 典型成因 |
|---|---|---|
| `managed` | 文件存在 + 带合规 contract frontmatter | 已经按 docs-contract 运行 |
| `unmanaged` | 文件存在但缺 frontmatter（或 frontmatter 不合规） | MVP 期写的文档；本 skill 引入前已存在 |
| `suggested` | 项目特征预测应有但路径不存在 | 还没写 |
| `skipped` | 探测说不需要 + 路径也不存在 | 项目当前无此特征 |

inventory **只看骨架预期路径**，不扫整个仓库；README / CHANGELOG / LICENSE 等永不会被归为冗余。

## 标准迁移流程

### 1. inventory 看现状

```bash
omp docs-contract inventory --root <project>
```

记下 `unmanaged` 和 `suggested` 两栏。

### 2. 补 suggested 文件

```bash
omp docs-contract scaffold --root <project> --apply
```

只对 `suggested` 写盘；`managed` 与 `unmanaged` 默认跳过（不覆盖人类已写的内容）。

### 3. 把 unmanaged 文件改造为 managed

对每个 unmanaged 文件，加上 contract frontmatter（参考 `assets/<TYPE>.md.tmpl` 的 frontmatter 段）。

迁移要点：
- 选 doc-type，照 `references/doc-type-catalog.md` 决定文件位置是否需要移动
- 写 `purpose`（一句话）
- 复制对应类型的默认 `must-not-contain`
- 必要时声明 `source-of-truth-for`（保证全项目唯一）
- 标 `update-when` / `defer-to`（可选，但建议）

### 4. lint 验证迁移结果

```bash
omp docs-contract lint --root <project>
```

CRITICAL / HIGH 必须清零；MEDIUM（L2 模式 lint）按需要修复或加行内豁免。

### 5. 可选：跑 L3 语义校验

```bash
omp docs-contract lint --root <project> --semantic
```

L3 报告 What/Why vs How 的判定。这是修剪过度下沉到代码细节的入口。

## 处理已存在的 unmanaged 内容时的判断原则

| 情况 | 处理 |
|---|---|
| 文件位置正确，只缺 frontmatter | 直接加 frontmatter |
| 文件位置不对（如 PROJECT.md 在 docs/ 下） | 移动到正确位置，再加 frontmatter |
| 文件内容大半是 How（实现细节、函数清单） | 拆分：What/Why 留下；How 移到代码注释 / PR 描述 / 删除 |
| 同一份文件承载多个 doc-type 的内容（混合 PRODUCT + ARCHITECTURE） | 拆成两份 |

## 配置文件

迁移期间常用配置：

```yaml
# docs/.docs-contract.yml
exempt_paths:
  - docs/architecture/archived/**     # 历史归档不审
  - docs/design-drafts/**             # 设计期临时材料
must_not_contain_extra:
  PROJECT.md: ["TODO"]                # 临时收紧 PROJECT.md 的硬规则
```
