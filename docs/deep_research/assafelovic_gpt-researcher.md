# assafelovic/gpt-researcher 深度研究实现分析

## 项目定位
典型的开源 deep research agent，核心是“规划 + 并发检索 + 递归加深 + 报告生成”。

## 架构分层
- `GPTResearcher` 主编排对象负责生命周期管理。
- `DeepResearchSkill` 负责 deep research 专属流程（breadth/depth/concurrency）。
- retriever/browser/context/writer 等 skill 组件化。

## Deep Research 实现思路
- 先生成初始研究问题与 SERP 查询。
- 每个查询并发执行检索与内容处理，提取 learnings/follow-up questions/citations。
- 采用递归策略：`depth` 递减、`breadth` 收缩，持续细化问题。
- 汇总后做上下文裁剪（词数限制）并交给报告生成阶段。

## 关键实现文件
- `github_cache/deep_research_repos/gpt-researcher/gpt_researcher/agent.py`
- `github_cache/deep_research_repos/gpt-researcher/gpt_researcher/skills/deep_research.py`
- `github_cache/deep_research_repos/gpt-researcher/gpt_researcher/actions/retriever.py`

## 可复用方案
- breadth/depth 参数化递归非常适合做“深度预算”控制。
- 研究上下文与 citation 分开管理，便于后处理。
- 多检索器 + MCP 扩展位设计合理。

## 局限与注意点
- 部分解析使用格式约定与正则，面对模型输出漂移时鲁棒性一般。
- 递归 + 并发在大任务下成本增长快，需要配额控制。
