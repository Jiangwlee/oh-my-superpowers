# langchain-ai/local-deep-researcher 深度研究实现分析

## 项目定位
本地化 deep research assistant，重点是“本地模型 + 本地部署 + 迭代检索反思”。

## 架构分层
- LangGraph state graph（query -> search -> summarize -> reflect 循环）。
- LLM 层支持 Ollama/LMStudio。
- 搜索层支持 DuckDuckGo/SearXNG/Tavily/Perplexity。

## Deep Research 实现思路
- 先由模型生成搜索 query。
- 执行搜索并标准化来源文本。
- 生成阶段性总结后进行 reflection（识别知识缺口）。
- 产出下一轮查询，直到达到循环上限，再输出最终 markdown 报告与来源。

## 关键实现文件
- `github_cache/deep_research_repos/local-deep-researcher/src/ollama_deep_researcher/graph.py`
- `github_cache/deep_research_repos/local-deep-researcher/src/ollama_deep_researcher/prompts.py`
- `github_cache/deep_research_repos/local-deep-researcher/src/ollama_deep_researcher/configuration.py`

## 可复用方案
- 本地模型适配（tool calling/JSON 双模式）很实用。
- 迭代式“总结-反思-新查询”闭环简洁有效。

## 局限与注意点
- 本地模型稳定性差异大，结构化输出需要兜底机制。
- 搜索质量受所选 search API 明显影响。
