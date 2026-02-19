# Deep Research 项目横向对比总表

## 对比维度说明
- 架构模式：单代理递归 / Supervisor-Worker / ReAct 工具循环 / 平台型工作流
- 迭代策略：如何“继续深入”
- 工具链：搜索、抓取、MCP、代码执行等
- 适用场景：最推荐的落地环境

## 18 项目总览

| 项目 | 架构模式 | 迭代策略 | 主要工具链 | 优势 | 局限 | 适用场景 |
|---|---|---|---|---|---|---|
| `khoj-ai/khoj` | 平台型多工具编排 | 按 `ResearchIteration` 状态推进 | 文档检索/联网搜索/读网页/代码/MCP | 工程化完整、可扩展强 | 架构较重 | 企业级统一 AI 平台 |
| `assafelovic/gpt-researcher` | 单代理 + 组件化 skill | breadth/depth 递归 + 并发 | 多 retriever + MCP + 报告生成 | 开源生态成熟、上手快 | 复杂任务成本上升快 | 通用 deep research 服务 |
| `dzhng/deep-research` | 轻量递归树 | breadth/depth 递归 + 收缩 | Firecrawl + LLM 结构化输出 | 代码极简、易改造 | 事实校验能力弱 | 原型验证、教学样例 |
| `Alibaba-NLP/DeepResearch` | ReAct 长链路工具调用 | 工具调用循环直到 `<answer>` | search/visit/scholar/python/parse_file | 研究性能强、评测导向 | 部署复杂、依赖多 | 学术评测/高强度任务 |
| `arc53/DocsGPT` | 平台型 Agent + Workflow | ReAct 或工作流节点迭代 | RAG + 工具 + MCP | 企业私有化能力强 | deep research 逻辑分散 | 知识库/客服/企业助手 |
| `google-deepmind/deepmind-research` | 论文代码集合 | 无统一 deep research 流程 | 各论文自定义 | 算法参考价值高 | 非可直接落地的 agent | 研究参考/算法借鉴 |
| `langchain-ai/open_deep_research` | Supervisor-Researcher LangGraph | supervisor 反思并并行派发 | Tavily/OpenAI/Anthropic + MCP | 架构先进、可配置可评测 | 依赖 LangGraph 生态 | 可产品化深度研究引擎 |
| `langchain-ai/local-deep-researcher` | 本地 LangGraph 循环 | summarize-reflect-query 循环 | Ollama/LMStudio + 多搜索 API | 本地部署友好、隐私好 | 模型稳定性依赖本地模型 | 本地私有研究助手 |
| `zilliztech/deep-searcher` | DeepSearch Agent + 向量库 | 子问题分解 + gap query 反思 | Milvus/向量检索 + LLM | 私有数据研究能力强 | token 成本高、互联网检索弱 | 企业内部知识研究 |
| `MiroMindAI/MiroThinker` | Orchestrator + 子代理协作 | 受控多轮工具调用 | ToolManager + 多模型 + benchmark 配置 | 容错强、长任务能力强 | 系统复杂度高 | 高性能研究代理平台 |
| `openai/sample-deep-research-mcp` | MCP 最小示例 | 无（提供工具接口） | FastMCP `search/fetch` | 官方示例清晰 | 不含完整研究闭环 | 自定义数据源接入样板 |
| `milkymap/anthropic-deep-research` | Claude 主循环 + OpenAI 搜索 | tool_use 触发 deep iterative search | Anthropic streaming + OpenAI search | 双模型解耦思路直观 | 鲁棒性和工程能力有限 | 轻量实验/PoC |
| `nickscamara/open-deep-research` | 产品化 chat tool | 深度循环 + 时间/失败阈值 | Firecrawl + AI SDK + Next.js | 产品体验好、进度可视化 | 路由逻辑集中、扩展性一般 | Web 应用快速落地 |
| `bytedance/deer-flow` | Orchestrator + 并行子代理 + 沙盒 | 子代理并行 + 主控反思补洞 | LangGraph + Docker 沙盒 + Memory | 长任务能力强、工业级工程 | 框架重、Docker 依赖 | 复杂长链路研究任务 |
| `google-gemini/gemini-fullstack-langgraph-quickstart` | LangGraph 循环 + React 全栈 | reflect 节点判断知识充分性 | Gemini 原生 Google Search + LangGraph | Google 官方、全栈一体 | 绑定 Gemini / Google Search | 生产级参考 Demo |
| `jina-ai/node-DeepResearch` | 轻量 ReAct 循环 | token 预算耗尽 or 找到答案 | Jina Reader + Gemini/OpenAI | 极简实现、答案精准 | 仅适合 QA，不擅长长报告 | 精准问答 / 低延迟场景 |
| `LearningCircuit/local-deep-research` | 本地迭代循环 + 多源路由 | summarize-reflect 循环 | 10+ 来源（arXiv/PubMed/Web 等） | 多源覆盖广、隐私安全 | AGPL / 小模型效果下降 | 本地隐私研究 / 学术检索 |
| `openai/cookbook-deep-research-api` | 托管 API（o3/o4-mini） | 模型内部自主规划（黑盒） | OpenAI Deep Research API + MCP | 官方 API、接入最简单 | 绑定 OpenAI、成本高 | 企业级快速接入 OpenAI |

## 架构模式归类

### 1. 单代理递归型
- `assafelovic/gpt-researcher`
- `dzhng/deep-research`
- `zilliztech/deep-searcher`

特点：实现直接、易理解。适合快速上线，但规模扩大后要重点补限流与成本控制。

### 2. Supervisor-Worker 多代理型
- `langchain-ai/open_deep_research`
- `MiroMindAI/MiroThinker`
- `bytedance/deer-flow`（Orchestrator + 并行子代理）

特点：扩展性和任务分解能力最强，适合复杂研究任务。

### 3. ReAct 工具循环型
- `Alibaba-NLP/DeepResearch`
- `milkymap/anthropic-deep-research`
- `jina-ai/node-DeepResearch`（token 预算终止）

特点：工具调用自由度高，适合开放式探索；要重视输出格式约束与回滚策略。

### 4. 平台工作流型
- `khoj-ai/khoj`
- `arc53/DocsGPT`
- `nickscamara/open-deep-research`（偏产品封装）
- `google-gemini/gemini-fullstack-langgraph-quickstart`（Google 官方全栈）

特点：落地能力强，便于业务接入；抽取”纯算法内核”较难。

### 5. 本地隐私型
- `langchain-ai/local-deep-researcher`
- `LearningCircuit/local-deep-research`（10+ 来源路由）

特点：零数据外泄，适合企业私有或个人隐私场景；效果依赖本地模型质量。

### 6. 托管 API 型（黑盒）
- `openai/cookbook-deep-research-api`（o3/o4-mini-deep-research）

特点：接入成本最低，10 行代码可跑；但完全依赖供应商，无法自定义内部逻辑。

## 选型建议

### 若目标是”最快做出可跑 deep research”
- 首选：`dzhng/deep-research`（极简代码，易改造）
- 备选：`openai/cookbook-deep-research-api`（直接调 API，不用写循环）

### 若目标是”企业私有知识 + 深度研究”
- 首选：`zilliztech/deep-searcher`（私有数据检索）
- 备选：`khoj-ai/khoj`、`arc53/DocsGPT`（平台能力更全）

### 若目标是”高性能复杂任务、多代理可扩展”
- 首选：`langchain-ai/open_deep_research`
- 进阶：`bytedance/deer-flow`（工业级，有沙盒 + 长期记忆）

### 若目标是”本地隐私 / 学术研究（arXiv/PubMed）”
- 首选：`LearningCircuit/local-deep-research`（10+ 来源路由，95% SimpleQA 准确率）
- 备选：`langchain-ai/local-deep-researcher`（更轻量）

### 若目标是”学习 Google 官方架构 / 全栈 Demo”
- 首选：`google-gemini/gemini-fullstack-langgraph-quickstart`

### 若目标是”接入 OpenAI Deep Research 的 MCP 数据源”
- 起点：`openai/sample-deep-research-mcp`（Server 端）+ `openai/cookbook-deep-research-api`（Client 端）

## 共同实现模式（可抽象为统一模板）
1. 任务澄清/问题分解
2. 检索与抓取（多源并发）
3. 信息压缩（结构化 learnings）
4. 反思补洞（gap questions）
5. 终止判断（深度、时间、失败率、收益）
6. 最终合成（带引用）

