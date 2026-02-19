# MiroMindAI/MiroThinker 深度研究实现分析

## 项目定位
高性能研究代理框架，强调长上下文、多工具调用上限和评测成绩（更偏“研究系统 + 生产框架”）。

## 架构分层
- Orchestrator：主循环调度 LLM、工具、子代理。
- ToolExecutor：执行工具并处理回滚/错误。
- Stream/Logging：实时流式事件 + 任务日志。
- 配置层：多 Agent/多 benchmark 预设。

## Deep Research 实现思路
- 在统一 orchestrator 中处理主代理与子代理协作。
- 对格式错误、拒答、重复 query 做防抖与回滚控制。
- 将中间答案、工具结果、上下文压缩纳入同一执行状态机。

## 关键实现文件
- `github_cache/deep_research_repos/MiroThinker/apps/miroflow-agent/src/core/orchestrator.py`
- `github_cache/deep_research_repos/MiroThinker/apps/miroflow-agent/src/core/tool_executor.py`
- `github_cache/deep_research_repos/MiroThinker/apps/miroflow-agent/src/core/pipeline.py`

## 可复用方案
- 工程级容错完善（回滚、重试、拒答检测、去重）。
- 主代理与子代理工具暴露机制可直接复用到复杂任务编排。

## 局限与注意点
- 系统复杂，初次定制成本高。
- 需要较强算力与完整工具生态才能发挥优势。
