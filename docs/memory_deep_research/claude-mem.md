# Claude-Mem 记忆架构技术分析

## 1. 项目整体结构

```
claude-mem/
├── src/
│   ├── services/           # 核心服务层
│   │   ├── sqlite/         # SQLite 存储层
│   │   ├── worker/         # Worker 服务 (API)
│   │   ├── context/        # 上下文生成
│   │   ├── sync/           # Chroma 向量同步
│   │   └── ...
│   ├── hooks/              # Claude Code 生命周期钩子
│   ├── cli/                # 命令行工具
│   ├── sdk/                # SDK 解析器
│   └── ui/                 # Web UI
├── plugin/                 # 构建后的插件
└── tests/                  # 测试
```

---

## 2. 存储架构

### 2.1 核心存储: SQLite (使用 bun:sqlite)

**位置**: `src/services/sqlite/Database.ts` 和 `SessionStore.ts`

**存储位置**: `~/.claude-mem/claude-mem.db`

**核心表结构**:

| 表名 | 用途 |
|------|------|
| `sdk_sessions` | 会话元数据 (content_session_id, memory_session_id, project, status) |
| `observations` | 观察记录 (AI 生成的洞察、结构化数据) |
| `session_summaries` | 会话总结 (request, learned, completed, next_steps 等) |
| `user_prompts` | 用户提示词 + FTS5 全文搜索索引 |
| `pending_messages` | 持久化消息队列 (支持崩溃恢复) |
| `schema_versions` | 数据库迁移版本记录 |

**SQLite 优化配置**:
- WAL 模式 (写前日志)
- 256MB 内存映射
- 10,000 页缓存
- 完整的索引策略

### 2.2 向量存储: ChromaDB

**位置**: `src/services/sync/ChromaSync.ts`

**用途**: 语义搜索 (Semantic Search)

**工作方式**:
- 通过 MCP (Model Context Protocol) 与 chroma-mcp 服务通信
- 每条 observation/summary 的不同字段 (narrative, facts, concepts) 存储为独立的向量文档
- 支持按项目隔离的 Collection

---

## 3. 索引机制

### 3.1 SQLite 索引策略

```sql
-- observations 表索引
idx_observations_sdk_session   (memory_session_id)
idx_observations_project       (project)
idx_observations_type          (type)
idx_observations_created      (created_at_epoch DESC)

-- session_summaries 表索引
idx_session_summaries_sdk_session (memory_session_id)
idx_session_summaries_project      (project)
idx_session_summaries_created     (created_at_epoch DESC)
```

### 3.2 FTS5 全文搜索

**user_prompts** 表使用 FTS5 虚拟表:
- 自动同步触发器 (INSERT/DELETE/UPDATE)
- 支持 prompt_text 全文搜索

### 3.3 向量索引 (Chroma)

每个 observation 被分解为多个向量文档:
- `obs_{id}_narrative` - 叙事内容
- `obs_{id}_text` - 原始文本 (遗留字段)
- `obs_{id}_fact_{index}` - 每个事实单独向量

---

## 4. 搜索机制

### 4.1 搜索策略架构

**位置**: `src/services/worker/search/`

| 策略 | 文件 | 用途 |
|------|------|------|
| `SQLiteSearchStrategy` | SQLite 过滤搜索 | 仅使用元数据过滤 (日期、类型、概念、文件) |
| `ChromaSearchStrategy` | 向量语义搜索 | 纯语义相似度搜索 |
| `HybridSearchStrategy` | 混合搜索 | 元数据过滤 + 向量排序 |

### 4.2 搜索流程

```
用户查询 → SearchManager.search()
    │
    ├─→ [无查询文本] → SQLiteSearchStrategy (过滤搜索)
    │
    └─→ [有查询文本] 
           │
           ├─→ ChromaDB 可用 → 返回语义匹配 ID 列表
           │       ↓
           ├─→ 按 90 天窗口过滤
           ├─→ 按文档类型分类 (obs/session/prompt)
           └─→ SQLite 获取完整数据 + 二次过滤
           │
           └─→ ChromaDB 不可用 → 返回错误提示
```

### 4.3 专用搜索接口

- **search**: 通用搜索 (支持多类型)
- **timeline**: 时间线上下文 (围绕锚点的历史)
- **decisions**: 决策类型观察
- **changes**: 变更相关观察
- **how_it_works**: 架构/原理类观察
- **find_by_concept/ type/ file**: 按概念/类型/文件搜索
- **get_recent_context**: 获取最近会话上下文

---

## 5. 上下文生成 (Context Generation)

**位置**: `src/services/context/`

### 5.1 核心模块

| 模块 | 职责 |
|------|------|
| `ContextBuilder.ts` | 主协调器，组装上下文 |
| `ObservationCompiler.ts` | 从数据库检索数据 |
| `TokenCalculator.ts` | Token 预算计算 |
| `TimelineRenderer.ts` | 时间线渲染 |
| `SummaryRenderer.ts` | 总结渲染 |

### 5.2 上下文注入流程

1. 加载配置 (ContextConfigLoader)
2. 计算 token 预算
3. 获取相关观察/总结 (ObservationCompiler)
4. 按时间/文件分组
5. 渲染为 Markdown 格式

---

## 6. 核心模块依赖关系

```
worker-service.ts (主入口)
    │
    ├── SearchManager.ts (搜索处理)
    │       ├── SessionStore.ts (SQLite CRUD)
    │       ├── SessionSearch.ts (SQLite 搜索)
    │       └── ChromaSync.ts (向量同步)
    │
    ├── SessionManager.ts (会话管理)
    │       └── SessionStore.ts
    │
    ├── ContextBuilder.ts (上下文生成)
    │       ├── SessionStore.ts
    │       └── ObservationCompiler.ts
    │
    └── Database.ts (数据库管理)
            ├── migrations (21+ 版本迁移)
            └── bun:sqlite
```

---

## 7. 记忆生命周期

### 5 个 Claude Code 钩子

| 钩子 | 时机 | 存储内容 |
|------|------|----------|
| SessionStart | 会话开始 | 创建 sdk_sessions 记录 |
| UserPromptSubmit | 用户提交提示 | user_prompts |
| PostToolUse | 工具使用后 | observations (AI 观察) |
| Summary | 会话总结 | session_summaries |
| SessionEnd | 会话结束 | 更新会话状态 |

### 数据流

```
Hook → Worker Service (HTTP) → 消息队列 → SDK Agent (AI 处理) 
                                              ↓
                                     ChromaDB 同步
                                              ↓
                                     SQLite 持久化
```

---

## 8. 关键设计特点

1. **双 Session ID 机制**
   - `content_session_id`: 用户可见的会话 ID
   - `memory_session_id`: 记忆系统的内部会话 ID (支持恢复)

2. **崩溃恢复**: `pending_messages` 表支持消息持久化和重试

3. **隐私保护**: `<private>` 标签在钩子层剥离

4. **混合搜索**: 结合 SQLite 元数据过滤和 Chroma 向量语义排序

5. **渐进式架构**: 支持纯 SQLite 模式 (无 Chroma) 作为 fallback

---

## 9. 总结

| 特性 | 实现方式 |
|------|----------|
| **存储** | SQLite (bun:sqlite) + ChromaDB 向量 |
| **索引** | FTS5 全文搜索 + Chroma 向量索引 |
| **搜索** | SQLite过滤 + Chroma语义 + 混合搜索 |
| **上下文** | Token预算 + 时间线/总结渲染 |
| **生命周期** | 5个 Claude Code 钩子 |
| **特殊** | 崩溃恢复、双Session ID机制 |

Claude-Mem 是一个设计完善的生产级 AI 记忆系统，特别适合 Claude Code 用户长期上下文记忆场景。

---

*文档生成时间：2026-02-23*
*来源：github_cache/memory/claude-mem/*
