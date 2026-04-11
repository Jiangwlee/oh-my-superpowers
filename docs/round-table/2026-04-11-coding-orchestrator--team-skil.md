# 圆桌讨论：coding-orchestrator 是否应合并到 team skill

- **日期**：2026-04-11
- **参与者**：DHH (codex/gpt-5.4),Linus Torvalds (pi/litellm-local/gemma4) Alan Kay (claude/sonnet),Elon Musk (codex/gpt-5.4)
- **轮次**：3

## 背景

# 讨论背景

**议题**：coding-orchestrator 是否应合并到 team skill

# 议题：coding-orchestrator 是否应合并到 team skill

## 背景

oh-my-superpowers 项目有两个相关 skill：

### team skill
- 核心能力：`omp team run <runtime> "<prompt>"` 派遣任务到 claude/codex/pi
- 已有 `code-and-review.md` 场景文档 + `code-review.md` prompt 模板
- 并行：shell `&` + git worktree + `--cwd`
- 无持久化状态，orchestrator 在 context 中跟踪

### coding-orchestrator skill
- 核心定位：不写代码，只编排 sub agent
- 有重量级 task spec 体系：story → task-NN → deviation rules → must-haves → acceptance
- 有 Compaction Recovery：handoff 机制应对长任务 context 压缩
- Review 机制：写了 `Agent(subagent_type: "codex")`，但该 subagent_type 在 Claude Code 中不存在
- 并行：依赖 Agent 的 `isolation: "worktree"`

## 核心矛盾

1. **Review 机制断裂**：coding-orchestrator 依赖不存在的 `Agent(subagent_type: "codex")`，而 team 已有可用的 `omp team run claude --prompt-file review.md`
2. **两套并行方案**：team 用 shell `&` + worktree，coding-orchestrator 用 Agent isolation，重复且不兼容
3. **能力重叠**：team 的 code-and-review 场景已覆盖"codex 编码 → claude 审查"的 pipeline

## coding-orchestrator 的独有价值

1. **task spec 模板体系**：story/task 分解、deviation rules、must-haves acceptance —— 比 team 的 prompt 模板更结构化
2. **compaction recovery**：handoff-context 文件在 context 压缩后恢复状态
3. **worker-guideline**：sub agent 行为协议（analysis paralysis guard、fix attempt limit、deviation handling）
4. **constitution.md**：全局编码准则（Karpathy 四原则）

## 待讨论问题

- coding-orchestrator 作为独立 skill 是否有存在必要？
- 如果合并，task spec 体系和 handoff 机制如何融入 team？
- 如果保留，如何修复 Review 机制（改用 team 还是其他方案）？
- worker-guideline 和 constitution 这类通用编码准则应该归属哪里？

## 讨论记录

### Round 1

- 【Elon Musk】【行动标签】：` 压缩为一句话
- 【Linus Torvalds】【质疑】：不要把特定领域的复杂逻辑强行塞进通用编排器，否则你会亲手制造出一个不可维护的烂摊子。
- 【Alan Kay】【质疑】：先看消息协议，再谈边界——接口不同则分，接口重叠则合，不要靠直觉。
- 【DHH】【行动标签】：` 压缩为一句话
- **【主持人】【补充】**：要求所有参与者先阅读两个 skill 的实际文件，再基于事实讨论

### Round 2

- 【Alan Kay】【陈述】：接口不同、层次不同，合并是降维，不是简化。
- 【Elon Musk】【行动标签】：` 压缩为一句话
- 【Linus Torvalds】【反驳】：不要把业务逻辑和底层原语混为一谈，保持 `team` 的通用性，让 `orchestrator` 作为一个基于 `team` 的高级应用层存在。
- 【DHH】【行动标签】：` 压缩为一句话
- **【用户】**：用户补充两个观点：

1. 核心在于 team skill 是否是无状态编排协议。如果它是无状态编排协议，最好不要合并。否则每加一个新场景，team skill 就膨胀一次。team skill 目前的主要问题还是协议不清晰。

2. coding-orchestrator 应该依赖于 team CLI（omp team run），或者更激进一些——不依赖 team，直接把 tmux 命令写入 coding-orchestrator skill，明确告诉 LLM 如何调用第三方工具。这样就完全和 team 解耦了。

请各位基于用户的这两个观点发表最终看法：
- 你支持哪个方案？（依赖 team CLI vs 直接写 tmux 命令）
- team skill 的协议边界应该是什么？

### Round 3

- 【DHH】【陈述】：` 压缩为一句话
- 【Elon Musk】【陈述】：` 压缩为一句话
- 【Alan Kay】【综合】：层次清晰比代码复用更重要——`team` 是协议，`orchestrator` 是应用，两者的稳定性周期根本不同，不该耦合。
- 【Linus Torvalds】【补充】：保持 `team` 作为底层通信原语的纯粹性，通过 tmux 命令解耦业务编排才是对架构的尊重。

## 最终结论


## 未解决的开放问题

（待 orchestrator 填充）

## 行动建议

（待 orchestrator 填充）
