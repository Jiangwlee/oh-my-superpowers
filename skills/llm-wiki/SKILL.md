---
name: llm-wiki
description: >-
  Use when building or maintaining an LLM-powered knowledge base with `omp wiki`. Triggers: 'add to wiki', 'ingest this article/URL',
  'what do I know about', 'search my wiki', 'lint my wiki', 'compile wiki', 'knowledge base', '加入知识库', '存入 wiki',
  '查一下我的 wiki', or any mention of 'llm wiki' or 'omp wiki'.
---

# llm-wiki

管理一个 LLM 原生的知识仓库：存入原始数据、编译成知识、问答、维护质量。

## Ingest

用户提供 URL、文件或文本时触发。

```bash
omp wiki ingest <url-or-file>
omp wiki ingest --text --title <title>   # 从 stdin 读取
```

CLI 将源文件标准化后存入 `raw/`，然后执行编译 SOP：

1. 运行 `omp wiki nav --json`，获取 `pending_synthesis` 列表。
2. 按 `references/compile.md` 编译：写 `wiki/sources/<slug>.md`，提取概念到 `wiki/concepts/`，级联更新相关页面，标注冲突。
3. 追加 `wiki/log.md`。
4. 运行 `omp wiki lint`，修复断链后结束。

加载：`references/compile.md` + `references/source-template.md`（步骤 2 前）。

## Query

用户询问「我对 X 了解多少」或需要从 wiki 检索知识时触发。

无 CLI，直接读 wiki 文件：

1. 运行 `omp wiki nav` 获取 wiki 文件列表，根据 slug 名称判断相关性。
2. 按需读 `wiki/sources/`、`wiki/concepts/`、`wiki/maps/` 中的相关文件。
3. 优先使用编译页面；覆盖不足时明确告知，不降级到 `raw/`。
4. 引用使用 markdown 相对链接。

如需归档答案回 wiki，加载 `references/archive.md`。

## Lint

用户说「lint my wiki」、编译后、或内容/链接可能漂移时触发。

```bash
omp wiki lint [--json]
```

- **Deterministic**（自动修复）：断 wikilink、index 缺失条目、失效 raw 引用。
- **Heuristic**（仅报告）：内容矛盾、孤儿页、过时声明。

有未解决问题时，不得声明 wiki 健康。加载 `references/linting.md` 处理具体问题。

## References

| 场景 | 加载 |
|------|------|
| ingest/compile 过程 | `references/compile.md` |
| lint 结果处理 | `references/linting.md` |
| 归档查询答案 | `references/archive.md` |
| 需要完整 CLI 参数 | `references/cli.md` |
| 写 source 页面 | `assets/source-template.md` |
| 写 concept 页面 | `assets/concept-template.md` |
| 写 map 页面 | `assets/map-template.md` |
