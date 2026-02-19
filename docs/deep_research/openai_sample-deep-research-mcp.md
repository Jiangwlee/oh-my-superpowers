# openai/sample-deep-research-mcp 深度研究实现分析

## 项目定位
官方最小示例：演示如何实现一个可被 Deep Research 使用的 MCP Server。

## 架构分层
- 数据层：`records.json` 静态数据。
- MCP 服务层：FastMCP 注册 `search`、`fetch` 两个工具。
- 传输层：SSE (`transport="sse"`)。

## Deep Research 实现思路
- 该仓库不实现完整 deep research agent。
- 它提供“可检索 + 可拉取详情”的 MCP 接口，供上层 deep research agent 调用。

## 关键实现文件
- `github_cache/deep_research_repos/sample-deep-research-mcp/sample_mcp.py`
- `github_cache/deep_research_repos/sample-deep-research-mcp/records.json`

## 可复用方案
- 用最小工具集定义 MCP 协议契约（search/fetch）非常清晰。
- 适合作为“自定义私有数据源接入 deep research”的脚手架。

## 局限与注意点
- 仅示例级实现，不含复杂权限、分页、排序、来源质量控制。
