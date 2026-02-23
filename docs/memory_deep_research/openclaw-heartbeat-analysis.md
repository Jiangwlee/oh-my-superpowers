# OpenClaw Heartbeat 与会话总结机制深度分析

## 1. Heartbeat 机制概述

### 1.1 Heartbeat 是什么

Heartbeat 是 OpenClaw 的定时检查机制，用于定期检查是否需要向用户发送通知。

### 1.2 默认 Heartbeat Prompt

```typescript
// src/auto-reply/heartbeat.ts
export const HEARTBEAT_PROMPT =
  "Read HEARTBEAT.md if it exists (workspace context). Follow it strictly. " +
  "Do not infer or repeat old tasks from prior chats. " +  // ⚠️ 明确禁止从历史会话中提取任务
  "If nothing needs attention, reply HEARTBEAT_OK.";
```

**关键要点**：
- ✅ 读取 HEARTBEAT.md 文件
- ❌ **不要**从之前的聊天中推断或重复旧任务
- 如果没有需要关注的，返回 HEARTBEAT_OK

### 1.3 Heartbeat 触发条件

```typescript
// src/infra/heartbeat-runner.ts
// 检查是否有待处理的系统事件
const shouldInspectPendingEvents = 
  reasonFlags.isExecEventReason || 
  reasonFlags.isCronEventReason || 
  hasTaggedCronEvents;
  
// 根据不同事件使用不同的 prompt
const prompt = hasExecCompletion
  ? EXEC_EVENT_PROMPT  // 异步命令完成
  : hasCronEvents
    ? buildCronEventPrompt(cronEvents)  // Cron 事件
    : resolveHeartbeatPrompt(cfg, heartbeat);  // 默认 heartbeat prompt
```

---

## 2. Heartbeat 能否触发历史会话总结？

### 2.1 结论：**不能**

Heartbeat 的设计目标是：
1. 检查 HEARTBEAT.md 是否有待处理任务
2. 响应 Cron 事件（如定时任务完成）
3. 响应异步命令完成事件

**Heartbeat 明确不做什么**：
- ❌ 从历史会话中总结信息
- ❌ 推断或重复旧任务
- ❌ 主动分析记忆数据

### 2.2 为什么 Heartbeat 不适合做总结

1. **Prompt 明确禁止**：默认 prompt 说 "Do not infer or repeat old tasks from prior chats"
2. **设计目标不同**：Heartbeat 是"检查"机制，不是"分析"机制
3. **触发频率问题**：Heartbeat 可能频繁触发（默认 30 分钟），不适合做重计算

---

## 3. OpenClaw 的会话总结机制：session-memory Hook

### 3.1 触发时机

**session-memory Hook** 在以下时机触发：
- 用户执行 `/new` 命令
- 用户执行 `/reset` 命令

### 3.2 工作流程

```
/new 或 /reset 命令
       ↓
1. 查找上一个会话文件
       ↓
2. 提取最近 N 条对话（默认 15 条，可配置）
       ↓
3. 使用 LLM 生成描述性 slug（文件名）
       ↓
4. 创建 memory/YYYY-MM-DD-slug.md 文件
       ↓
5. 写入会话内容
```

### 3.3 输出格式

```markdown
# Session: 2026-01-16 14:30:00 UTC

- **Session Key**: agent:main:main
- **Session ID**: abc123def456
- **Source**: telegram

## Conversation Summary

user: ...
assistant: ...
```

### 3.4 配置选项

```json
{
  "hooks": {
    "internal": {
      "entries": {
        "session-memory": {
          "enabled": true,
          "messages": 25  // 包含最近 25 条对话
        }
      }
    }
  }
}
```

---

## 4. 与记忆系统的关系

### 4.1 session-memory Hook 与 Memory 的关系

| 特性 | session-memory Hook | Memory 系统 |
|------|---------------------|-------------|
| **触发条件** | /new 或 /reset | 用户查询时 |
| **数据来源** | 当前会话历史 | 所有已保存记忆 |
| **生成方式** | 复制对话原文 | 向量搜索 + 混合搜索 |
| **存储位置** | `memory/YYYY-MM-DD-slug.md` | `MEMORY.md` + `memory/*.md` |
| **目的** | 保留会话历史 | 提供长期记忆检索 |

### 4.2 数据流

```
会话进行中
     ↓
用户执行 /new 或 /reset
     ↓
session-memory Hook 触发
     ↓
提取会话内容 → 生成 slug → 保存到 memory/*.md
     ↓
新会话开始，可以使用 memory_search 检索历史
```

---

## 5. 总结

### 5.1 OpenClaw 的记忆总结机制

| 机制 | 触发条件 | 目的 | 是否主动分析历史 |
|------|----------|------|-----------------|
| **Heartbeat** | 定时/Cron事件 | 检查待处理任务 | ❌ 明确禁止 |
| **session-memory Hook** | /new 或 /reset | 保存会话历史 | ⚠️ 仅保存当前会话 |
| **Memory 搜索** | 用户查询 | 检索记忆 | ❌ 被动检索 |

### 5.2 关键发现

1. **Heartbeat 不是用来总结历史的**：默认 prompt 明确说 "Do not infer or repeat old tasks from prior chats"

2. **会话总结通过 Hook 实现**：只有当用户主动执行 `/new` 或 `/reset` 时，才会保存会话到 memory

3. **没有主动分析机制**：OpenClaw 缺乏类似 "Insight" 的主动分析历史记忆、提取共性模式的功能

4. **记忆系统是被动的**：只有用户查询时才会检索记忆，没有后台定时分析任务

---

## 6. 对比：Heartbeat vs session-memory Hook

| 特性 | Heartbeat | session-memory Hook |
|------|-----------|---------------------|
| **触发方式** | 定时（默认 30 分钟） | 手动（/new 或 /reset） |
| **数据来源** | HEARTBEAT.md + 系统事件 | 当前会话内容 |
| **输出** | 通知用户或 HEARTBEAT_OK | 保存到 memory/*.md |
| **分析历史** | ❌ 明确禁止 | ⚠️ 仅当前会话 |
| **AI 模型调用** | 是 | 是（生成 slug） |

---

*文档生成时间：2026-02-23*
*来源：github_cache/openclaw-repos/openclaw/*
