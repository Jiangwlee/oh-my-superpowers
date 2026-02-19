# nickscamara/open-deep-research 深度研究实现分析

## 项目定位
面向产品体验的 Web 应用（Next.js + AI SDK），在聊天流中内置 deep research 工具。

## 架构分层
- 前端交互层：聊天 UI、进度与活动流。
- API 路由层：`/api/chat` 中注册 deepResearch 工具。
- 研究执行层：search/extract/analyze/synthesis 循环。

## Deep Research 实现思路
- 在工具 `deepResearch` 中维护 `researchState`（depth、findings、summaries、失败次数、进度）。
- 每轮流程：搜索 -> 提取网页 -> 分析缺口/下一主题 -> 决定继续。
- 受时间限制（4.5 分钟）和失败阈值控制，避免失控长任务。
- 最后统一 synthesis 生成超长分析并附带来源。

## 关键实现文件
- `github_cache/deep_research_repos/open-deep-research/app/(chat)/api/chat/route.ts`
- `github_cache/deep_research_repos/open-deep-research/lib/ai/prompts.ts`
- `github_cache/deep_research_repos/open-deep-research/lib/ai/index.ts`

## 可复用方案
- 产品化细节很完整：进度事件、source 流、activity 状态。
- 把深度研究封装为单个工具，便于挂入任意聊天代理。

## 局限与注意点
- 研究循环主要在单文件 route 内，后续扩展时建议拆服务层。
- 时间驱动截断可能导致复杂问题研究深度不足。
