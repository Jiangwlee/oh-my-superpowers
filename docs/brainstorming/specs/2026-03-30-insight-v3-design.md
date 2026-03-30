# Insight v3：三层 Pipeline 架构改进

> 借鉴 Claude Code /insights 的三层 pipeline，将 omp-insight 从两层（capture → evaluate）升级为三层（capture → aggregate → evaluate），提升信号质量和聚合精度。

## 目录

- [设计方案](#设计方案)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 背景与目标

omp-insight v2 采用两层架构：capture（LLM → 自由文本 Memory）→ evaluate（LLM → Insight）。痛点：capture 输出是自由文本，导致 evaluate 缺少可靠的统计输入，所有聚合逻辑由 LLM 完成，信号质量不稳定。

v3 目标：插入代码聚合层，让 LLM 只做语义判断，确定性统计由代码完成。

### 架构

```
v2: Session JSONL → Capture (LLM → 自由文本 Memory) → Evaluate (LLM → Insight)

v3: Session JSONL → Capture (LLM → 6字段结构化 Memory) → Aggregate (代码) → Evaluate (LLM → Insight)
```

三层职责：

| 层 | 输入 | 输出 | 执行者 |
|----|------|------|--------|
| Capture | session 对话 | 6 字段结构化 Memory | LLM（per-session），角色：复盘分析师 |
| Aggregate | 全量 Memory 表 | 聚合统计 JSON | 纯 Python 代码 |
| Evaluate | 聚合统计 + top-N summary | Insight | LLM（单次），角色：持续改进顾问 |

### Memory 新 Schema（6 字段）

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | enum: bug/decision/pattern/friction/workflow/other | 最小可计算分类 |
| `scope` | enum: file/module/skill/agent/project/other | 影响范围 |
| `summary` | string (≤100字) | 人类可读短文本 |
| `source` | string | "session_id@runtime" |
| `evidence_ref` | string | 原始证据位置 |
| `confidence` | float 0.0-1.0 | 置信度（可选） |

附加可选字段：`tags: list[str]`

### Aggregate 输出结构

```python
@dataclass
class AggregateResult:
    total_memories: int
    time_range: tuple[datetime, datetime]
    by_kind: dict[str, KindStats]       # kind → 统计
    by_scope: dict[str, int]            # scope → 计数
    top_tags: list[tuple[str, int]]     # 高频 tags top-20
    samples_by_kind: dict[str, list[str]]  # kind → top-5 summaries

@dataclass
class KindStats:
    count: int
    avg_confidence: float
    recent_7d: int
    recent_30d: int
    top_scopes: list[tuple[str, int]]
```

Aggregate 纯函数签名：`def aggregate(memories: list[Memory]) -> AggregateResult`

只做：按 kind/scope 分组频次、时间窗口趋势、精确去重、confidence 加权、tag 共现检测。不做语义归类。不访问 SQLite，数据来源是 `store.list_memories()` 读取的 markdown 文件。

> **注意**：Insight dataclass 本身不需要修改。`evidence` 字段语义从 "memory IDs" 改为 "kind 列表" 仅影响 EVALUATE_PROMPT 的输出格式，不影响 Insight 结构。

### Evaluate 重构

- 输入从全量 Memory 文本改为 AggregateResult JSON + 每组 top-5 summary
- evidence 字段语义从 memory IDs 改为 kind 列表
- 先单路，数据量 >1000 条或输出质量下降时再按认知边界拆 facet（模式发现/风险识别/行动建议）

### 关键决策

- **混合模式 C**：JSON 结构 + narrative 字段，Round Table 全票通过
- **不引入 embedding normalization layer**：Round Table 3:1 否决，避免模型版本漂移和调参黑箱，embedding 仅做离线实验
- **删表重建**：旧 Memory 表直接删除，重新执行 capture，不做迁移兼容
- **kind/scope 允许 other**：枚举表是产品资产，other 积累后人工决策是否扩展
- **CLI 接口不变**：aggregate 是 evaluate 的内部前置步骤，不新增子命令

---

## 行动原则

- **确定性聚合 > LLM 猜测**：凡是能用代码稳定算出来的，不丢给模型。**禁止：** 在 aggregate 层调用 LLM
- **粗糙可审计 > 精致黑箱**：枚举 + GROUP BY，不引入 embedding。**禁止：** 在主链路引入 embedding/向量聚类
- **破坏性升级 > 兼容性补丁**：删旧表重建，不做迁移层。**禁止：** 兼容性 shim、deprecated 标记
- **YAGNI**：单路 evaluate，不预建 facet 拆分。**禁止：** 预留"未来可能需要"的接口
- **TDD**：先写 aggregate 测试，再实现。**禁止：** 未经测试验证就报告完成

---

## 行动计划

### 文件结构设计

| 操作 | 文件路径 | 职责 |
|------|----------|------|
| 修改 | `skills/insight/scripts/models.py` | MemoryKind/Scope 枚举重定义，Memory dataclass 重构 |
| 新增 | `skills/insight/scripts/aggregate.py` | 代码聚合层：AggregateResult + aggregate() |
| 修改 | `skills/insight/scripts/cli.py` | CAPTURE/EVALUATE PROMPT 重写，evaluate 流程插入 aggregate |
| 修改 | `skills/insight/scripts/store.py` | Memory 读写方法适配新字段 + recall/promote 方法修复 |
| 新增 | `skills/insight/tests/test_aggregate.py` | aggregate 模块测试 |
| 修改 | `skills/insight/references/extraction-flow.md` | 反映三层 pipeline |
| 修改 | `skills/insight/references/insight-schema.md` | 反映新字段定义 |

### 任务步骤

#### Task 1: Memory 模型重构

**Files:**
- 修改: `skills/insight/scripts/models.py`

- [ ] **Step 1: 重定义 MemoryKind 枚举** (~2 min)
  - 从 correction/preference/workflow/decision/fact 改为 bug/decision/pattern/friction/workflow/other

- [ ] **Step 2: 重定义 Scope 枚举** (~2 min)
  - 从 project/user 改为 file/module/skill/agent/project/other

- [ ] **Step 3: 重构 Memory dataclass** (~3 min)
  - 删除 `context` 字段，新增 `source`、`evidence_ref`
  - `content` 改名为 `summary`
  - `source_session_id` 合并入 `source`（格式："session_id@runtime"）
  - 更新 `to_markdown()` 序列化：frontmatter 输出新字段名
  - 更新 `from_frontmatter()` 反序列化：解析 `summary`（原 `content`）、`source`（原 `source_session_id`）、`evidence_ref`（新增），删除对 `context` 的解析

- [ ] **Step 4: 验证** (~1 min)
  ```bash
  python -c "from scripts.models import Memory, MemoryKind, Scope; print('OK')"
  ```

#### Task 2: Store 层适配

> **注意**：Memory 存储在 `memories/` 目录下的 markdown 文件中（每条一个 `.md`），不是 SQLite 表。SQLite（`meta.db`）只存 `evidence_links`、`hit_logs`、`session_progress`。"删表重建" = 删除 `memories/` 目录下的旧 `.md` 文件。

**Files:**
- 修改: `skills/insight/scripts/store.py`

- [ ] **Step 1: 删除旧 Memory 文件** (~1 min)
  - 破坏性升级：旧 Memory markdown 文件字段不兼容，直接删除 `memories/` 目录下所有 `.md` 文件
  - 用户重新执行 `omp-insight capture` 重建

- [ ] **Step 2: 适配 Memory 读写方法** (~3 min)
  - `store_memory()` / `get_memory()` / `list_memories()` 依赖 `Memory.to_markdown()` / `Memory.from_frontmatter()`，Task 1 已更新这些方法，此处确认调用兼容
  - cursor 机制（`session_progress` 表）不变

- [ ] **Step 3: 修复 recall 输出方法** (~3 min)
  - `_recall_md()`：`mem.content` → `mem.summary`，删除对 `mem.context` 的引用
  - `_recall_json()`：`"content": mem.content` → `"summary": mem.summary`，`"context": mem.context` → 删除，新增 `"source": mem.source`、`"evidence_ref": mem.evidence_ref`

- [ ] **Step 4: 修复 promote() 方法** (~2 min)
  - `memory.content` → `memory.summary`
  - `memory.context` → 删除（action 改用 reason 参数或空字符串）

- [ ] **Step 5: 适配 get_store() 的 Scope 分流** (~2 min)
  - 旧逻辑：`Scope.USER` → global，`Scope.PROJECT` → project_id
  - 新 Scope 枚举有 6 个值（file/module/skill/agent/project/other）
  - 决策：所有 scope 都使用 project_id 存储，删除 `Scope.USER` 的特殊分流

- [ ] **Step 6: 验证** (~1 min)
  ```bash
  python -c "from scripts.store import InsightStore; s = InsightStore('test'); print('OK')"
  ```

#### Task 3: Aggregate 模块（TDD）

**Files:**
- 新增: `skills/insight/scripts/aggregate.py`
- 新增: `skills/insight/tests/test_aggregate.py`

- [ ] **Step 1: 写测试** (~5 min)
  ```python
  def test_aggregate_by_kind():
      # 构造已知 Memory 集合
      # 断言 by_kind 频次、avg_confidence、recent_7d

  def test_aggregate_by_scope():
      # 断言 by_scope 分布

  def test_aggregate_top_tags():
      # 断言 top_tags 排序正确

  def test_aggregate_samples():
      # 断言 samples_by_kind 每组最多 5 条

  def test_aggregate_empty():
      # 空 Memory 集合不报错
  ```

- [ ] **Step 2: 运行测试确认失败** (~1 min)
  ```bash
  pytest skills/insight/tests/test_aggregate.py -v
  # 预期：FAIL
  ```

- [ ] **Step 3: 实现 aggregate.py** (~5 min)
  - `AggregateResult` / `KindStats` dataclass 定义
  - `def aggregate(memories: list[Memory]) -> AggregateResult`（纯函数，输入 Memory 列表）
  - 调用方式：`aggregate(store.list_memories(limit=9999))`
  - 内部：`collections.Counter` + `datetime` 时间窗口计算，无外部依赖，不访问 SQLite

- [ ] **Step 4: 运行测试确认通过** (~1 min)
  ```bash
  pytest skills/insight/tests/test_aggregate.py -v
  # 预期：PASS
  ```

- [ ] **Step 5: 提交** (~1 min)
  ```bash
  git add skills/insight/scripts/aggregate.py skills/insight/tests/test_aggregate.py
  git commit -m "feat(insight): add deterministic aggregate layer"
  ```

#### Task 4: Capture/Evaluate Prompt 重写 + 流程改造

**Files:**
- 修改: `skills/insight/scripts/cli.py`

- [ ] **Step 1: 重写 CAPTURE_PROMPT** (~3 min)
  - 角色：复盘分析师
  - 输出：6 字段 JSON（kind/scope/summary/evidence_ref/confidence/tags）

- [ ] **Step 2: 重写 EVALUATE_PROMPT** (~3 min)
  - 角色：持续改进顾问
  - 输入：{aggregate_json} + {samples}
  - evidence 字段语义改为 kind 列表

- [ ] **Step 3: 改造 cmd_evaluate 流程** (~5 min)
  - 函数签名不变：`def cmd_evaluate(args: argparse.Namespace) -> int`
  - 关键逻辑：调用 `aggregate(store)` → 序列化为 JSON → 拼入 EVALUATE_PROMPT → 调用 LLM
  - 边界情况：Memory 为空时直接返回，不调用 LLM

- [ ] **Step 4: 验证 E2E** (~3 min)
  ```bash
  omp-insight capture --source . --dry-run
  omp-insight evaluate --source . --dry-run
  ```

- [ ] **Step 5: 提交** (~1 min)
  ```bash
  git add skills/insight/scripts/cli.py
  git commit -m "feat(insight): restructure capture/evaluate for v3 three-layer pipeline"
  ```

#### Task 5: 文档更新

**Files:**
- 修改: `skills/insight/references/extraction-flow.md`
- 修改: `skills/insight/references/insight-schema.md`

- [ ] **Step 1: 更新 extraction-flow.md** (~3 min)
  - 反映三层 pipeline（capture → aggregate → evaluate）
  - 更新数据流图

- [ ] **Step 2: 更新 insight-schema.md** (~3 min)
  - 反映新 Memory 字段定义（6 字段 + 可选字段）
  - 更新 kind/scope 枚举值

- [ ] **Step 3: 提交** (~1 min)
  ```bash
  git add skills/insight/references/
  git commit -m "docs(insight): update references for v3 three-layer pipeline"
  ```
