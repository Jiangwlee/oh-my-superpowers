# 圆桌讨论：CLI 架构拆分：omp/omp-tool/omp-agent 三命令 vs 统一 omp vs 当前 omp+omp-xxx 散装模式

- **日期**：2026-04-07
- **参与者**：Linus Torvalds (pi/github-copilot/gpt-4.1),DHH (codex/gpt-5.4) Grace Hopper (pi/qwen3.5-27b)
- **轮次**：3

## 背景

# 讨论背景

**议题**：CLI 架构拆分：omp/omp-tool/omp-agent 三命令 vs 统一 omp vs 当前 omp+omp-xxx 散装模式

## 背景

oh-my-superpowers 是一个 Pi Agent + Skills 开发套件。当前架构：

### 现状问题
1. scripts 散落在各 skill 目录中（skills/<name>/scripts/），而 CLI 入口在 bin/omp-<name>
2. Skill 把菜谱（SKILL.md）和工具（scripts/）打包在一起，工具可能被其他 skill 依赖，形成错误的横向依赖
3. SKILL.md 从不直接调用 scripts，只通过命令名引用（路径耦合）

### 已决定
- 将 scripts 从 skill 中提取到独立的 tools/ 目录，按功能域组织
- Skill 回归纯 SOP（只有 SKILL.md + references/）

### 待讨论：CLI 入口设计
用户倾向方案 C（三个命令）：
- omp: 项目管理（install/remove/list/test）
- omp-tool: 调用 tool
- omp-agent: 运行 agent

其他方案供参考：
- 方案 A: bin/omp-xxx 直接链接到 tools/（改动最小）
- 方案 B: 统一 omp subcommand（单入口，类似 git）

### 设计约束
- 用户是 LLM agent（主要调用者）和人类开发者
- 安装后 CLI 在 ~/.local/bin/，tools 在 ~/.oh-my-superpowers/tools/
- 已有 omp run <agent-name> 用于运行 agent

## 讨论记录

### Round 1

- 【Grace Hopper】【质疑】：CLI 设计的目标应该是"用户忘记命令的存在"，而不是"命令命名符合架构师的审美"。
- 【Linus Torvalds】【质疑】：命令分类不能代替清晰的实现，别让分命令结构沦为伪分层。
- 【DHH】【行动标签】：` 压缩为一句话
- **【主持人】【综合】**：三位一致反对拆分，追问：LLM 作为主要调用者时设计逻辑是否不同？

### Round 2

- 【Grace Hopper】【补充】：CLI 架构讨论应该转向"工具元数据标准化"和"LLM 发现协议"，而非命令命名美学。
- 【Linus Torvalds】【质疑】：CLI 设计首先要结构清晰，LLM 只是新用户，不能用来粉饰命令混乱。
- 【DHH】【质疑】：` 压缩为一句话
- **【主持人】【综合】**：用户补充：SKILL.md=SOP，--help=一等公民API。追问 tool 自描述边界。
- **【用户】**：【用户】【指令】：继续。共识已收敛到"一个 CLI + 自动推断"。现在需要落地到具体规则。

### Round 3

- 【DHH】【补充】：` 压缩为一句话
- 【Grace Hopper】【质疑】：停止争论命令命名，先定义工具元数据标准，否则 --help 永远成不了一等公民 API。
- 【Linus Torvalds】【质疑】：没有自动化绑定和实际约束，所谓元数据标准就是纸面协议，没解决实际混乱。
- **【主持人】【综合】**：暂停圆桌，启动 deep research 调研工具元数据协议
- **【主持人】【综合】**：最终决议：7项全部敲定，落地为CLI开发规范+checklist

## 最终结论

**简言之**：务实路线——用规范和 checklist 约束质量，不搞元数据协议。

## 未解决的开放问题

（待 orchestrator 填充）

## 行动建议

（待 orchestrator 填充）
