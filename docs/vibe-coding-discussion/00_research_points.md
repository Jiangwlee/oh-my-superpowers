# Vibe Coding Discussion 研究点定义

## 背景与目标

目标是以 `skills/vibe-coding-discussion/` 的方式实现一个简化版临时群组讨论机制：
- 主控 Agent（Claude）可拉起 Codex 与 OpenCode（或其他 CLI Agent）
- 讨论期间多方上下文可见、顺序发言、可控收敛
- 讨论结束后可总结并优雅关闭临时参与者

本阶段只做 research，不做实现。

## 研究点

1. 会话拓扑与关系模型
- 是否支持“中心化主控 + 可见群聊”
- 是否支持真正对等群组，或仅支持主从编排
- 子代理之间能否直接通信

2. Agent 拉起与生命周期管理
- 如何启动不同 CLI Agent（claude/codex/gemini/opencode）
- 会话是否可复用（持久 session）
- 是否支持 pause/resume/shutdown 与回收

3. 消息总线与上下文可见性
- 消息是否具备统一结构（sender/receiver/type/timestamp）
- 是否有“房间/线程/会话”概念
- 是否支持历史查询、过滤、归档

4. 并行与调度机制
- 是否支持并行子任务
- 并行结果如何聚合
- 是否有顺序发言/轮次控制基础设施

5. 任务与收敛机制
- 是否支持任务拆解、状态流转、Done 判定
- 是否有 review gate / adversarial review / escalation 等收敛机制

6. 共享工作区与工件沉淀
- 是否支持共享目录/文件同步/变更广播
- 是否支持结构化 artifacts（spec/plan/review）沉淀

7. 可观测性与可追溯
- 是否能查看会话状态、消息历史、成员状态
- 是否可保留审计记录

8. 安全与边界
- 执行权限（是否 bypass sandbox）
- 文件访问边界控制
- 超时、失败重试、降级策略

## 输出模板（每个候选项目）

每个项目统一输出：
- 项目定位
- 关键机制证据（文件+行号）
- 与目标场景的契合点
- 不足与风险
- 可借鉴技术路线（面向 skill 级实现）

## 当前样本范围

- `devchain`（已完成）
- `Claude-Code-Workflow`
- `metaswarm`
- `claude-symphony-of-one-mcp`
- `codex-as-mcp`
