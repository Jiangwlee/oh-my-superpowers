# jina-ai/node-DeepResearch 深度研究实现分析

## 项目定位
Jina AI 出品的 Node.js Deep Research 实现，核心理念是"持续搜索直到找到答案或预算耗尽"，强调**答案精准性**而非长篇报告生成。

- **Stars**: 5.1k
- **License**: Apache-2.0
- **GitHub**: https://github.com/jina-ai/node-DeepResearch
- **技术栈**: Node.js / TypeScript
- **托管 API**: search.jina.ai

## 架构分层

- **问题解析层**: 将原始问题转化为结构化搜索意图。
- **搜索执行层**: 调用 Jina Reader API（`r.jina.ai`）进行网页抓取与内容提取，支持 Google 搜索。
- **推理循环层**: LLM（Gemini 或 OpenAI）对已收集信息做推理，判断是否可回答问题。
- **预算控制层**: 基于 token 消耗设置硬性上限，超出则强制终止并输出当前最佳答案。

## Deep Research 实现思路

1. 接收问题后，LLM 生成初始搜索查询。
2. 用 Jina Reader 抓取网页正文（去除 HTML 噪音）。
3. LLM 对抓取内容做实时推理：
   - 若信息充分 → 输出 `<answer>`。
   - 若信息不足 → 生成新查询，继续搜索。
4. token 预算耗尽时，输出"当前最佳推断"。

## 与其他项目的区别

- **目标不同**: 大多数项目目标是生成完整报告；本项目目标是**找到精准答案**（类 QA）。
- **工具自研**: Jina Reader 是自家工具，整合紧密；其他项目多用 Firecrawl / Tavily。
- **代码极简**: Node.js 实现，单文件可运行，无重框架依赖。

## 关键实现文件（GitHub 路径）

- `src/agent.ts` — 核心研究循环
- `src/tools/jina-reader.ts` — Jina Reader 集成
- `src/utils/token-tracker.ts` — token 预算控制

## 可复用方案

- **token 预算终止策略**: 硬限制而非基于反思判断，实现最简单，适合成本敏感场景。
- **答案精准型循环**: 适合 QA 类任务（不适合生成长报告）。

## 局限与注意点

- 依赖 Jina Reader API，网页质量受限于 Jina 的解析能力。
- 以"找答案"为目标，不适合需要多角度综合分析的研究场景。
- Node.js 实现，Python 项目迁移成本较高。
