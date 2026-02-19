# Alibaba-NLP/DeepResearch 深度研究实现分析

## 项目定位
偏“研究级/评测级”深度研究系统，围绕 ReAct + 多工具 + 长轨迹推理构建，强调 benchmark 表现。

## 架构分层
- ReAct Agent：多轮思考与工具调用主循环。
- 工具层：`search`、`visit`、`google_scholar`、`PythonInterpreter`、`parse_file`。
- 推理执行层：并发 rollout、数据切分、批量评测。

## Deep Research 实现思路
- 主循环中模型输出 `<tool_call>` 与 `<answer>` 标记。
- 工具执行结果回写为 `<tool_response>`，驱动下一轮思考。
- 通过 token/轮数/超时三重约束控制长链条任务。
- 在评测脚本中支持多 worker 并行，适配 GAIA 等数据集。

## 关键实现文件
- `github_cache/deep_research_repos/DeepResearch/inference/react_agent.py`
- `github_cache/deep_research_repos/DeepResearch/inference/tool_search.py`
- `github_cache/deep_research_repos/DeepResearch/inference/tool_visit.py`
- `github_cache/deep_research_repos/DeepResearch/inference/run_multi_react.py`

## 可复用方案
- ReAct 循环实现完整，适合做高强度工具调用场景。
- 评测/推理分离，便于持续优化策略。

## 局限与注意点
- 工程复杂度和部署门槛较高。
- 多外部依赖（搜索、抓取、模型服务）对环境要求高。
