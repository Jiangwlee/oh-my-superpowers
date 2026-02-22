# Devchain 多智能体协作系统研究报告

## 1. 项目概述

**Devchain** 是一个支持 Claude Code、Codex、Gemini CLI 多智能体协作的开发工作流编排系统。通过 MCP (Model Context Protocol) 协议实现不同 AI 工具的统一通信和任务协作。

## 2. 核心架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      Devchain Local App                          │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Claude    │  │    Codex    │  │        Gemini           │  │
│  │    CLI      │  │    CLI      │  │         CLI             │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                      │                │
│         └────────────────┼──────────────────────┘                │
│                          │                                       │
│                   ┌──────▼──────┐                               │
│                   │  MCP HTTP   │  ← JSON-RPC over HTTP          │
│                   │  Endpoint   │    /mcp/rpc                    │
│                   └──────┬──────┘                               │
│                          │                                       │
│              ┌───────────┼───────────┐                          │
│              ▼           ▼           ▼                          │
│         ┌────────┐  ┌────────┐  ┌────────┐                      │
│         │ Epics  │  │  Chat  │  │Skills  │                      │
│         │Service │  │Service │  │Service │                      │
│         └────────┘  └────────┘  └────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 三层配置模型

```
Agent (实例) → Profile (角色) → ProviderConfig (AI CLI 配置)

Agent: {
  name: "Coder",
  profileId: "coder-profile",
  providerConfigId: "codex-high"
}

Profile: {
  name: "Coder",
  instructions: "[[prompt:Worker AI SOP]]",
  temperature: null
}

ProviderConfig: {
  name: "codex-high",
  providerName: "codex",
  options: "--model=gpt-5.3-codex"
}
```

## 3. 智能体拉起机制

### 3.1 启动流程

```typescript
// 1. 创建 tmux 会话
const tmuxSessionName = `devchain_${projectSlug}_${epicId}_${agentId}_${sessionId}`;
await tmuxService.createSession(tmuxSessionName, project.rootPath);

// 2. 构建命令行
const commandArgs = buildSessionCommand(envVars, provider.binPath, optionArgs);
// 结果: ['env', 'KEY=val', '/usr/local/bin/claude', '--model', 'opus']

// 3. 发送命令到 tmux
await tmuxService.sendCommandArgs(tmuxSessionName, commandArgs);

// 4. 延迟等待后注入 Initial Prompt
await renderAndPasteInitialPrompt({...});
```

### 3.2 实际命令示例

```bash
# Claude Code
tmux send-keys -t "devchain_myproj_abc123_def456_ghi789" \
  "env DEVCHAIN_API_URL=http://127.0.0.1:3000 \
       DEVCHAIN_PROJECT_ID=xxx \
       /usr/local/bin/claude --model claude-opus-4-6 --dangerously-skip-permissions" \
  Enter

# Codex
tmux send-keys -t "devchain_myproj_abc123_def456_ghi789" \
  "/usr/local/bin/codex --model=gpt-5.3-codex \
   --config model_reasoning_effort=\"high\" \
   --dangerously-bypass-approvals-and-sandbox" \
  Enter
```

## 4. MCP 统一通信协议

### 4.1 通信格式

**JSON-RPC 2.0 over HTTP**
```json
// 请求
{
  "jsonrpc": "2.0",
  "id": "uuid",
  "method": "tools/call",
  "params": {
    "name": "devchain_list_epics",
    "arguments": { "sessionId": "xxx", "statusName": "In Progress" }
  }
}

// 响应
{
  "jsonrpc": "2.0",
  "id": "uuid",
  "result": {
    "content": [{ "type": "text", "text": "..." }],
    "isError": false
  }
}
```

### 4.2 MCP Tools (40+ 工具)

| 类别 | 工具 |
|------|------|
| Epics | `devchain_list_epics`, `devchain_create_epic`, `devchain_update_epic` |
| Chat | `devchain_send_message`, `devchain_chat_read_history` |
| Agents | `devchain_list_agents`, `devchain_get_agent_by_name` |
| Documents | `devchain_list_documents`, `devchain_get_document` |
| Skills | `devchain_list_skills`, `devchain_get_skill` |
| Reviews | `devchain_list_reviews`, `devchain_get_review` |

## 5. 多智能体协作模式

### 5.1 典型协作流程 (Claude + Codex)

```
用户创建 Epic "实现登录功能"
         │
         ▼
┌─────────────────────┐
│ Epic Manager        │ 分配任务给 Coder
│ (Claude)            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Coder (Claude)      │ 编写代码
│                     │ devchain_update_epic → Review
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Code Reviewer       │ 审查代码
│ (Codex)             │ devchain_send_message → Coder
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Coder (Claude)      │ 修复问题
│                     │ 再次提交 Review
└──────────┬──────────┘
           │
           ▼
    [循环直到通过]
           │
           ▼
┌─────────────────────┐
│ Code Reviewer       │ 标记 Done
│ (Codex)             │
└─────────────────────┘
```

### 5.2 通信机制

#### 方式 1: devchain_send_message (实时)
```typescript
await devchain_send_message({
  sessionId: "reviewer-session-id",
  recipientAgentNames: ["Coder"],
  message: "发现安全问题：密码明文存储"
});
// 底层: tmux paste 注入到 Coder 终端
```

#### 方式 2: Epic 状态流转
```typescript
await devchain_update_epic({
  id: "epic-123",
  statusName: "Review",
  agentName: "Code Reviewer"  // 重新分配
});
```

#### 方式 3: Chat 线程
```typescript
await devchain_create_thread({
  participantAgentNames: ["Coder", "Code Reviewer"],
  title: "登录功能讨论"
});
```

## 6. Prompt 注入机制

### 6.1 Profile Instructions 解析

支持三种引用格式：
```typescript
// 1. 引用 Prompt 库
"[[prompt:Worker AI — Task Execution SOP (v1.0)]]"

// 2. 引用文档 (slug)
"[[development-standards]]"

// 3. 引用标签
"[[#architecture]]"
```

### 6.2 解析流程
```typescript
// InstructionsResolver.resolve()
const references = extractReferences(instructions);
for (const ref of references) {
  if (ref.type === 'prompt') {
    const prompt = await loadPromptByTitle(ref.value);
    content += buildPromptSnippet(prompt);
  }
}
```

## 7. 关键设计亮点

| 设计点 | 说明 |
|--------|------|
| **tmux 隔离** | 每个智能体独立会话，互不干扰 |
| **CLI 标准化** | 统一调用 claude/codex/gemini 命令 |
| **MCP 协议** | JSON-RPC 统一通信接口 |
| **动态 Prompt** | `[[...]]` 引用实现指令复用 |
| **消息队列** | Message Pool 支持离线消息 |
| **自动注册** | 启动时自动配置 MCP |

## 8. 与 Openclaw 的对比

| 特性 | Devchain | Openclaw |
|------|----------|----------|
| 多 Provider | ✅ Claude/Codex/Gemini | ? |
| 智能体管理 | Agent/Profile/ProviderConfig | Skills |
| 通信协议 | MCP over HTTP | ? |
| 任务管理 | Epic 工作流 | ? |
| 消息传递 | devchain_send_message | ? |
| 代码审查 | 内置 Review 系统 | ? |

## 9. 参考文件

- `github_cache/vibe-coding-discussion/apps/local-app/templates/5-agents-dev.json` - 5 智能体模板
- `github_cache/vibe-coding-discussion/apps/local-app/src/modules/mcp/tool-definitions.ts` - MCP 工具定义
- `github_cache/vibe-coding-discussion/apps/local-app/src/modules/sessions/services/sessions.service.ts` - 会话管理
- `github_cache/vibe-coding-discussion/apps/local-app/src/modules/mcp/services/mcp.service.ts` - MCP 服务实现

---

**研究日期**: 2026-02-22  
**研究项目**: TwiTech-LAB/devchain  
**研究人**: Openclaw Assistant
