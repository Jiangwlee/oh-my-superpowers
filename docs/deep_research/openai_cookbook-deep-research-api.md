# openai/openai-cookbook — Deep Research API 官方示例分析

## 项目定位
OpenAI 官方 Cookbook 中的 Deep Research API 示例，演示如何调用 OpenAI 专用深度研究模型（`o3-deep-research` / `o4-mini-deep-research`）完成自动化研究工作流。

- **仓库**: https://github.com/openai/openai-cookbook
- **示例路径**: `examples/deep_research_api/`
- **Cookbook 页面**: https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api
- **性质**: OpenAI **官方** API 示例

## Deep Research 专用模型

| 模型 | 特点 | 适用场景 |
|------|------|---------|
| `o3-deep-research-2025-06-26` | 高质量深度合成，推理更强 | 复杂研究任务 |
| `o4-mini-deep-research-2025-06-26` | 轻量快速，低延迟 | 简单查询 / 成本敏感 |

## 核心 API 调用方式

通过 `responses` 端点调用：

```python
from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="o3-deep-research-2025-06-26",
    input="请研究 2025 年量子计算领域的主要进展",
    tools=[{"type": "web_search_preview"}],
)
print(response.output_text)
```

## 两种示例

### 1. 基础示例（introduction_to_deep_research_api.ipynb）
- 直接调用 Deep Research 模型。
- 模型自主规划子问题、执行 Web 搜索、合成引用报告。
- 适合快速接入。

### 2. Agents SDK 集成示例（introduction_to_deep_research_api_agents.ipynb）
- 将 Deep Research 模型嵌入 OpenAI Agents SDK 工作流。
- 结合 MCP Server 接入内部私有文件（如企业知识库）。
- 支持工具链扩展：Web Search + 代码执行 + 自定义 MCP 工具。

## 与 openai/sample-deep-research-mcp 的关系

| 项目 | 角色 |
|------|------|
| `openai/sample-deep-research-mcp` | 展示如何为 Deep Research 模型**提供自定义数据源**（MCP Server 端） |
| `openai-cookbook/deep_research_api` | 展示如何**调用** Deep Research 模型并集成 MCP Client |

两者互补：一个是数据源侧示例，一个是消费侧示例。

## 可复用方案

- Deep Research API 最简集成模板（约 10 行代码）。
- MCP + Agents SDK 组合：私有知识库接入 Deep Research 的标准做法。
- 双模型策略参考：重任务用 o3，轻任务用 o4-mini，按需切换。

## 局限与注意点

- 依赖 OpenAI 专有模型，无法替换为开源 LLM。
- Deep Research 模型仅通过 `responses` 端点访问（非 `chat/completions`）。
- 成本较高，o3-deep-research 每次研究可能消耗大量 token。
