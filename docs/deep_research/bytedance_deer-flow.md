# bytedance/deer-flow 深度研究实现分析

## 项目定位
ByteDance 出品的开源 Super Agent 框架，通过编排子代理、持久记忆和沙盒执行环境处理复杂长链任务（分钟级到小时级）。

- **Stars**: ~20k
- **License**: MIT
- **GitHub**: https://github.com/bytedance/deer-flow
- **技术栈**: Python (32.9%) + TypeScript (42.1%)，基于 LangGraph + LangChain

## 架构分层

- **Orchestrator（主控）**: 接收用户意图，分解为子任务，并行派发给子代理。
- **Sub-Agents（子代理）**: 各司其职，支持并行执行，结果汇回主控。
- **Memory 模块**: 跨会话持久化长期记忆，支持状态追踪。
- **Sandbox 执行环境**: Docker 隔离容器，支持代码执行 + 文件系统访问。
- **Skills 模块**: 可渐进加载的技能集，用于管理上下文窗口。

## Deep Research 实现思路

- Orchestrator 做意图解析 + 任务分解，生成并行研究子任务。
- 每个子代理独立执行 ReAct 循环（搜索 → 阅读 → 推理）。
- 子代理结果汇聚后，主控做反思补洞（gap analysis）再触发新一轮研究。
- Memory 模块确保多轮/多会话的研究状态可延续。
- 沙盒支持代码计算验证，增强事实可信度。

## 关键实现文件（GitHub 路径）

- `src/agents/` — 子代理实现
- `src/memory/` — 长期记忆模块
- `src/skills/` — 渐进加载 Skills

## 可复用方案

- Sub-Agent 并行派发模式：主控 + 多并行研究子代理，是高吞吐研究引擎的标准架构。
- Memory 持久化设计：适合需要跨次研究积累知识的场景。
- Skills 渐进加载：缓解长上下文成本问题的工程实践参考。

## 局限与注意点

- 整体框架较重，引入成本高。
- 依赖 Docker 沙盒，部署环境要求较高。
- 与 LangGraph 深度绑定，迁移到其他 runtime 需要较大改造。
