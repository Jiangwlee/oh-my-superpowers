# dzhng/deep-research 深度研究实现分析

## 项目定位
极简实现（小代码量）deep research agent，强调“可读性优先”。

## 架构分层
- 查询生成：LLM 生成 SERP queries 与 research goals。
- 检索执行：Firecrawl 搜索并抓取 markdown。
- 结果压缩：从检索内容抽取 learnings 与 follow-up questions。
- 递归控制：基于 depth/breadth 迭代深入。

## Deep Research 实现思路
- 每层生成 N 个查询并并发检索。
- 每个查询提炼学习点后形成下一层研究方向。
- 深度耗尽后输出 `learnings + visitedUrls`，再生成最终报告。
- `p-limit` 控制并发，避免 API 限流。

## 关键实现文件
- `github_cache/deep_research_repos/deep-research/src/deep-research.ts`
- `github_cache/deep_research_repos/deep-research/src/prompt.ts`
- `github_cache/deep_research_repos/deep-research/src/ai/providers.ts`

## 可复用方案
- “递归研究树”结构清晰，适合快速移植到其它框架。
- 把报告生成和研究循环分离，便于替换模型或输出格式。

## 局限与注意点
- 对来源质量控制较轻，主要依赖搜索结果质量。
- 缺少更细粒度的事实验证/冲突消解环节。
