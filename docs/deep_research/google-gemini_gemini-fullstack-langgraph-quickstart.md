# google-gemini/gemini-fullstack-langgraph-quickstart 深度研究实现分析

## 项目定位
Google 官方出品的全栈 Deep Research 示例，展示如何用 Gemini 2.5 + LangGraph 构建生产级研究应用。

- **Stars**: 17.9k
- **License**: Apache-2.0
- **GitHub**: https://github.com/google-gemini/gemini-fullstack-langgraph-quickstart
- **技术栈**: React 前端 + LangGraph Python 后端

## 架构分层

- **前端（React）**: 用户输入 + 流式展示研究进度 + 引用来源。
- **后端（LangGraph Graph）**:
  - `generate_queries` 节点: 生成多个搜索查询。
  - `web_research` 节点: 调用 Gemini 内置 Google Search 工具执行检索。
  - `reflect` 节点: 对已有 learnings 做反思，判断是否存在知识缺口。
  - `finalize_answer` 节点: 合并所有 learnings，生成带引用的最终答案。
- **循环控制**: `reflect` 节点判断知识是否充分，充分则终止；否则返回 `generate_queries` 继续迭代。

## Deep Research 实现思路

1. 用 Gemini 2.5 Flash 做快速搜索查询生成（低成本）。
2. 每个查询通过 Gemini 的原生 Google Search grounding 工具检索。
3. `reflect` 节点用 Gemini Pro 做高质量反思：评估是否可以回答原始问题。
4. 循环直到充分或达到最大迭代次数。
5. 最终由 Gemini Pro 合成带引用的 Markdown 答案。

## 关键实现文件（GitHub 路径）

- `backend/src/agent/graph.py` — 核心 LangGraph 状态机
- `backend/src/agent/nodes.py` — 各节点实现（查询/检索/反思/合成）
- `frontend/src/` — React 流式前端

## 与其他项目的区别

| 特征 | 本项目 | langchain-ai/open_deep_research |
|------|--------|----------------------------------|
| 来源 | Google 官方 | LangChain 社区 |
| 搜索工具 | Gemini 原生 Google Search | Tavily / 可配置 |
| 前端 | 内置 React UI | 无内置前端 |
| 适用模型 | Gemini 2.5 系列 | 多 LLM 可配置 |
| 复杂度 | 相对轻量 | 支持更复杂的 Supervisor-Worker |

## 可复用方案

- `reflect` 节点的反思判断逻辑：用 LLM 判断 "现有信息是否足以回答问题"，是最简洁的终止条件实现。
- 双模型策略（Flash 查询 + Pro 反思）：有效控制成本。

## 局限与注意点

- 搜索能力依赖 Gemini 原生 Google Search grounding，不易替换成其他搜索引擎。
- 框架仍绑定 LangGraph，对 LangGraph 不熟悉的团队需要学习成本。
