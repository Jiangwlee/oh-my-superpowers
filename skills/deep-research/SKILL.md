---
name: deep-research
description: >-
  Use when a task requires systematic multi-round research across multiple
  angles, sources, and validation steps before producing a conclusion or
  report. Do NOT use when a quick ad-hoc search, a single-page summary, or a
  one-off fact lookup is enough.
---

# deep-research Skill

深度研究工作流。核心目标是把“搜一搜”升级为：
- 先拆研究目标
- 再做 broad exploration
- 再做 targeted deep dive
- 再做 diversity / validation
- 最后输出 `brief` 与可审计的 `full report`

它适合多轮研究，不适合一次性的临时搜索或单页总结。

## 统一入口

```bash
omp-deep-research <subcommand> [args]
```

主入口支持四类动作：
- `init`
- `save-source`
- `update-state`
- `build-report`

详细参数不要硬记，按需读取 `references/cli.md`。

## 研究 SOP

推荐的使用顺序：

1. 先澄清研究目标和子问题
2. 做 broad exploration，识别关键维度和关键词
3. 对关键维度做 deep dive，读关键全文而不是只看 snippet
4. 主动补齐不同类型的证据和反方/限制信息
5. 每轮结束做 synthesis check，判断是否继续
6. 最终生成两层产物
   - `brief`
   - `full report`

如果研究还没有覆盖多个角度、缺乏关键来源、或缺少反方/限制信息，就不应过早结束。

---

## 数据目录

默认路径：`~/.local/share/oh-my-superpowers/deep-research/`

可通过环境变量 `DEEP_RESEARCH_DATA_DIR` 覆盖。

## 何时加载详细文档

详细文档索引：`references/README.md`

只在需要时加载：
- 研究流程与阶段目标：`references/methodology.md`
- 来源优先级与搜索策略：`references/source-strategy.md`
- 停止条件：`references/stop-criteria.md`
- 报告格式与审计要求：`references/reporting.md`
- CLI 详细参数：`references/cli.md`
- workspace 结构与文件命名：`references/workspace.md`
- research state / payload 结构：`references/state-schema.md`
