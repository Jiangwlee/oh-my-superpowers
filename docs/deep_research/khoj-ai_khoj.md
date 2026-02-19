# khoj-ai/khoj 深度研究实现分析

## 项目定位
Khoj 是一个“个人/企业 AI second brain”平台，Deep Research 只是其多能力中的一个模式（`/research`），与通用聊天、文档检索、自动化、Agent Builder 共用底层能力。

## 架构分层
- API/路由层：研究路由与会话管理。
- 工具执行层：文档检索、联网搜索、网页阅读、代码执行、MCP 工具调用。
- 研究编排层：按迭代（ResearchIteration）驱动工具调用与上下文累积。
- 模型交互层：把工具结果回灌模型，继续下一轮决策。

## Deep Research 实现思路
- 由 `research.py` 统一编排“模型生成动作 -> 执行工具 -> 回写上下文 -> 继续迭代”。
- 支持多工具并行执行（文档检索、联网检索、读网页、代码、MCP），并在每轮合并结构化结果。
- 工具调用历史通过 `construct_tool_chat_history`/`construct_iteration_history` 组织，减少模型丢上下文。
- 允许中断控制、状态消息、终止条件判断，适合长任务。

## 关键实现文件
- `github_cache/deep_research_repos/khoj/src/khoj/routers/research.py`
- `github_cache/deep_research_repos/khoj/src/khoj/processor/tools/mcp.py`
- `github_cache/deep_research_repos/khoj/src/khoj/processor/operator/operator_agent_openai.py`

## 可复用方案
- “统一工具协议 + 统一状态机”模式：把多工具能力抽象到同一执行框架。
- MCP 客户端同时支持 `stdio` 与 `sse`，便于本地/远程工具扩展。
- 每轮状态与上下文显式持久化，利于追踪与调试。

## 局限与注意点
- 架构较重，接入成本高于轻量 deep research 项目。
- 研究能力与全平台能力耦合，二次裁剪时需要拆依赖。
