# Trigger Cases

用于验证 `deep-research` 的触发边界。

目录约定：
- `should-trigger/`：应该触发 deep-research 的请求
- `should-not-trigger/`：不应该触发的请求

评估目标：
- 多轮系统研究请求应触发
- 单页总结、一次性事实查询、临时搜索不应触发
