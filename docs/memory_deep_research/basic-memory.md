# Basic Memory 项目记忆架构技术分析

## 1. 项目概述

**Basic Memory** 是一个本地优先(local-first)的知识管理系统，基于 **Model Context Protocol (MCP)** 实现。它让 AI 助手（如 Claude）可以读取和写入本地 Markdown 文件，构建可遍历的知识图谱。

核心特点：
- 本地文件为数据源（Markdown 文件）
- SQLite/PostgreSQL 作为索引数据库
- 支持语义搜索和知识图谱遍历
- 支持云端同步（可选）

---

## 2. 目录结构

```
src/basic_memory/
├── api/                    # FastAPI REST API
│   └── v2/routers/         # API路由
├── deps/                   # 依赖注入
├── importers/             # 导入器（Claude, ChatGPT等）
├── markdown/               # Markdown解析和处理
│   ├── entity_parser.py    # 实体解析器
│   ├── markdown_processor.py
│   └── plugins.py         # Markdown插件
├── models/                # SQLAlchemy ORM模型
│   ├── knowledge.py       # Entity, Observation, Relation
│   └── base.py
├── mcp/                   # MCP服务器和工具
│   ├── tools/             # MCP工具
│   └── prompts/           # 提示模板
├── repository/            # 数据访问层
├── schema/                # Schema解析和验证
├── services/              # 业务逻辑层
│   ├── entity_service.py  # 实体管理
│   ├── search_service.py  # 搜索服务
│   ├── context_service.py # 上下文构建
│   └── link_resolver.py   # 链接解析
└── sync/                  # 文件同步服务
    └── sync_service.py    # 文件系统与数据库同步
```

---

## 3. 核心记忆机制实现

### 3.1 存储方式

**双层存储架构**：
1. **文件系统（源）**：Markdown 文件存储在本地目录
2. **数据库（索引）**：SQLite/PostgreSQL 用于索引和查询

```python
# Entity 模型 - basic_memory/models/knowledge.py
class Entity(Base):
    """Core entity in the knowledge graph."""
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String, unique=True)
    title: Mapped[str] = mapped_column(String)
    note_type: Mapped[str] = mapped_column(String)  # e.g., "person", "project"
    permalink: Mapped[Optional[str]] = mapped_column(String)  # 规范化路径
    file_path: Mapped[str] = mapped_column(String)  # 实际文件路径
    checksum: Mapped[Optional[str]] = mapped_column(String)  # 文件变更检测
    
    # 关系
    observations = relationship("Observation", back_populates="entity")
    outgoing_relations = relationship("Relation", foreign_keys="[Relation.from_id]")
    incoming_relations = relationship("Relation", foreign_keys="[Relation.to_id]")
```

**三种核心数据结构**：
- **Entity（实体）**：代表一个概念/文档，对应一个 Markdown 文件
- **Observation（观察）**：实体的分类事实，格式：`- [category] content`
- **Relation（关系）**：实体间的方向链接，格式：`- relation_type [[Target]]`

### 3.2 索引机制

**SearchService** 负责构建全文搜索索引：

```python
# basic_memory/services/search_service.py
class SearchService:
    """支持三种搜索模式:
    1. Exact permalink lookup
    2. Pattern matching with * (e.g., 'specs/*')
    3. Full-text search across title/content
    """
```

**索引内容**：
- 实体本身（标题、permalink、内容片段）
- 所有 Observations（分类事实）
- 所有 Relations（关系）

**搜索特性**：
- 支持全文搜索（FTS5 for SQLite, PostgreSQL full-text search）
- 支持语义搜索（可选，向量嵌入）
- 支持标签过滤、元数据过滤、时间范围过滤
- 智能降级：严格搜索无结果时，自动尝试宽松 OR 查询

### 3.3 搜索方式

```python
# 搜索API示例
await search_service.search(
    query=SearchQuery(
        text="coffee brewing",        # 搜索文本
        tags=["technique"],           # 标签过滤
        note_types=["person"],       # 类型过滤
        after_date="2024-01-01",    # 时间过滤
        retrieval_mode=SearchRetrievalMode.FTS  # 搜索模式
    ),
    limit=10,
    offset=0
)
```

**搜索流程**：
1. 解析查询参数
2. 执行 FTS5/全文搜索
3. 如果无结果，尝试宽松搜索（去除停用词）
4. 返回结构化结果

### 3.4 核心模块

| 模块 | 职责 |
|------|------|
| **EntityService** | 实体的创建、读取、更新、删除（CRUD）操作 |
| **SearchService** | 全文搜索索引构建与查询 |
| **ContextService** | 基于知识图谱的上下文构建（图遍历） |
| **SyncService** | 文件系统与数据库的同步（增量扫描、水印优化） |
| **LinkResolver** | WikiLink `[[Target]]` 的解析与关系构建 |
| **EntityParser** | Markdown 解析（提取 observations 和 relations） |

---

## 4. 知识图谱遍历

**ContextService** 实现知识图谱的上下文感知遍历：

```python
# basic_memory/services/context_service.py
class ContextService:
    """处理三种上下文构建方式:
    1. Direct permalink lookup - 精确路径查找
    2. Pattern matching - 使用 * 通配符
    3. Graph traversal - 关系图遍历
    """
```

使用 **递归 CTE** 实现图遍历：
- 支持深度遍历（默认 depth=1）
- 支持时间范围过滤
- 同时返回实体、observations、relations

---

## 5. 同步机制

**SyncService** 实现文件与数据库的增量同步：

```python
# 智能扫描优化
class SyncService:
    """水印追踪优化:
    - 记录 last_scan_timestamp 和 last_file_count
    - 使用 find -newermt 进行增量扫描
    - 大型项目性能提升 84x-225x
    """
    
    async def sync(self, directory: Path, force_full: bool = False):
        # 1. 扫描检测变更（新增/修改/删除/移动）
        # 2. 处理文件变更
        # 3. 解析关系（解决前向引用）
        # 4. 更新搜索索引
        # 5. 更新水印
```

**变更检测策略**：
1. 比较 mtime（修改时间）和 size（文件大小）
2. 比较 checksum（校验和）确认实际变更
3. 通过 checksum 匹配检测文件移动

---

## 6. Markdown 格式

项目使用结构化的 Markdown 格式：

```markdown
---
title: Coffee Brewing
type: topic
permalink: coffee/brewing
tags: [technique, coffee]
---

# Coffee Brewing

## Observations
- [method] Pour over produces clean, bright flavors
- [equipment] V60 dripper requires precise timing

## Relations
- relates_to [[Coffee Beans]]
- implements [[Brewing Recipe]]
```

---

## 7. 总结

Basic Memory 的记忆架构设计要点：

| 特性 | 实现方式 |
|------|----------|
| **存储** | Markdown 文件 + SQLite/PostgreSQL 索引 |
| **结构** | Entity-Observation-Relation 三元组 |
| **索引** | 全文搜索（FTS5）+ 向量搜索（可选） |
| **搜索** | 精确匹配 + 通配符 + 全文检索 + 智能降级 |
| **遍历** | 递归 CTE 图遍历，支持深度和时效过滤 |
| **同步** | 增量扫描 + 水印优化 + 变更检测 |
| **扩展** | MCP 协议支持多 AI 客户端 |

这是一个设计精良的本地优先知识管理系统，特别适合需要 AI 辅助知识管理的场景。

---

*文档生成时间：2026-02-23*
*来源：github_cache/memory/basic-memory/*
