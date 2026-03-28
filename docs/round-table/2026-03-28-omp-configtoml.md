# 圆桌讨论：omp 是否需要中心化配置文件（config.toml）来统一默认模型？

- **日期**：2026-03-28
- **参与者**：DHH (codex/gpt-5.4),Linus Torvalds (pi/qwen3.5-27b) Elon Musk (codex/gpt-5.4),Dario Amodei (claude/opus)
- **轮次**：2

## 背景

# 讨论背景

**议题**：omp 是否需要中心化配置文件（config.toml）来统一默认模型？

## 背景

omp（oh-my-superpowers）是一个 Agent + Skills 开发套件。当前各组件的默认模型散落在多处：
- bin/omp 硬编码 litellm-local/qwen3.5-27b 作为 pi runtime fallback
- agents/agents.json 每个 agent 各自写死模型
- skills/insight 硬编码 sonnet 作为 LLM 调用默认模型
- skills/round-table 每角色指定模型（persona 属性）
- skills/team 不指定模型，由调用方传入

## 提议方案
创建 $OMP_HOME/config.toml，按 runtime 定义默认模型：
```toml
[models]
pi = "litellm-local/qwen3.5-27b"
codex = "gpt-5.4"
claude = "sonnet"
```

各组件统一读取这个配置，优先级：命令行 --model > agents.json > config.toml > 硬编码 fallback。

## 核心争议
1. 这是否会把各个 skill/agent 与 omp 框架绑死？目前 skill 规范要求「每个 skill 独立自治」
2. 现在是否已经绑死了？（skills 已经通过 $OMP_HOME 引用路径、通过 omp-xxx CLI 入口暴露）
3. 如果不做中心化配置，有没有更好的方式统一默认模型？
4. 配置文件的粒度：按 runtime 分够不够？是否需要更细（如 per-skill、per-agent）？

请各位从自己的视角出发，讨论这个架构决策。

## 讨论记录

### Round 1

- 【Elon Musk】【行动标签】：` 压缩为一句话
- 【Dario Amodei】【陈述】：现状是无治理的隐性耦合，config.toml 把它变成有治理的显式约定——这不是增加耦合，是把已有耦合从暗处搬到明处，加上渐进式控制和静默降级。
- 【Linus Torvalds】【质疑】：中心化配置文件是懒惰的设计——它把"必须明确的选择"推迟到运行时，然后假装问题解决了。
- 【DHH】【行动标签】：` 压缩为一句话

### Round 2

- 【Elon Musk】【行动标签】：` 压缩为一句话
- 【Dario Amodei】【反驳】：config.toml 通过环境变量注入而非代码 import，让 skill 零感知地获得统一默认值——这是基础设施层约束，不是应用层耦合。
- 【Linus Torvalds】【反驳】：config.toml 掩盖的是技能边界不清的问题，应该让技能彻底无状态，把默认值决策推到框架层或命令行。
- 【DHH】【行动标签】：` 压缩为一句话

## 最终结论


## 未解决的开放问题

（待 orchestrator 填充）

## 行动建议

（待 orchestrator 填充）
