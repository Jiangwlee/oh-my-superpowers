# arc53/DocsGPT 深度研究实现分析

## 项目定位
DocsGPT 是企业私有知识/Agent 平台，“deep research”能力以内置 Agent 与 Workflow 方式提供，不是单一独立 deep research 引擎。

## 架构分层
- Agent 层：classic/react/workflow 多 agent 形态。
- Workflow 层：可视化节点图执行（WorkflowEngine）。
- Tool/RAG 层：检索、外部工具、MCP、提示词编排。

## Deep Research 实现思路
- 通过 ReAct agent 或 Workflow graph 编排研究流程。
- 支持“源数据 + 工具调用 + 多轮推理”的组合式执行。
- 运行记录（workflow runs）可持久化，便于审计与复盘。

## 关键实现文件
- `github_cache/deep_research_repos/DocsGPT/application/agents/workflow_agent.py`
- `github_cache/deep_research_repos/DocsGPT/application/agents/react_agent.py`
- `github_cache/deep_research_repos/DocsGPT/application/agents/workflows/workflow_engine.py`
- `github_cache/deep_research_repos/DocsGPT/application/seed/config/premade_agents.yaml`

## 可复用方案
- “工作流图 + Agent”组合适合企业流程化研究场景。
- 对私有数据源和多模型/多工具接入较友好。

## 局限与注意点
- deep research 逻辑分散在平台能力中，抽取单独算法成本较高。
- 需要数据库与完整平台配套，轻量化运行成本高于纯 agent 项目。
