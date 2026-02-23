# memU 项目记忆架构技术分析

## 1. 目录结构概览

```
memU/
├── src/memu/
│   ├── app/                    # 核心应用服务
│   │   ├── memorize.py         # 记忆存储核心逻辑
│   │   ├── retrieve.py        # 记忆检索核心逻辑
│   │   ├── service.py         # 主服务入口 (MemoryService)
│   │   ├── settings.py        # 配置管理
│   │   └── crud.py            # 增删改查操作
│   ├── database/              # 数据库抽象层
│   │   ├── interfaces.py      # 数据库接口协议
│   │   ├── models.py          # 核心数据模型
│   │   ├── factory.py         # 数据库工厂
│   │   ├── inmemory/          # 内存存储实现
│   │   │   ├── repo.py        # 内存仓库
│   │   │   ├── state.py       # 状态管理
│   │   │   ├── vector.py      # 向量搜索实现
│   │   │   └── repositories/  # 各类仓库实现
│   │   ├── postgres/          # PostgreSQL + pgvector
│   │   └── sqlite/            # SQLite 实现
│   ├── prompts/               # LLM 提示词模板
│   │   ├── memory_type/       # 记忆类型提示词 (profile/event/knowledge/behavior/skill/tool)
│   │   ├── retrieve/          # 检索相关提示词
│   │   └── preprocess/       # 预处理提示词
│   ├── llm/                   # LLM 客户端封装
│   ├── embedding/             # 向量化模型封装
│   └── workflow/              # 工作流引擎
└── examples/                  # 使用示例
```

---

## 2. 核心数据模型

### 2.1 记忆类型 (MemoryType)
memU 定义了 6 种记忆类型：

| 类型 | 描述 |
|------|------|
| **profile** | 用户画像、偏好、沟通风格 |
| **event** | 重要事件、时间线 |
| **knowledge** | 知识、事实信息 |
| **behavior** | 行为模式、习惯 |
| **skill** | 学会的技能 |
| **tool** | 工具使用经验 |

### 2.2 核心数据结构 (`database/models.py`)

```python
# 资源 (对应原始材料)
class Resource(BaseRecord):
    url: str
    modality: str           # conversation, document, image, video, audio
    local_path: str
    caption: str | None
    embedding: list[float]  # 向量表示

# 记忆项 (核心记忆单元)
class MemoryItem(BaseRecord):
    resource_id: str | None
    memory_type: str        # profile/event/knowledge/behavior/skill/tool
    summary: str             # 记忆摘要
    embedding: list[float]   # 向量表示
    happened_at: datetime    # 事件时间
    extra: dict              # 扩展信息 (reinforcement_count, ref_id等)

# 记忆分类 (文件夹)
class MemoryCategory(BaseRecord):
    name: str
    description: str
    embedding: list[float]   # 分类向量
    summary: str | None      # 分类摘要

# 关联 (记忆与分类的映射)
class CategoryItem(BaseRecord):
    item_id: str
    category_id: str
```

---

## 3. 存储架构

### 3.1 多后端支持

memU 支持三种存储后端（通过 `database/factory.py` 选择）：

| 后端 | 用途 | 向量支持 |
|------|------|---------|
| **inmemory** | 开发/测试，内存存储 | 纯 Python 实现 |
| **sqlite** | 轻量级部署，本地文件 | 需要扩展 |
| **postgres** | 生产环境，高并发 | pgvector |

### 3.2 核心仓储模式

```python
# 协议定义 (database/interfaces.py)
class Database(Protocol):
    resource_repo: ResourceRepo
    memory_category_repo: MemoryCategoryRepo
    memory_item_repo: MemoryItemRepo
    category_item_repo: CategoryItemRepo
```

每个仓库实现了 Protocol 接口，支持：
- **MemoryItemRepo**: 记忆项的增删改查、向量搜索
- **MemoryCategoryRepo**: 分类管理
- **CategoryItemRepo**: 关联管理

---

## 4. 索引机制

### 4.1 向量索引

memU 使用 **余弦相似度** 进行向量检索 (`database/inmemory/vector.py`)：

```python
def cosine_topk(query_vec, corpus, k=5):
    # 批量计算余弦相似度
    q = np.array(query_vec)
    matrix = np.array([vec for _, vec in corpus])
    scores = matrix @ q / (norm(q) * norm(matrix) + 1e-9)
    # 使用 argpartition 实现 O(n) 复杂度选取 top-k
    return top-k results
```

### 4.2 显著性评分 (Salience Ranking)

memU 实现了高级排序算法，结合三个因素：

```
salience_score = similarity × reinforcement_factor × recency_factor

其中:
- similarity: 向量余弦相似度
- reinforcement_factor: log(强化次数 + 1)  # 对数防止过度强化
- recency_factor: exp(-0.693 × days_ago / half_life)  # 指数衰减
```

---

## 5. 搜索机制

### 5.1 分层检索策略

memU 实现了两层检索架构 (`app/retrieve.py`)：

#### RAG 模式 (基于向量)
1. **路由意图** - 判断是否需要检索
2. **分类检索** - 先找相关分类 (category)
3. **记忆项检索** - 从分类中找具体记忆 (item)
4. **资源检索** - 找原始资源 (resource)
5. **充分性判断** - LLM 判断是否需要继续检索

#### LLM 模式 (基于语言模型)
- 使用 LLM 评估每个记忆项与查询的相关性
- 支持更复杂的语义理解

### 5.2 引用机制

支持在记忆摘要中使用 `[ref:xxxx]` 格式引用其他记忆项，实现知识图谱式关联。

---

## 6. 记忆存储流程 (Memorize)

### 完整工作流 (`app/memorize.py`)

```
memorize(resource_url, modality)
    │
    ├─[Step 1] ingest_resource      - 获取原始内容
    │
    ├─[Step 2] preprocess_multimodal - 预处理 (分割/转录/理解)
    │   ├─ conversation: 分段 + 摘要
    │   ├─ image: Vision API 描述
    │   ├─ video: 提取关键帧 + Vision
    │   └─ document: 提取文本 + 摘要
    │
    ├─[Step 3] extract_items        - LLM 提取记忆项
    │   └─ 使用 memory_type prompt 生成结构化记忆
    │
    ├─[Step 4] deduplicate_merge    - 去重合并
    │
    ├─[Step 5] categorize_items     - 分类 + 向量化
    │   ├─ 创建 Resource
    │   ├─ 为记忆项生成 embedding
    │   └─ 建立与分类的关联
    │
    ├─[Step 6] persist_index        - 持久化 + 更新分类摘要
    │   └─ LLM 合并新记忆到分类摘要
    │
    └─[Step 7] build_response       - 返回结果
```

---

## 7. 记忆强化 (Reinforcement)

memU 实现了记忆强化机制 (`database/inmemory/repositories/memory_item_repo.py`)：

```python
def create_item_reinforce(self, *, ...):
    # 计算内容哈希
    content_hash = compute_content_hash(summary, memory_type)
    
    # 查找是否存在相同内容
    existing = self._find_by_hash(content_hash, user_data)
    if existing:
        # 强化现有记忆
        existing.extra["reinforcement_count"] += 1
        existing.extra["last_reinforced_at"] = now.isoformat()
    else:
        # 创建新记忆
        item_extra = {
            "content_hash": content_hash,
            "reinforcement_count": 1,
            "last_reinforced_at": now.isoformat()
        }
```

---

## 8. 核心模块总结

| 模块 | 职责 | 关键文件 |
|------|------|---------|
| **MemoryService** | 统一入口，组合各 mixin | `app/service.py` |
| **MemorizeMixin** | 记忆存储工作流 | `app/memorize.py` |
| **RetrieveMixin** | 记忆检索工作流 | `app/retrieve.py` |
| **Database** | 存储抽象，支持多后端 | `database/interfaces.py` |
| **MemoryItemRepo** | 记忆项 CRUD + 向量搜索 | `database/inmemory/repositories/memory_item_repo.py` |
| **WorkflowEngine** | 可扩展的工作流编排 | `workflow/pipeline.py` |

---

## 9. 技术亮点

1. **分层抽象**: 清晰的数据库接口协议，支持多存储后端
2. **向量检索**: 纯 Python 实现的高效余弦搜索，支持显著性排序
3. **记忆强化**: 通过内容哈希实现去重和强化机制
4. **工作流引擎**: 可扩展的分步处理流水线
5. **多模态支持**: 统一处理 conversation/document/image/video/audio
6. **LLM 驱动**: 充分利用大语言模型进行记忆提取和相关性判断
7. **分类系统**: 记忆分类 + 动态摘要更新

---

## 10. 总结

| 特性 | 实现方式 |
|------|----------|
| **存储** | 多后端支持 (inmemory/sqlite/postgres) |
| **结构** | Resource-MemoryItem-MemoryCategory 三层 |
| **记忆类型** | 6种类型 (profile/event/knowledge/behavior/skill/tool) |
| **索引** | 余弦相似度向量搜索 + 显著性排序 |
| **检索** | RAG模式 + LLM模式分层 |
| **强化** | 内容哈希去重 + 强化计数 |
| **多模态** | 支持 conversation/document/image/video/audio |

memU 是一个设计精良的生产级记忆框架，特别适合需要 **24/7 运行** 的 AI 智能体，特点是记忆类型分类清晰、工作流可扩展、多模态支持完善。

---

*文档生成时间：2026-02-23*
*来源：github_cache/memory/memU/*
