# Hooks 开发指南

Claude Code Hooks 是在 Agent 生命周期事件中自动执行的命令。本文档覆盖 hook 开发的核心知识。

## 配置层级

Hooks 可配置在三层 settings 中，优先级从高到低：

| 层级 | 文件 | 作用域 | 共享 |
|------|------|--------|------|
| Local | `.claude/settings.local.json` | 当前项目、仅自己 | 否（gitignore） |
| Project | `.claude/settings.json` | 当前项目、所有协作者 | 是（提交到 git） |
| User | `~/.claude/settings.json` | 所有项目、仅自己 | 否 |

同一事件的 hooks 在多层都有定义时，**更具体的层级优先**。

## 生命周期事件

常用事件：

| 事件 | 触发时机 | stdout 行为 |
|------|----------|-------------|
| `SessionStart` | 会话开始 | 注入 Claude 上下文 |
| `UserPromptSubmit` | 用户发送消息前 | 注入 Claude 上下文 |
| `PreToolUse` | 工具调用前 | 仅 verbose 可见 |
| `PostToolUse` | 工具调用后 | 仅 verbose 可见 |
| `PostCompact` | 上下文压缩后 | 仅 verbose 可见 |
| `Stop` | Agent 完成响应 | 仅 verbose 可见 |

关键区别：**只有 `SessionStart` 和 `UserPromptSubmit` 的 stdout 会自动注入 Claude 上下文**，其他事件的 stdout 仅在 verbose 模式（`Ctrl+O`）可见。

## Hook 配置格式

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo hello",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

每个 hook 条目的字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| `type` | 是 | `"command"` |
| `command` | 是 | shell 命令，支持 `$PWD` 等环境变量 |
| `timeout` | 否 | 超时毫秒数 |
| `async` | 否 | `true` 则后台执行不阻塞 |

## stdout 输出协议

Hook 的 stdout 支持两种格式：**纯文本**和 **JSON**。

### 纯文本

直接输出文本。对 `SessionStart`/`UserPromptSubmit` 事件，文本会注入 Claude 上下文；其他事件仅 verbose 可见。

### JSON 结构化输出

通过 JSON 可以精确控制输出目标：

```json
{
  "systemMessage": "用户可见的提示信息",
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "注入 Claude 上下文的内容"
  }
}
```

核心字段：

| 字段 | 适用事件 | 效果 |
|------|----------|------|
| `systemMessage` | 所有事件 | **直接显示给用户**（界面可见） |
| `additionalContext` | SessionStart, PreToolUse, PostToolUse | **注入 Claude 上下文**（模型可见） |
| `continue` | 所有事件 | `false` 时终止 Agent |
| `stopReason` | 所有事件 | `continue: false` 时显示给用户的原因 |
| `suppressOutput` | 所有事件 | `true` 时隐藏 verbose 输出 |

### 输出目标速查

| 我想... | 怎么做 |
|---------|--------|
| 给用户看一行提示 | `{"systemMessage": "..."}` |
| 给 Claude 注入上下文 | `{"hookSpecificOutput": {"hookEventName": "...", "additionalContext": "..."}}` |
| 两者都要 | 同时输出 `systemMessage` + `hookSpecificOutput` |
| 什么都不需要 | 不输出或输出到 stderr |

## 设计原则

1. **按需选择输出格式。** 纯文本够用就用纯文本，需要区分用户可见/模型可见时才用 JSON。
2. **同一命令服务多场景时，用参数切换。** 如 `--hook` 标志区分人工调用和 hook 调用的输出格式。
3. **后台 hook 用 `async: true`。** 耗时操作（LLM 调用、网络请求）不应阻塞用户交互。
4. **stderr 用于调试。** 进度信息、错误日志写 stderr，不污染 stdout 的结构化输出。
5. **设置合理的 timeout。** 快速查询 5s，LLM 调用 30s，避免 hook 卡死整个会话。

## 与 Skill 的关系

Hooks 是 Claude Code 的独立机制，不依赖 Skills。但 Skill 可以通过 `hooks.json` 声明所需的 hooks，`omp install` 时自动合并到 settings.json。这是安装便利性，不是依赖关系。

## 参考

- [Claude Code Hooks 官方文档](https://code.claude.com/docs/en/hooks)
- [Claude Code Settings 官方文档](https://code.claude.com/docs/en/settings)
