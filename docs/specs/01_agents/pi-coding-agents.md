# Pi简介

Pi是一套极简的Agent框架，支持`skills`, `prompts`和`tools`注入。Pi会自动加载`~/.agents/skills`中定义的Skill，用户也可以通过`--skill`来添加任意路径的`skill`.Pi遵从标准的`skill`规范，与`claude code`的`skill`规范兼容。因此，只要创建创建一个Prompt Markdown文件，指定skills（系统skills不用显式指定，会默认加载），指定tools（默认不用指定，会自动加载默认tools），就可以通过`pi`命令将它们串联成一个`Pi Agent`。将`Pi Agent`封装成cli，就可以创建一个command来调用Agent。

Pi可以通过命令行指定Agent使用的模型，比如：litellm-local/qwen3.5-27b, openai-codex/gpt-5.4
作成Agent cli后，一般使用非交互模式，如果想看到实时流式输出，需要使用`--mode json`，比如：pi --mode json --model litellm-local/qwen3.5-27b -p "你有哪些技能？"

为了更好看，可能需要用`jq`再处理，以下是部分输出示例：
```json
{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"根据项目上下文，我当前有以下可用技能：\n\n## 1. **chrome-cdp** \n- **位置**: `/home/bruce/.agents/skills/chrome-cdp/SKILL.md`\n- **用途**: 使用 Chrome CDP (Chrome DevTools Protocol) 在本地 Chrome 浏览器中执行操作\n- **适用场景**:\n  - 需要在工作流中使用真实 Chrome 标签页\n  - 运行预置的网站 SOP 脚本（如爬取、提取数据）\n  - 检查或调试已在 Chrome 中打开的页面\n\n## 2. **skill-review**\n- **位置**: `/home/bruce/.agents/skills/skill-review/SKILL.md`\n- **用途**: 审查、审计和改进 Agent Skill\n- **适用场景**:\n  - 审查技能目录结构\n  - 检查 SKILL.md 文件规范\n  - 审计技能引用或脚本质量\n  - 诊断技能触发问题\n  - 评估技能是否准备好部署\n\n---\n\n此外，我还可以使用基础工具：\n- `read` - 读取文件内容\n- `bash` - 执行命令行\n- `edit` - 精确编辑文件\n- `write` - 创建/覆盖文件\n- `subagent` - 调用 pi 子代理\n\n需要我加载某个技能的详细内容吗？"}],"api":"openai-completions","provider":"litellm-local","model":"qwen3.5-27b","usage":{"input":3495,"output":289,"cacheRead":0,"cacheWrite":0,"totalTokens":3784,"cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0,"total":0}},"stopReason":"stop","timestamp":1774336482851,"responseId":"chatcmpl-bBpAIMTNO0KLW4DkdFXUsqQBt6I0bLFt"}}
{"type":"turn_end","message":{"role":"assistant","content":[{"type":"text","text":"根据项目上下文，我当前有以下可用技能：\n\n## 1. **chrome-cdp** \n- **位置**: `/home/bruce/.agents/skills/chrome-cdp/SKILL.md`\n- **用途**: 使用 Chrome CDP (Chrome DevTools Protocol) 在本地 Chrome 浏览器中执行操作\n- **适用场景**:\n  - 需要在工作流中使用真实 Chrome 标签页\n  - 运行预置的网站 SOP 脚本（如爬取、提取数据）\n  - 检查或调试已在 Chrome 中打开的页面\n\n## 2. **skill-review**\n- **位置**: `/home/bruce/.agents/skills/skill-review/SKILL.md`\n- **用途**: 审查、审计和改进 Agent Skill\n- **适用场景**:\n  - 审查技能目录结构\n  - 检查 SKILL.md 文件规范\n  - 审计技能引用或脚本质量\n  - 诊断技能触发问题\n  - 评估技能是否准备好部署\n\n---\n\n此外，我还可以使用基础工具：\n- `read` - 读取文件内容\n- `bash` - 执行命令行\n- `edit` - 精确编辑文件\n- `write` - 创建/覆盖文件\n- `subagent` - 调用 pi 子代理\n\n需要我加载某个技能的详细内容吗？"}],"api":"openai-completions","provider":"litellm-local","model":"qwen3.5-27b","usage":{"input":3495,"output":289,"cacheRead":0,"cacheWrite":0,"totalTokens":3784,"cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0,"total":0}},"stopReason":"stop","timestamp":1774336482851,"responseId":"chatcmpl-bBpAIMTNO0KLW4DkdFXUsqQBt6I0bLFt"},"toolResults":[]}
{"type":"agent_end","messages":[{"role":"user","content":[{"type":"text","text":"你有哪些技能？"}],"timestamp":1774336482823},{"role":"assistant","content":[{"type":"text","text":"根据项目上下文，我当前有以下可用技能：\n\n## 1. **chrome-cdp** \n- **位置**: `/home/bruce/.agents/skills/chrome-cdp/SKILL.md`\n- **用途**: 使用 Chrome CDP (Chrome DevTools Protocol) 在本地 Chrome 浏览器中执行操作\n- **适用场景**:\n  - 需要在工作流中使用真实 Chrome 标签页\n  - 运行预置的网站 SOP 脚本（如爬取、提取数据）\n  - 检查或调试已在 Chrome 中打开的页面\n\n## 2. **skill-review**\n- **位置**: `/home/bruce/.agents/skills/skill-review/SKILL.md`\n- **用途**: 审查、审计和改进 Agent Skill\n- **适用场景**:\n  - 审查技能目录结构\n  - 检查 SKILL.md 文件规范\n  - 审计技能引用或脚本质量\n  - 诊断技能触发问题\n  - 评估技能是否准备好部署\n\n---\n\n此外，我还可以使用基础工具：\n- `read` - 读取文件内容\n- `bash` - 执行命令行\n- `edit` - 精确编辑文件\n- `write` - 创建/覆盖文件\n- `subagent` - 调用 pi 子代理\n\n需要我加载某个技能的详细内容吗？"}],"api":"openai-completions","provider":"litellm-local","model":"qwen3.5-27b","usage":{"input":3495,"output":289,"cacheRead":0,"cacheWrite":0,"totalTokens":3784,"cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0,"total":0}},"stopReason":"stop","timestamp":1774336482851,"responseId":"chatcmpl-bBpAIMTNO0KLW4DkdFXUsqQBt6I0bLFt"}]}
```

以下是pi命令：

```bash
pi --help
pi - AI coding assistant with read, bash, edit, write tools

Usage:
  pi [options] [@files...] [messages...]

Commands:
  pi install <source> [-l]     Install extension source and add to settings
  pi remove <source> [-l]      Remove extension source from settings
  pi uninstall <source> [-l]   Alias for remove
  pi update [source]           Update installed extensions (skips pinned sources)
  pi list                      List installed extensions from settings
  pi config                    Open TUI to enable/disable package resources
  pi <command> --help          Show help for install/remove/uninstall/update/list

Options:
  --provider <name>              Provider name (default: google)
  --model <pattern>              Model pattern or ID (supports "provider/id" and optional ":<thinking>")
  --api-key <key>                API key (defaults to env vars)
  --system-prompt <text>         System prompt (default: coding assistant prompt)
  --append-system-prompt <text>  Append text or file contents to the system prompt
  --mode <mode>                  Output mode: text (default), json, or rpc
  --print, -p                    Non-interactive mode: process prompt and exit
  --continue, -c                 Continue previous session
  --resume, -r                   Select a session to resume
  --session <path>               Use specific session file
  --fork <path>                  Fork specific session file or partial UUID into a new session
  --session-dir <dir>            Directory for session storage and lookup
  --no-session                   Don't save session (ephemeral)
  --models <patterns>            Comma-separated model patterns for Ctrl+P cycling
                                 Supports globs (anthropic/*, *sonnet*) and fuzzy matching
  --no-tools                     Disable all built-in tools
  --tools <tools>                Comma-separated list of tools to enable (default: read,bash,edit,write)
                                 Available: read, bash, edit, write, grep, find, ls
  --thinking <level>             Set thinking level: off, minimal, low, medium, high, xhigh
  --extension, -e <path>         Load an extension file (can be used multiple times)
  --no-extensions, -ne           Disable extension discovery (explicit -e paths still work)
  --skill <path>                 Load a skill file or directory (can be used multiple times)
  --no-skills, -ns               Disable skills discovery and loading
  --prompt-template <path>       Load a prompt template file or directory (can be used multiple times)
  --no-prompt-templates, -np     Disable prompt template discovery and loading
  --theme <path>                 Load a theme file or directory (can be used multiple times)
  --no-themes                    Disable theme discovery and loading
  --export <file>                Export session file to HTML and exit
  --list-models [search]         List available models (with optional fuzzy search)
  --verbose                      Force verbose startup (overrides quietStartup setting)
  --offline                      Disable startup network operations (same as PI_OFFLINE=1)
  --help, -h                     Show this help
  --version, -v                  Show version number

Extensions can register additional flags (e.g., --plan from plan-mode extension).

Examples:
  # Interactive mode
  pi

  # Interactive mode with initial prompt
  pi "List all .ts files in src/"

  # Include files in initial message
  pi @prompt.md @image.png "What color is the sky?"

  # Non-interactive mode (process and exit)
  pi -p "List all .ts files in src/"

  # Multiple messages (interactive)
  pi "Read package.json" "What dependencies do we have?"

  # Continue previous session
  pi --continue "What did we discuss?"

  # Use different model
  pi --provider openai --model gpt-4o-mini "Help me refactor this code"

  # Use model with provider prefix (no --provider needed)
  pi --model openai/gpt-4o "Help me refactor this code"

  # Use model with thinking level shorthand
  pi --model sonnet:high "Solve this complex problem"

  # Limit model cycling to specific models
  pi --models claude-sonnet,claude-haiku,gpt-4o

  # Limit to a specific provider with glob pattern
  pi --models "github-copilot/*"

  # Cycle models with fixed thinking levels
  pi --models sonnet:high,haiku:low

  # Start with a specific thinking level
  pi --thinking high "Solve this complex problem"

  # Read-only mode (no file modifications possible)
  pi --tools read,grep,find,ls -p "Review the code in src/"

  # Export a session file to HTML
  pi --export ~/.pi/agent/sessions/--path--/session.jsonl
  pi --export session.jsonl output.html

Environment Variables:
  ANTHROPIC_API_KEY                - Anthropic Claude API key
  ANTHROPIC_OAUTH_TOKEN            - Anthropic OAuth token (alternative to API key)
  OPENAI_API_KEY                   - OpenAI GPT API key
  AZURE_OPENAI_API_KEY             - Azure OpenAI API key
  AZURE_OPENAI_BASE_URL            - Azure OpenAI base URL (https://{resource}.openai.azure.com/openai/v1)
  AZURE_OPENAI_RESOURCE_NAME       - Azure OpenAI resource name (alternative to base URL)
  AZURE_OPENAI_API_VERSION         - Azure OpenAI API version (default: v1)
  AZURE_OPENAI_DEPLOYMENT_NAME_MAP - Azure OpenAI model=deployment map (comma-separated)
  GEMINI_API_KEY                   - Google Gemini API key
  GROQ_API_KEY                     - Groq API key
  CEREBRAS_API_KEY                 - Cerebras API key
  XAI_API_KEY                      - xAI Grok API key
  OPENROUTER_API_KEY               - OpenRouter API key
  AI_GATEWAY_API_KEY               - Vercel AI Gateway API key
  ZAI_API_KEY                      - ZAI API key
  MISTRAL_API_KEY                  - Mistral API key
  MINIMAX_API_KEY                  - MiniMax API key
  OPENCODE_API_KEY                 - OpenCode Zen/OpenCode Go API key
  KIMI_API_KEY                     - Kimi For Coding API key
  AWS_PROFILE                      - AWS profile for Amazon Bedrock
  AWS_ACCESS_KEY_ID                - AWS access key for Amazon Bedrock
  AWS_SECRET_ACCESS_KEY            - AWS secret key for Amazon Bedrock
  AWS_BEARER_TOKEN_BEDROCK         - Bedrock API key (bearer token)
  AWS_REGION                       - AWS region for Amazon Bedrock (e.g., us-east-1)
  PI_CODING_AGENT_DIR              - Session storage directory (default: ~/.pi/agent)
  PI_PACKAGE_DIR                   - Override package directory (for Nix/Guix store paths)
  PI_OFFLINE                       - Disable startup network operations when set to 1/true/yes
  PI_SHARE_VIEWER_URL              - Base URL for /share command (default: https://pi.dev/session/)
  PI_AI_ANTIGRAVITY_VERSION        - Override Antigravity User-Agent version (e.g., 1.23.0)

Available Tools (default: read, bash, edit, write):
  read   - Read file contents
  bash   - Execute bash commands
  edit   - Edit files with find/replace
  write  - Write files (creates/overwrites)
  grep   - Search file contents (read-only, off by default)
  find   - Find files by glob pattern (read-only, off by default)
  ls     - List directory contents (read-only, off by default)
```

---

# Research Report: Pi Coding Agent Subagent Development

## Overview

Pi coding agent is an open-source, minimal terminal-based AI coding harness that has emerged as a significant alternative to closed-source solutions like Claude Code. The ecosystem around pi-mono (27k+ stars) has grown rapidly, with OpenClaw (333k+ stars) being the most prominent project built on top of it. The agent supports extension development through TypeScript modules, with community-driven subagent implementations emerging as key differentiators from Pi's original minimal design philosophy.

## Google / DuckDuckGo

**Key Findings:**

1. **Pi Agent Philosophy**: Pi was designed as a minimal coding harness where developers can adapt the agent to their workflows. Unlike Claude Code, it doesn't have built-in sub-agent tools - this was an intentional design decision by creator Mario Zechner (https://mariozechner.at/posts/2025-11-30-pi-coding-agent/)

2. **Extension Architecture**: Pi uses TypeScript extensions that can:
   - Subscribe to lifecycle events
   - Register custom tools callable by the LLM via `pi.registerTool()`
   - Add commands and intercept tool calls
   - Documented at: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/extensions.md

3. **Comparison with Claude Code**: A detailed comparison exists at https://github.com/disler/pi-vs-claude-code comparing 12 categories including design philosophy, tools, hooks, SDK, and enterprise features

4. **Multi-Agent Systems**: Advanced tutorials exist for building multi-agent systems using Pi Agent extensions without native sub-agent support (https://atalupadhyay.wordpress.com/2026/02/24/pi-agent-revolution-building-customizable-open-source-ai-coding-agents-that-outperform-claude-code/)

5. **Architecture Documentation**:
   - Mintlify docs: https://pt-act-pi-mono.mintlify.app/concepts/architecture
   - Anatomy article: https://shivamagarwal7.medium.com/agentic-ai-pi-anatomy-of-a-minimal-coding-agent-powering-openclaw-5ecd4dd6b440

## X

**Not used.** (Browser scripts encountered errors)

## Reddit

**Not used.** (Browser scripts encountered errors)

## GitHub

**Key Repositories:**

1. **badlogic/pi-mono** (27,452 stars) - Core monorepo containing the coding agent CLI, unified LLM API, TUI & web UI libraries
   - URL: https://github.com/badlogic/pi-mono

2. **nicobailon/pi-subagents** (548 stars) - Pi extension for async subagent delegation with truncation, artifacts, and session sharing
   - URL: https://github.com/nicobailon/pi-subagents
   - Recent issues include session sharing failures and async execution problems

3. **can1357/oh-my-pi** (2,323 stars) - AI coding agent for terminal with hash-anchored edits, optimized tool harness, LSP, Python, browser, subagents support
   - URL: https://github.com/can1357/oh-my-pi

4. **jayminwest/overstory** (1,113 stars) - Multi-agent orchestration for AI coding agents with pluggable runtime adapters for Claude Code, Pi, and more
   - URL: https://github.com/jayminwest/overstory

5. **nicobailon/pi-messenger** (403 stars) - Multi-agent communication extension for pi coding agent
   - URL: https://github.com/nicobailon/pi-messenger

6. **badlogic/pi-skills** (909 stars) - Skills for pi coding agent compatible with Claude Code and Codex CLI
   - URL: https://github.com/badlogic/pi-skills

7. **openclaw/openclaw** (333,068 stars) - Personal AI assistant built on Pi, featuring Live Canvas, browser tools, nodes, cron, sessions
   - URL: https://github.com/openclaw/openclaw

8. **mergisi/awesome-openclaw-agents** (1,815 stars) - 162 production-ready AI agent templates for OpenClaw across 19 categories
   - URL: https://github.com/mergisi/awesome-openclaw-agents

9. **qualisero/awesome-pi-agent** (292 stars) - Curated list of add-ons, hooks, tools, skills, and resources for pi coding agent
   - URL: https://github.com/qualisero/awesome-pi-agent

10. **disler/pi-vs-claude-code** (537 stars) - Feature-by-feature comparison between Pi Agent and Claude Code
    - URL: https://github.com/disler/pi-vs-claude-code

**Key Issues Found:**
- Session sharing failures in pi-subagents (ERR_PACKAGE_PATH_NOT_EXPORTED errors)
- Async execution issues with jiti resolution
- Custom tools failing to load when importing from pi-coding-agent
- Multi-agent architecture improvements discussed in openclaw repo

## 综合结论

### 主要发现

1. **Pi Agent 的核心理念**: Pi 被设计为一个最小化的代码代理框架，强调可扩展性和开发者控制权。与 Claude Code 不同，Pi 原生不支持子代理（sub-agents），这是有意为之的设计选择，以保持系统的简洁性。

2. **扩展生态系统**: 社区已经开发了多个重要的扩展项目来实现子代理功能：
   - `pi-subagents` 提供异步子代理委托、截断、工件和会话共享
   - `oh-my-pi` 集成了完整的子代理支持
   - `overstory` 提供多代理编排框架

3. **OpenClaw 的主导地位**: OpenClaw 作为建立在 Pi 之上的项目，获得了 33 万+星标，成为最成功的 Pi 衍生项目。它通过网关架构将 Pi SDK 嵌入到消息系统中，而不是使用子进程或 RPC 模式。

4. **技术栈**:
   - TypeScript 扩展模块
   - 生命周期事件订阅
   - 自定义工具注册 (`pi.registerTool()`)
   - 会话持久化和共享
   - 与 Claude Code、Codex CLI 兼容的技能系统

5. **开发挑战**:
   - 包路径导出错误（ERR_PACKAGE_PATH_NOT_EXPORTED）
   - jiti 解析问题导致异步执行失败
   - 自定义工具加载时的子路径导入问题
   - 会话共享机制的稳定性

### 共识点

- Pi Agent 的核心价值在于其最小化设计和可扩展性
- 社区驱动的扩展模式成功弥补了原生功能的缺失
- TypeScript 扩展 API 是主要的开发方式
- OpenClaw 代表了 Pi Agent 最成功的应用案例

### 主要分歧

- **是否应该原生支持子代理**: Pi 创始人 Mario Zechner 认为不应该，而社区通过扩展实现了这一功能
- **扩展 vs 核心功能**: 某些功能（如子代理）应该在核心中实现还是作为可选扩展存在

## Gaps and Limitations

### 未覆盖的领域

1. **详细的 API 文档**: 虽然找到了扩展文档链接，但未能获取完整的 API 参考手册和最佳实践指南

2. **实际使用案例**: 缺乏企业级应用的实际部署经验和性能数据

3. **社区讨论深度**: 由于浏览器脚本问题，未能从 X 和 Reddit 获取社区讨论和开发者反馈

4. **代码实现细节**: 虽然找到了示例仓库，但未能深入阅读具体的扩展实现代码

5. **性能基准测试**: 缺少 Pi Agent 与其他代理框架（如 Claude Code、Codex CLI）的性能对比数据

6. **未来路线图**: 无法确认 Pi-mono 项目的官方发展计划和子代理功能的未来方向

### 研究限制

- 浏览器自动化脚本存在技术问题，限制了 X 和 Reddit 平台的访问
- 部分关键文档链接未能直接获取内容
- GitHub 搜索主要基于仓库描述，缺乏深入的代码级分析
