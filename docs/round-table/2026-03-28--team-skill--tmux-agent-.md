# 圆桌讨论：是否需要新建 team skill 作为通用 tmux agent 编排层

- **日期**：2026-03-28
- **参与者**：DHH (codex/gpt-5.4),Linus Torvalds (pi/qwen3.5-27b) Elon Musk (codex/gpt-5.4),Dario Amodei (claude/opus)
- **轮次**：2

## 背景

## 议题

是否需要新建一个名为 `team` 的 skill，作为通用 tmux agent 编排层？

## 背景

### 现状
- 项目 oh-my-superpowers 是一个 Pi Agent + Skills 开发套件
- 已有 round-table skill，通过 tmux 并行启动多个 AI runtime（claude/codex/pi）进行圆桌讨论
- round-table 的 spawn.sh 已实现 tmux session 创建、并行启动、输出收集
- 但 round-table 仅限"讨论"场景，无法用于编码协作

### 需求
- 用户想要一个通用编排层：Claude 做 design/plan → Codex 编码 → Claude review → Pi 测试
- 模式：one-shot（一个 prompt 一个结果）、no-session（不保留会话历史）、YOLO（不需要 permission 确认）
- 编排者始终是当前 Claude Code session
- 通信方向：单向（orchestrator → worker → 结果）
- 多轮交互是编排者的职责，不是 skill 的职责

### 已调研的开源方案
- codex-orchestrator：仅支持 Codex，TypeScript/Bun，不支持 no-session
- turbomux：支持多 runtime，Go，882 行，但无完成检测，无输出清洗

### 约束
- 必须遵循 omp skill 规范（SKILL.md + scripts/ + references/）
- CLI 入口为 omp-team
- 脚本必须 CLI 化，Bash 实现
- 与 round-table 是独立 skill，不互相依赖

## 讨论记录

### Round 1

- 【Elon Musk】【行动标签】：` 压缩为一句话
- 【Dario Amodei】【质疑】：方向正确，但 YOLO 无监督执行需要内建安全边界，单向通信不够，完成检测是必须先解的地基问题——先解决这三个架构约束，再写第一行代码。
- 【Linus Torvalds】【质疑】：先证明这个编排模式在三个独立场景中稳定出现，再谈要不要封装成 skill；否则就是过早抽象。
- 【DHH】【行动标签】：` 压缩为一句话
- **【用户】**：用户已确认以下决策：

1. **硬需求确认**：不需要讨论场景验证，用户已有大量实践，需求成立
2. **独立 skill 确认**：面向 AI agent 的需求，skill 是最佳解决方案
3. **单向通信确认**：one-shot 场景不需要双向，worker 的问题放在输出中
4. **tmux 标准化**：在 team skill 中建立标准化封装

用户补充的架构要求：
- scripts/CLI：team 的执行快捷键（spawn/wait/collect 等原子操作）
- SKILL.md：聚焦编排，形成编排层 SOP
- references/：场景化编排 SOP，针对经典编排模式（开发场景、round-table 等）提供详细 SOP
- CLI 要支持以文件形式提供 Prompt（`--prompt-file`），应对复杂场景

### Round 2

- 【Elon Musk】【行动标签】：` 压缩为一句话
- 【Dario Amodei】【综合】：架构约束已经消除了大部分安全顾虑，但完成检测（超时+退出码+文件存在性）和输出清洗是不可省略的最小安全基线——十几行 bash 的事，不是过度设计。
- 【Linus Torvalds】【修正】：别建通用编排层，先做三个具体场景的脚本，能复用的基础设施从 round-table 提取即可。
- 【DHH】【行动标签】：` 压缩为一句话

## 最终结论


## 未解决的开放问题

（待 orchestrator 填充）

## 行动建议

（待 orchestrator 填充）
