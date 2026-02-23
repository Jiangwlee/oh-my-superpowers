# OpenClaw 记忆系统深度研究报告

## 概述

OpenClaw 是一个 AI 代理框架，其记忆系统是一个精心设计的生产级系统，基于 Markdown 文件存储，结合向量语义搜索、关键词搜索、时序衰减和多样性重排序，支持多种嵌入提供商，并在会话压缩前自动触发记忆刷新，确保重要信息不会丢失。

---

## 1. 存储架构

### 1.1 双层存储结构

```
~/.openclaw/workspace/
├── MEMORY.md                    # 长期记忆（精选，仅主会话加载）
└── memory/
    └── YYYY-MM-DD.md           # 每日日志（追加模式，加载今天+昨天）
```

**核心理念**：文件是唯一的真相来源，模型只"记住"写入磁盘的内容。

### 1.2 存储策略

| 文件 | 加载策略 | 用途 |
|------|----------|------|
| `MEMORY.md` | 仅主会话加载 | 长期记忆，精选内容 |
| `memory/YYYY-MM-DD.md` | 今天 + 昨天 | 近期工作日志 |

---

## 2. 索引层实现

### 2.1 数据库架构

OpenClaw 使用 SQLite + FTS5 作为索引层：

```sql
-- 元数据表
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);

-- 文件追踪表
CREATE TABLE files (
  path TEXT PRIMARY KEY,
  source TEXT DEFAULT 'memory',
  hash TEXT, mtime INTEGER, size INTEGER
);

-- 文本块表（带向量嵌入）
CREATE TABLE chunks (
  id TEXT PRIMARY KEY,
  path TEXT, source TEXT,
  start_line INTEGER, end_line INTEGER,
  hash TEXT, model TEXT,
  text TEXT, embedding TEXT,
  updated_at INTEGER
);

-- 全文搜索虚拟表（FTS5）
CREATE VIRTUAL TABLE chunks_fts USING fts5(text, id, path...);

-- 嵌入缓存表
CREATE TABLE embedding_cache (
  provider, model, provider_key, hash,
  embedding TEXT, dims INTEGER,
  PRIMARY KEY (provider, model, provider_key, hash)
);
```

### 2.2 向量嵌入支持

| 提供商 | 默认模型 | 特点 |
|--------|----------|------|
| OpenAI | `text-embedding-3-small` | 远程，支持批量API |
| Gemini | `gemini-embedding-001` | 远程 |
| Voyage | `voyage-4-large` | 远程 |
| Local | `embeddinggemma-300m-qat` | 本地，node-llama-cpp |

**自动选择优先级**：local（如果配置）→ openai → gemini → voyage

---

## 3. 搜索机制

### 3.1 双工具设计

OpenClaw 提供两个记忆工具供模型调用：

| 工具 | 功能 | 使用场景 |
|------|------|----------|
| `memory_search` | 语义搜索，返回片段 | 回答关于之前工作、决策、日期等问题 |
| `memory_get` | 精确读取指定文件的指定行 | 在 search 后获取详细内容 |

**工具调用触发条件**（system-prompt.ts）：
```
"Before answering anything about prior work, decisions, dates, people, 
preferences, or todos: run memory_search on MEMORY.md + memory/*.md; 
then use memory_get to pull only the needed lines."
```

### 3.2 混合搜索（Hybrid Search）

结合两种检索方式：

| 方式 | 优势 | 适用场景 |
|------|------|----------|
| **向量相似度** | 语义匹配，支持同义改写 | "Mac Studio网关主机" vs "运行网关的机器" |
| **BM25关键词** | 精确匹配ID、代码符号 | `a828e60`, `memorySearch.query.hybrid` |

**合并公式**：
```
finalScore = vectorWeight × vectorScore + textWeight × textScore
```

**默认权重**：vectorWeight = 0.7, textWeight = 0.3

### 3.3 高级后处理

#### 时序衰减（Temporal Decay）

- **公式**：`decayedScore = score × e^(-λ × ageInDays)`
- **半衰期**：默认 30 天
- **常绿文件**：`MEMORY.md` 不参与衰减

#### MMR 重排序（MMR Diversity）

- 平衡相关性与多样性
- 避免返回相似/重复的记忆片段
- 参数 `lambda=0.7`（偏向相关性）

---

## 4. 自动记忆刷新

### 4.1 会话压缩前刷新

当会话接近自动压缩阈值时，触发**静默 agentic turn**：

```typescript
// 默认阈值
contextWindow - 20000 - 4000 tokens
```

**工作流程**：
1. 系统检测到上下文接近压缩阈值
2. 静默触发一个 agentic turn（用户无感知）
3. 提醒模型在上下文被压缩前写入持久记忆
4. 模型将重要信息写入 `memory/YYYY-MM-DD.md`
5. 返回 `NO_REPLY`，继续正常对话

### 4.2 配置项

```json5
{
  agents: {
    defaults: {
      compaction: {
        memoryFlush: {
          enabled: true,
          softThresholdTokens: 4000,
          prompt: "Write lasting notes to memory/YYYY-MM-DD.md"
        }
      }
    }
  }
}
```

---

## 5. 同步机制

| 触发时机 | 行为 |
|----------|------|
| 会话启动 | 预热同步（如果 `onSessionStart=true`） |
| 搜索时 | 如果索引脏，后台同步 |
| 文件监听 | 文件变化时标记 dirty，debounce 1.5s 后同步 |
| 定时同步 | 可配置 `intervalMinutes` |
| 会话记录 | 达到 delta 阈值时异步索引 |

---

## 6. 核心代码结构

```
src/
├── memory/
│   ├── manager.ts            # 记忆索引管理器
│   ├── memory-schema.ts      # 数据库 Schema 定义
│   ├── embeddings.ts         # 向量嵌入实现
│   ├── hybrid.ts             # 混合搜索实现
│   ├── sync-*.ts            # 文件同步相关
│   └── types.ts             # 类型定义
├── agents/
│   ├── memory-search.ts      # 记忆搜索配置解析
│   └── tools/
│       └── memory-tool.ts   # memory_search 和 memory_get 工具
└── auto-reply/
    └── reply/
        └── memory-flush.ts  # 自动记忆刷新
```

---

## 7. 配置示例

```json5
{
  agents: {
    defaults: {
      memorySearch: {
        provider: "openai",
        model: "text-embedding-3-small",
        fallback: "gemini",
        query: {
          maxResults: 6,
          minScore: 0.35,
          hybrid: {
            enabled: true,
            vectorWeight: 0.7,
            textWeight: 0.3,
            mmr: { enabled: true, lambda: 0.7 },
            temporalDecay: { enabled: true, halfLifeDays: 30 }
          }
        },
        sync: { watch: true, onSessionStart: true, onSearch: true },
        cache: { enabled: true, maxEntries: 50000 }
      }
    }
  }
}
```

---

## 8. 扩展：QMD 后端（实验性）

可选替换内置 SQLite 索引器：

- **QMD**：结合 BM25 + 向量 + 重排序
- 本地优先：Bun + node-llama-cpp 运行
- 支持会话 JSONL 索引
- 失败自动回退到内置管理器

---

## 9. 与 OpenCode 对比

| 特性 | OpenClaw | OpenCode |
|------|----------|----------|
| **存储** | `~/.openclaw/workspace/MEMORY.md` + `memory/YYYY-MM-DD.md` | `.github/instructions/memory.instruction.md` |
| **搜索** | 向量+BM25混合搜索 | 无 |
| **自动触发** | 系统prompt强制要求搜索 | 仅用户要求时 |
| **索引** | SQLite + FTS5 向量 | 无 |
| **时效性** | 时序衰减 + MMR | 无 |
| **复杂度** | 生产级系统 | 简单文件系统 |

---

## 10. 总结

OpenClaw 的记忆机制是一个**生产级系统**，具有以下核心特性：

1. **文件即真相**：所有记忆都持久化到 Markdown 文件
2. **混合搜索**：结合向量语义搜索和 BM25 关键词搜索
3. **智能排序**：时序衰减 + MMR 多样性重排序
4. **自动刷新**：会话压缩前自动触发记忆保存
5. **灵活配置**：支持多种嵌入提供商和可调节参数

这套系统确保了 AI 代理在长期会话中能够有效利用历史信息，同时避免了上下文膨胀问题。

---

*文档生成时间：2026-02-23*
*来源：github_cache/openclaw-repos/openclaw/*
