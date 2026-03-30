# 圆桌讨论：OMP CLI → Web 任务系统

- **日期**：2026-03-28
- **参与者**：Steve Jobs (claude/opus)、DHH (codex/gpt-5.4)、Linus Torvalds (pi/qwen3.5-27b)、Grace Hopper (pi/kimi-coding/kimi-k2-thinking)
- **轮次**：3

## 背景

将 oh-my-superpowers (OMP) 的 CLI 能力暴露为 Web 服务。OMP 已有可工作的 CLI（omp-team、omp-round-table、omp-\<skill\>），但使用门槛高。目标：降低使用难度 + 把能力变成服务。

## 讨论演进

### 第 1 轮：方向验证

**引导问题：** 把 CLI 包装成 Web 服务这个方向对不对？

- **Steve Jobs**（陈述）：不要做 CLI 的 Web 壳。从用户意图出发构建任务引擎，CLI 和 Web 都是前端。UI 不暴露 Agent/Skill/Runtime 等技术概念。延迟是生死线，流式输出必须。
- **Linus Torvalds**（质疑）："降低使用难度"和"变成服务"是两码事。正确路径：CLI → HTTP API → Optional UI。先暴露 /run、/status、/logs 三个 endpoint。进程管理别造轮子，实时日志用 SSE。
- **DHH**（质疑）：不要前后端分离。做单体任务应用——一个仓库、一个部署单元、一个数据库。把能力收敛成类型化任务，用 SSE 推事件，SQLite/Postgres 存全过程。
- **Grace Hopper**（综合）：先定义任务接口协议（自描述 JSON schema），再谈实现。协议语言无关、事件 schema 标准化。24h 内让非程序员跑通第一个任务。

**共识：** 不做 CLI 的 Web 壳，"任务"是核心抽象，SSE > WebSocket。
**分歧：** 实现起点——协议先行 vs API 先行 vs 单体先行 vs 体验先行。

### 第 2 轮：如何暴露 CLI 能力而不重写

**用户追问：** 如何把现有能力暴露出去？不想重写。异步执行 omp 命令是否就是答案？

- **Linus**（陈述）：是的，就是异步执行。subprocess.Popen() 跑 CLI，文件系统存状态，tail 推日志。唯一要改的：给 CLI 加 --json-output flag。
- **DHH**（补充）：CLI 是你最稳定的边界，不要重写。单体后端做一层薄适配——参数校验、日志采集、流式输出、结果落盘。异步执行是手段，不是架构。
- **Jobs**（质疑）：异步执行 CLI 是实现细节，不是答案。但底层 fork subprocess 无所谓——关键是暴露给用户的不应该是 CLI 参数。
- **Hopper**（质疑）：异步执行可作为临时脚手架。先定义"意图→能力"映射，CLI 和 Web 共享同一种协议。

**共识合拢：** CLI 不需要重写，后端异步调用 omp 命令是可行路径。分歧只剩"包多厚"。

### 第 3 轮：MVP 边界

**用户修正：**
1. chatbot 不是需求，不需要实时对话
2. 核心定位是任务系统——用户发布任务，agent 执行，可观测进度、可终止
3. 单/多 agent 统一为单 agent 模型：team = agent + team skill

- **Linus**（综合）：Task = {id, status, output_file} + 4 态状态机 (PENDING→RUNNING→DONE|FAILED) + fork-exec CLI。100 行代码跑通 MVP。
- **DHH**（综合）：围绕"任务"的 Majestic Monolith。界面三件事：新建任务、查看运行中、查看已完成。创建时选"单人处理"或"团队讨论"，背后映射到 omp 命令。一人可读、一机可跑、一周可成。
- **Jobs**（综合）：MVP 三个屏幕——输入屏 + 执行屏（进度叙事，不是日志流）+ 结果屏。Web 层全部价值在于把机器日志翻译成人话。
- **Hopper**（综合）：先标准化任务描述格式（任务卡片 JSON），再让 CLI 和 Web 各取所需。

## 最终结论

### 全员共识

| 维度 | 结论 |
|------|------|
| 产品定位 | **任务系统**，非 chatbot |
| 统一模型 | 单 agent 执行任务；team = agent + team skill |
| 后端核心 | 异步 fork-exec `omp-*` CLI，**不重写** |
| 架构 | **单体应用**，不做前后端分离 |
| 实时通信 | **SSE** 单向推送 |
| MVP 范围 | 新建任务 / 查看进度 / 查看结果 |
| 状态机 | PENDING → RUNNING → DONE \| FAILED |

### 架构共识

```
┌─────────────┐     POST /tasks      ┌──────────────────┐
│   Web UI    │ ──────────────────→  │   单体后端        │
│  3 个视图    │ ←── SSE /stream ──  │                  │
│ 新建/进度/结果│                     │  Task Model      │
└─────────────┘                     │  ├─ id, status   │
                                    │  ├─ prompt       │
                                    │  └─ output       │
                                    │                  │
                                    │  Adapter 层      │
                                    │  fork-exec omp-* │
                                    │  stdout → SSE    │
                                    └──────────────────┘
```

### 关键设计原则

1. **CLI 是稳定边界** — 不重写，用 adapter 包住
2. **任务是一等公民** — 所有操作围绕 Task CRUD
3. **进度叙事 > 日志转发** — Web 的价值是把机器输出翻译成人话 (Jobs)
4. **一人可读、一机可跑、一周可成** (DHH)
5. **协议从使用中生长** — 不预先设计宇宙级协议

## 未解决的开放问题

1. **存储选择**：文件系统 (Linus) vs 数据库 (DHH) — 不影响 MVP，可后续迁移
2. **任务卡片标准化**：Hopper 主张的 JSON schema 标准——何时定义？MVP 后还是之前？
3. **进度叙事层**：Jobs 主张把日志翻译成人话——翻译逻辑放哪里？前端还是后端？
4. **技术栈选型**：尚未确定具体框架（Python FastAPI / Go / Rails / Node）
5. **安全性**：用户输入到 CLI 参数的注入防护（Linus 提醒：用列表传参，别用 shell=True）

## 行动建议

1. **选定技术栈**，发起 brainstorming 做具体设计
2. **24h MVP**：一个 Python 文件 + SQLite，能提交任务、看 SSE 流、查结果
3. **CLI 侧**：考虑给 omp-team 加 `--json-output` 支持结构化输出
4. **验证假设**：让一个非 CLI 用户试用，观察他卡在哪里
