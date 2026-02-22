# metaswarm 研究报告

## 1. 项目定位

`metaswarm` 是一套以 Claude Code 为核心的多代理编排方法论与技能体系，强调：
- 阶段化流程
- 质量门禁
- 对抗式评审
- 外部工具（Codex/Gemini）委托

它更像“流程操作系统”，不是低层消息中间件。

## 2. 关键机制证据

### 2.1 双模式协调（Task Mode / Team Mode）
- `guides/agent-coordination.md:11` 若有 `TeamCreate`/`SendMessage` 用 Team Mode
- `guides/agent-coordination.md:55` Task Mode：fire-and-forget 子任务
- `guides/agent-coordination.md:83` Team Mode：持久 teammate + 直接消息
- `guides/agent-coordination.md:91` 支持代理间直接通信

结论：明确抽象了“主从编排”与“持久团队协作”两种模式。

### 2.2 关键不变量（保障收敛质量）
- `guides/agent-coordination.md:176` 对抗评审必须 fresh Task
- `guides/agent-coordination.md:205` 模式无关不变量（验证、门禁、升级）

结论：把“如何讨论”提升为“如何保证结论可靠”。

### 2.3 外部 CLI 工具适配层
- `skills/external-tools/SKILL.md:103` routing/dispatch 阶段化说明
- `skills/external-tools/SKILL.md:125` IMPLEMENT 可委托外部工具
- `skills/external-tools/SKILL.md:149` 跨模型对抗评审
- `skills/external-tools/adapters/codex.sh:31` health 检查
- `skills/external-tools/adapters/codex.sh:77` implement
- `skills/external-tools/adapters/codex.sh:230` review

结论：通过 shell adapter 统一了“不同 CLI 能力”的接入方式。

## 3. 与目标场景的契合点

1. 提供了“群组讨论之外”的关键能力：收敛机制
2. 提供外部 CLI 委托范式，适配 Codex 非常自然
3. 对临时团队生命周期有明确协议（create/join/shutdown/delete）

## 4. 不足与风险

1. 该项目强依赖 BEADS、流程和规范，落地成本高
2. Team Mode 依赖特定工具能力，不是通用基础设施
3. 更偏“任务交付编排”，不是纯讨论体验优化

## 5. 可借鉴路线（对 skill 实现）

从 metaswarm 借鉴“轻协议”，而非整套系统：
- Mode 检测：有群组能力就 Team Mode，否则退化为 Task Mode
- 不变量：每轮讨论后主控独立验证、最终总结时给证据
- 升级策略：超过轮次未收敛即触发 human checkpoint

对 `skills/vibe-coding-discussion/` 的启发：
- 讨论机制要和“收敛规则”一起设计，不能只做消息转发
