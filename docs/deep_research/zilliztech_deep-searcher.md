# zilliztech/deep-searcher 深度研究实现分析

## 项目定位
面向私有数据的 deep search/deep research 方案，核心是“向量检索 + 反思迭代 + 报告生成”。

## 架构分层
- API 层（FastAPI）暴露加载与查询接口。
- Agent 层（DeepSearch）执行分解、检索、反思、总结。
- 数据层（Milvus/向量库）承载离线文档与网页加载结果。

## Deep Research 实现思路
- 将原始问题分解为子问题（SUB_QUERY_PROMPT）。
- 对每个子问题做向量检索，并用 YES/NO 重排过滤片段。
- 反思阶段生成 gap queries，再做下一轮检索。
- 到达迭代上限或无新问题后，汇总所有 chunk 生成最终报告。

## 关键实现文件
- `github_cache/deep_research_repos/deep-searcher/deepsearcher/agent/deep_search.py`
- `github_cache/deep_research_repos/deep-searcher/deepsearcher/online_query.py`
- `github_cache/deep_research_repos/deep-searcher/main.py`

## 可复用方案
- “子问题分解 + 反思补洞”适合企业知识库场景。
- 检索与总结分离，便于替换向量库和模型。

## 局限与注意点
- 对 chunk 级别逐条 LLM 评估，token 成本较高。
- 默认互联网检索仍较弱（代码中有 TODO 标记）。
