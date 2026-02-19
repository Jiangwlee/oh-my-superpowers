# milkymap/anthropic-deep-research 深度研究实现分析

## 项目定位
轻量级 Anthropic + OpenAI 混合方案：Claude 负责主循环与工具决策，OpenAI 搜索模型负责网页检索。

## 架构分层
- 主代理循环：Anthropic streaming + tool_use。
- 工具层：`simple_web_search`、`deep_iterative_web_search`。
- 检索执行层：OpenAI `gpt-4o-mini-search-preview` 并行查询。

## Deep Research 实现思路
- `run()` 驱动长期对话循环。
- 当 Claude 触发工具调用时，进入 deep iterative web search。
- deep 模式内部多轮迭代：搜索 -> 汇总 -> 再搜索，直到 stop condition 或迭代上限。
- 最终把工具结果作为 `tool_result` 回填主对话。

## 关键实现文件
- `github_cache/deep_research_repos/anthropic-deep-research/src/anthropic_openai/agent_loop.py`
- `github_cache/deep_research_repos/anthropic-deep-research/src/anthropic_openai/definitions.py`

## 可复用方案
- “决策模型与搜索模型解耦”便于做成本/性能分层。
- streaming 事件消费与 tool 回填流程完整。

## 局限与注意点
- 依赖输出格式稳定性，工具参数解析脆弱点较多。
- 代码规模小，生产级容错与观测能力不足。
