# LearningCircuit/local-deep-research 深度研究实现分析

## 项目定位
隐私优先的本地化深度研究助手，SimpleQA 基准测试约 95% 准确率，支持搜索 10+ 来源（arXiv、PubMed、Web 等）及本地私有文档，全程本地加密。

- **Stars**: 4k+
- **License**: AGPL-3.0
- **GitHub**: https://github.com/LearningCircuit/local-deep-research
- **技术栈**: Python，支持 Ollama / 本地模型 + 云端 LLM（Anthropic、Google）

## 架构分层

- **搜索源路由层**: 根据查询类型自动或手动路由到最合适的搜索引擎（Web / arXiv / PubMed / Wikipedia / 本地文档等）。
- **迭代研究循环**: 搜索 → 摘要 → 反思知识缺口 → 生成新查询 → 循环。
- **本地加密存储**: 所有中间数据和最终报告存储于本地加密数据库，零知识架构。
- **报告生成层**: 合成带引用的 Markdown 报告。

## 搜索来源支持（10+）

| 来源 | 适用场景 |
|------|---------|
| Web (DuckDuckGo/Brave/SerpAPI) | 通用查询 |
| arXiv | 学术论文 |
| PubMed | 医疗/生命科学 |
| Wikipedia | 百科知识 |
| 本地文档 | 私有知识库 |
| GitHub | 代码/技术文档 |
| Semantic Scholar | 引用追踪 |

## Deep Research 实现思路

1. 问题分解为初始子问题列表。
2. 每个子问题路由到最合适的搜索来源。
3. 检索结果压缩为结构化 learnings。
4. LLM 反思：已有信息能否回答原始问题？存在哪些知识缺口？
5. 针对缺口生成新查询，继续循环。
6. 生成带引用的最终 Markdown 报告。

## 关键实现文件（GitHub 路径）

- `local_deep_research/research_engine.py` — 研究主循环
- `local_deep_research/search/` — 各来源搜索适配器
- `local_deep_research/report_generator.py` — 报告合成

## 可复用方案

- **多搜索源路由策略**: 按查询类型自动选择最优来源，显著提升专业领域检索质量。
- **SimpleQA 高准确率验证**: 证明本地模型 + 迭代搜索可以达到接近 SOTA 的事实准确率。

## 局限与注意点

- AGPL-3.0 许可，商用需注意 copyleft 传染性。
- 本地模型质量直接影响研究质量；使用小模型时效果下降明显。
- 搜索来源较多，首次配置成本略高（各来源可能需要 API Key）。
