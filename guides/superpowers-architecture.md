# Superpowers 项目架构分析

来源：`github_cache/superpowers`，版本 4.3.0，作者 Jesse Vincent

---

## 一、项目目录结构

```
superpowers/
├── .claude-plugin/            # Claude Code 插件声明
│   ├── plugin.json            # 插件元数据（名称/版本/作者）
│   └── marketplace.json       # 插件市场配置
├── .cursor-plugin/            # Cursor 插件声明
│   └── plugin.json            # 含 skills/agents/commands/hooks 路径映射
├── .opencode/                 # OpenCode 平台适配
│   ├── INSTALL.md
│   └── plugins/superpowers.js # 系统提示注入插件（JS）
├── .codex/                    # Codex 平台适配
│   └── INSTALL.md
├── skills/                    # 14 个 Skills（每个子目录含 SKILL.md）
├── agents/                    # 代理定义（code-reviewer.md）
├── commands/                  # 斜杠命令（brainstorm / write-plan / execute-plan）
├── hooks/
│   ├── hooks.json             # 注册 SessionStart 钩子
│   └── session-start.sh       # 注入 using-superpowers 引导程序
└── lib/skills-core.js         # 技能发现/路径解析工具（供 OpenCode 用）
```

---

## 二、多平台适配策略

| 平台 | 发现机制 | 安装方式 | 适配文件 |
|------|---------|---------|---------|
| Claude Code | 内置插件市场 | `/plugin install` | `.claude-plugin/` |
| Cursor | 内置插件市场 | `/plugin-add` | `.cursor-plugin/` |
| OpenCode | 手动符号链接 + JS 插件 | git clone + symlink | `.opencode/` |
| Codex | 手动符号链接 | git clone + symlink | `.codex/` |

核心逻辑相同（skills/agents/commands/hooks），不同平台只需不同的声明文件适配发现机制。

---

## 三、Claude Code 安装后的文件分布

`.cursor-plugin/plugin.json` 声明了以下路径映射（Claude Code plugin.json 同理）：

```json
{
  "skills":   "./skills/",
  "agents":   "./agents/",
  "commands": "./commands/",
  "hooks":    "./hooks/hooks.json"
}
```

| 资产类型 | 数量 | 注册方式 |
|---------|------|---------|
| Skills | 14 个 | 平台扫描 `skills/*/SKILL.md`，注册 name + description |
| Agents | 1 个 | `agents/code-reviewer.md`，通过 `Task` 工具的 `subagent_type` 调用 |
| Commands | 3 个 | `/brainstorm` `/write-plan` `/execute-plan` |
| Hooks | 1 个 | SessionStart → `session-start.sh` |

---

## 四、引导程序机制（核心架构）

### 工作原理

```
安装时     → 平台注册 14 个 skills 的 name+description（不加载内容）
会话启动时  → SessionStart hook 注入 using-superpowers 全文到 system prompt
运行时     → LLM 收到消息 → 检查 skill 列表 → Skill 工具按需加载具体内容
```

本质是**懒加载 + 行为塑造**：引导程序不包含任何具体 skill 内容，只负责改变 LLM 的决策习惯。

### session-start.sh 做了什么

```bash
# 读取 using-superpowers/SKILL.md 全文
# 注入到两个字段（兼容 Claude + Cursor）：
{
  "additional_context": "...",
  "hookSpecificOutput": {
    "additionalContext": "..."
  }
}
```

---

## 五、using-superpowers 引导程序解析（96行）

### 各模块职责

| 模块 | 行数 | 作用 |
|------|------|------|
| 绝对命令 + 1% 阈值 | ~7 行 | 强制 LLM 每次都检查 skill 列表 |
| 决策流程图（DOT 语法） | ~28 行 | 定义何时、如何加载 skill |
| Red Flags 反规避表 | ~17 行 | 封堵 LLM 跳过 skill 的 12 种借口 |
| 优先级/分类规则 | ~20 行 | 解决多 skill 冲突、刚性/柔性区分 |

### 关键设计决策

**1. 绝对命令**（`<EXTREMELY-IMPORTANT>` 标签）

```
IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.
```

- 使用 `<EXTREMELY-IMPORTANT>` 是对 Claude 系列有效的权重提升标记
- 1% 阈值：不是"确定相关才用"，而是"有一点可能就必须检查"
- 剥夺 LLM 的自主判断权，消除跳过 skill 的可能性

**2. DOT 流程图的两条路径**

```dot
路径A：收到消息 → 检查 skill → 有则加载 → 无则直接回复
路径B：准备进入计划模式 → 检查是否已 brainstorm → 没有则先 brainstorm
```

路径 B 是特殊拦截：把 `brainstorming` 硬编码为计划前的强制前置步骤。

**3. Red Flags 反规避表**

预判 LLM 跳过 skill 的所有借口，逐一封堵：

| 规避类型 | 封堵方式 |
|---------|---------|
| 时序规避（"先做X再查"） | "查 skill 在一切之前" |
| 复杂度规避（"太简单了"） | "简单的事也会变复杂" |
| 缓存规避（"我记得这个"） | "Skills 会更新，必须重新读" |
| 效率规避（"这样更快"） | "无纪律的行动浪费时间" |

**4. 职责分离**

- **平台**：注册 14 个 skills 的 name + description（LLM 在 system prompt 可见）
- **引导程序**：只改变 LLM 的决策习惯（"做事前先查列表"）
- **匹配逻辑**：交给 LLM 自己——LLM 天然擅长将用户意图和 description 做语义匹配

---

## 六、可复用的设计模式

### 模式 1：SessionStart Hook 作为引导程序注入点

适用场景：有一套需要在每次会话都激活的行为规范。

```json
// hooks/hooks.json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup|resume|clear|compact",
      "hooks": [{ "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh" }]
    }]
  }
}
```

### 模式 2：Command 作为 Skill 的轻量入口

Command 文件内容只有一行，把斜杠命令映射到对应 skill：

```markdown
---
description: "..."
disable-model-invocation: true
---

Invoke the superpowers:brainstorming skill and follow it exactly as presented to you
```

### 模式 3：YAML frontmatter 的 description 决定触发时机

description 不是写给人看的说明，是写给 LLM 做语义匹配的触发条件。越精确的 description，触发命中率越高。

### 模式 4：Skill 内嵌辅助文档（按需加载）

`systematic-debugging` skill 包含多个辅助文档：

```
skills/systematic-debugging/
  SKILL.md                      # 主流程
  root-cause-tracing.md         # 按需加载
  defense-in-depth.md           # 按需加载
  condition-based-waiting.md    # 按需加载
  find-polluter.sh              # 可执行脚本
```

主 SKILL.md 只引用这些文件的路径，LLM 需要时再读取，避免一次性塞入过多内容。

---

## 七、14 个 Skills 一览

| Skill | 触发场景 |
|-------|---------|
| `using-superpowers` | 每次会话启动（由 hook 注入） |
| `brainstorming` | 任何创造性工作之前 |
| `writing-plans` | 有规范/需求的多步任务 |
| `executing-plans` | 有计划需要执行（带检查点） |
| `subagent-driven-development` | 执行计划的子代理模式 |
| `test-driven-development` | 实现功能/修复 bug |
| `systematic-debugging` | 遇到 bug/测试失败 |
| `dispatching-parallel-agents` | 2+ 个独立任务 |
| `requesting-code-review` | 完成任务后 |
| `receiving-code-review` | 收到评审反馈 |
| `using-git-worktrees` | 需要隔离工作区 |
| `finishing-a-development-branch` | 实现完成后 |
| `verification-before-completion` | 声称完成之前 |
| `writing-skills` | 创建/编辑 skill |
