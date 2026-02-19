# langchain-ai/open_deep_research 深度研究实现分析

## 项目定位
LangGraph 驱动的开放 deep research 框架，强调可配置、可评测、可并行。

## 架构分层
- 顶层图：澄清问题 -> 研究简报 -> 监督者执行 -> 最终报告。
- 监督者子图：分解任务并派发并行研究单元。
- 研究者子图：工具调用、结果压缩、回传 supervisor。
- 配置层：模型、搜索 API、MCP、并发度、迭代上限。

## Deep Research 实现思路
- Supervisor 使用工具（ConductResearch/ResearchComplete/think）进行任务分配。
- Researcher 执行检索与工具调用，达到阈值后压缩研究结果。
- Supervisor 汇总多 researcher 输出并循环迭代，最终进入报告生成节点。

## 关键实现文件
- `github_cache/deep_research_repos/open_deep_research/src/open_deep_research/deep_researcher.py`
- `github_cache/deep_research_repos/open_deep_research/src/open_deep_research/configuration.py`
- `github_cache/deep_research_repos/open_deep_research/src/open_deep_research/prompts.py`

## 可复用方案
- “Supervisor-Researcher 双层图”是高可扩展深度研究模式。
- 配置项完整，适合做平台化产品。

## 局限与注意点
- 依赖 LangGraph/LangChain 生态，迁移到其它 runtime 需要改造。
- 并行研究单元较多时，成本和限流压力明显。
