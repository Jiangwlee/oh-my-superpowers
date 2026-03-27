# omp-insight v2 设计文档

> 基于三层记忆模型（raw → memory → insight）的 Agent 记忆系统重设计。

## 目录

- [背景与目标](#背景与目标)
- [三层记忆模型](#三层记忆模型)
- [数据结构](#数据结构)
- [CLI 命令](#cli-命令)
- [存储结构](#存储结构)
- [SQLite Schema](#sqlite-schema)
- [recall 行为](#recall-行为)
- [promote / degrade 语义](#promote--degrade-语义)
- [evaluate 机制](#evaluate-机制)
- [SKILL.md 设计](#skillmd-设计)
- [YAML Frontmatter 格式](#yaml-frontmatter-格式)
- [迁移策略](#迁移策略)
- [关键决策记录](#关键决策记录)
- [行动计划](#行动计划)

---

## 背景与目标

### 问题

v1 的 `omp-insight` 存在以下核心问题：

1. **没有 Memory 层** — `CorrectionTrajectory` 是临时中间产物，不持久化
2. **Insight 范围太窄** — 只覆盖"纠正"模式，缺少偏好、工作流、技术决策等
3. **缺少生命周期管理** — 没有 hit_count、evidence_count、衰减机制
4. **CLI 是给人设计的** — 但真正的用户是 Agent
5. **Memory 和 Insight 未区分** — 所有提取结果都叫"insight"，质量参差不齐

### 目标

构建一个三层记忆系统，让 Agent 能：
- **capture**：从对话中自动提取有价值的 memory
- **recall**：在 session 开始时加载 memory + insight，减少重复犯错
- **evaluate**：从 memory 中提炼极少的、高价值的 insight

### 成功标准

- Memory 覆盖 5 种类型（correction/preference/workflow/decision/fact）
- Insight 数量极少（不超过一屏，约 10-20 条）
- recall 输出可直接注入 system prompt
- evaluate 幂等，多次运行结果一致

---

## 三层记忆模型

```
raw (对话原文)
  ↓ capture（LLM 提取，正则做 hint）
memory (重要事件，带 hit_count/confidence)
  ↓ evaluate（低频，cron / 手动，从 memory 聚类提炼）
insight (极少的高价值模式，如同 CLAUDE.md 条目)
  ↓ 衰减：长期无引用/验证 → confidence 下降
```

### 核心区分

| 维度 | Memory | Insight |
|------|--------|---------|
| 本质 | 事实记录（被动记录的观察） | 聚合知识（主动提炼的模式） |
| 数量 | 多（数百条） | 极少（不超过一屏） |
| 生成频率 | 高频（每次 session 结束） | 低频（每日 cron / 手动） |
| 生命周期 | 创建后不可变 | 可编辑、可降级 |
| 加载策略 | 按 hit_count 排序，预算内填充 | 全量加载 |
| 类比 | 笔记本里的笔记 | 贴在显示器上的便签 |

---

## 数据结构

### Memory

```python
class MemoryKind(str, Enum):
    """Memory 的类别。"""
    CORRECTION = "correction"      # 用户纠正了错误行为
    PREFERENCE = "preference"      # 用户偏好
    WORKFLOW = "workflow"           # 工作流程/协作方式
    DECISION = "decision"          # 技术/产品决策
    FACT = "fact"                   # 项目/环境事实


class Scope(str, Enum):
    """作用域。"""
    PROJECT = "project"
    USER = "user"


@dataclass
class Memory:
    """一条记忆。被动记录的事实，创建后不可变。"""
    id: str                        # mem_{hex_timestamp}_{random4}
    kind: MemoryKind
    content: str                   # 一句话描述这条记忆
    context: str                   # 发生的上下文（触发场景）
    scope: Scope
    source_session_id: str
    created_at: datetime
    hit_count: int = 0             # recall 命中次数
    confidence: float = 0.5        # LLM 提取时的置信度
    tags: list[str] = field(default_factory=list)
```

### Insight

```python
@dataclass
class Insight:
    """一条洞察。主动提炼的模式，值得每个 session 优先加载。"""
    id: str                        # ins_{hex_timestamp}_{random4}
    pattern: str                   # 一句话描述这个模式
    action: str                    # Agent 应该怎么做
    evidence: list[str]            # 关联的 memory IDs
    scope: Scope
    created_at: datetime
    last_validated_at: datetime    # 最近一次被证据支撑
    evidence_count: int = 0        # 支撑证据的数量
    confidence: float = 0.6        # 初始置信度，需要更高门槛
    tags: list[str] = field(default_factory=list)
```

### ID 生成规则

```
格式: {type}_{hex_timestamp}_{random4}
示例: mem_6605a3c0_f2a1
      ins_6605a3c0_b7e3

- type: mem | ins（一眼区分类型）
- hex_timestamp: Unix 时间戳的十六进制（保证排序）
- random4: 4 位十六进制随机数（防碰撞）
```

---

## CLI 命令

### 总览（7 个命令，三组受众）

```bash
# Agent 热路径（SKILL.md 里写这两个）
omp-insight capture --source <dir> [--session <id>]    # 从对话提取 memory
omp-insight recall  --source <dir> [--format json|md]  # 召回 memory + insight
                    [--budget <tokens>] [--dry-run]

# 后台冷路径（cron / 手动，idempotent）
omp-insight evaluate --source <dir> [--dry-run]        # memory → insight 候选评估
                     [--prompt-file <path>]

# 用户查看 + 干预
omp-insight list    --source <dir> [--type memory|insight]
omp-insight promote <id> [--reason <text>]             # memory → insight
omp-insight degrade <id> [--reason <text>]             # 归档 insight
omp-insight delete  <id>
```

### 参数约定

- `--source`：默认 `detect_project(os.getcwd()).root`。不在项目目录下时报错并提示 `--source` 期望格式。
- `--format`：recall 默认 `md`（Agent 读自然语言），`json` 给程序集成。
- `--budget`：recall 的 token 预算，默认 4096。
- `--dry-run`：recall 和 evaluate 均支持，用于调试和预览。
- `--prompt-file`：evaluate 的 prompt 模板路径，支持版本化迭代。

### 命令详述

#### capture

```bash
omp-insight capture --source /path/to/project [--session abc123]
```

从最近的对话中提取 memory。流程：
1. 扫描 `--source` 目录对应的对话历史（Claude/Codex/Pi/OpenClaw）
2. LLM 分析对话，提取 Memory（正则做 hint 预筛，LLM 精筛）
3. 去重（content 语义相似度检查）
4. 写入 `memories/` 目录

#### recall

```bash
omp-insight recall --source /path/to/project --budget 4096 --format md
```

输出当前项目的 memory + insight，供注入 system prompt。流程：
1. 加载全部 insight（pattern + action，通常很短）
2. 剩余预算按 `hit_count * confidence` 降序填充 memory
3. 超出预算截断
4. 更新 hit_logs

#### evaluate

```bash
omp-insight evaluate --source /path/to/project --dry-run
```

从 memory 中提炼 insight 候选。流程：
1. 扫描所有 active memory
2. 按语义聚类
3. 检查聚类内的 hit_count 分布、跨 session 覆盖度
4. LLM 提炼候选 insight（pattern + action）
5. `--dry-run` 时只输出候选列表，不写入

**幂等性**：多次运行不产生重复 insight。通过 evidence 集合的内容 hash 去重。

---

## 存储结构

```
~/.local/share/oh-my-superpowers/insight/
├── <project-hash>/
│   ├── memories/              # 每条一个 markdown（YAML frontmatter）
│   │   └── mem_6605a3c0_f2a1.md
│   ├── insights/              # 每条一个 markdown（YAML frontmatter）
│   │   └── ins_6605a3c0_b7e3.md
│   └── meta.db                # SQLite：evidence_links, hit_logs
└── global/
    ├── memories/
    ├── insights/
    └── meta.db
```

---

## SQLite Schema

```sql
-- evidence_links: insight → memory 的多对多关系
CREATE TABLE evidence_links (
    insight_id TEXT NOT NULL,
    memory_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (insight_id, memory_id)
);

-- hit_logs: recall 命中日志（用于统计 hit_count）
CREATE TABLE hit_logs (
    item_id TEXT NOT NULL,
    item_type TEXT NOT NULL,     -- 'memory' | 'insight'
    session_id TEXT,
    timestamp INTEGER NOT NULL
);

-- 索引
CREATE INDEX idx_hit_item ON hit_logs(item_id);
CREATE INDEX idx_hit_timestamp ON hit_logs(timestamp);
```

---

## recall 行为

```
recall(budget=4096):
  1. 加载全部 insight（全量，pattern + action 通常很短）
  2. 计算剩余预算 = budget - insight_tokens
  3. 按 hit_count * confidence 降序排列 memory
  4. 逐条填充，超出预算截断
  5. 记录 hit_logs
  6. 输出格式：markdown（默认）或 JSON
```

### 输出示例（markdown）

```markdown
## Insights

- **禁止相对路径调用**: 编写 skill 脚本时，始终通过 omp-<skill> 入口调用
- **测试优先**: 修改核心模块前先写 T1 测试覆盖

## Memories

- [correction] 用户纠正：不要在 SKILL.md 中写 bash scripts/foo.sh
- [preference] 用户偏好 Google 风格 docstring
- [workflow] 用户要求 BrainStorm → Plan → Code → Review 流程
```

---

## promote / degrade 语义

### promote

```
promote(memory_id, reason?):
  1. memory 保留不动（它是证据）
  2. 创建新 Insight:
     - pattern: 从 memory.content 提炼
     - action: 从 memory.context 推导
     - evidence: [memory_id]
  3. 写入 evidence_links
  4. 如果已有相关 insight，追加 evidence 而非创建新的
```

### degrade

```
degrade(insight_id, reason?):
  1. 删除 insight 文件
  2. 删除 evidence_links 中该 insight 的记录
  3. evidence 中的 memory 保留不动
  4. 不做 "insight → memory" 的伪转换
```

### 设计原则

- Memory 是事实层证据，永远不因 promote/degrade 而消失
- Insight 是结论层，可以被创建和销毁
- promote 不是"升级"，是"从证据中结晶"
- degrade 不是"降级"，是"承认结论不再成立"

---

## evaluate 机制

### 触发方式

- **cron**（推荐）：每日一次，`omp-insight evaluate --source <dir>`
- **手动**：用户主动运行
- **事件驱动**（可选）：当新增 N 条未被 insight 覆盖的 memory 时触发

### 流程

```
evaluate(source_dir, prompt_file?):
  1. 扫描 memories/ 下所有 active memory
  2. 按 content 语义聚类（相似 memory 归组）
  3. 对每个聚类检查：
     - hit_count 总和 > 阈值？
     - 跨 session 数量 > 1？
     - 是否已有 insight 覆盖？
  4. 对候选聚类调用 LLM 提炼 insight:
     - 输入：聚类内所有 memory
     - 输出：pattern + action
     - prompt 来自 --prompt-file（可版本化）
  5. 去重：evidence 集合 hash 与已有 insight 比对
  6. 写入 insights/ 和 evidence_links
```

### 幂等性保证

- 相同 memory 集合不会产生重复 insight
- 已被 insight 覆盖的 memory 不再参与候选
- `--dry-run` 只输出候选列表，不写入

---

## SKILL.md 设计

SKILL.md 核心只写两件事：**何时使用** 和 **如何使用**。

### 何时使用（触发条件）

**capture（记住）**：
- session 结束时（session hook 自动触发）
- 用户明确说"记住这个"
- 用户反复纠正同一类错误
- 用户表达了稳定偏好或工作流要求

**recall（想起）**：
- session 开始时（自动注入 system prompt）
- 开始新任务前，检查是否有历史偏好或约束

### 如何使用（Agent 接口）

```bash
# 记住：从当前 session 提取有价值的记忆
omp-insight capture --source .

# 想起：获取当前项目的记忆和洞察
omp-insight recall --source . --format md --budget 4096
```

---

## YAML Frontmatter 格式

### Memory

```yaml
---
id: mem_6605a3c0_f2a1
kind: correction
content: "禁止在 SKILL.md 中用相对路径调用脚本"
context: "用户在 review skill 时反复纠正此问题"
scope: project
source_session_id: "session_abc123"
created_at: "2026-03-27T18:00:00"
hit_count: 5
confidence: 0.7
tags: ["skill", "code-style"]
---
```

### Insight

```yaml
---
id: ins_6605a3c0_b7e3
pattern: "用户要求所有脚本必须 CLI 化，禁止相对路径调用"
action: "编写 skill 脚本时，始终通过 omp-<skill> 入口调用，不写相对路径"
evidence: ["mem_6605a3c0_f2a1", "mem_6605b100_c3d2"]
scope: project
created_at: "2026-03-27T18:00:00"
last_validated_at: "2026-03-27T18:00:00"
evidence_count: 2
confidence: 0.8
tags: ["skill", "code-style"]
---
```

---

## 迁移策略

### 原则

- 旧 Insight 全部降级为 Memory（confidence 0.5）
- 跑一次 `evaluate` 重新筛选哪些值得成为 Insight
- 不尝试"智能重建历史"，能保真就保真

### 步骤

1. **备份**：`cp -r ~/.local/share/oh-my-superpowers/insight/ ~/.local/share/oh-my-superpowers/insight.bak/`
2. **转换**：运行 `scripts/migrate_v1.py`
   - 每条旧 Insight → 新 Memory（kind=CORRECTION，content=corrected_behavior，context=trigger）
   - 标记 `tags: ["migrated_v1"]`
3. **验证**：`omp-insight list --type memory` 确认转换结果
4. **重建**：`omp-insight evaluate --dry-run` 预览候选 insight
5. **确认**：`omp-insight evaluate` 执行提炼

### 迁移脚本

一次性脚本，放在 `skills/insight/scripts/migrate_v1.py`，不做成 CLI 子命令。

---

## 关键决策记录

> 来自 Round Table 讨论（session 20260327T170648，11 轮，4 位参与者）

| # | 决策 | 理由 | 投票 |
|---|------|------|------|
| 1 | Memory 和 Insight 是两个独立类型 | Memory 是事实（不可变），Insight 是聚合知识（可编辑）。不同物种不应统一 | Jobs+Linus+Karpathy 支持，Musk 倾向统一但接受 |
| 2 | promote 保留 memory，创建 insight | 证据层不应因操作而消失 | 4/4 全票 |
| 3 | degrade 删除 insight，不做伪转换 | insight 不是 memory 的同构变体 | 4/4 全票 |
| 4 | recall 预算默认 4096 token | insight 全量优先，memory 按 hit_count*confidence 填充 | 4/4 通过（Musk/Jobs 有微调建议） |
| 5 | --source 默认 detect_project(cwd) | 非项目目录报错，不猜测 | 3/4（Linus 倾向 pwd fallback） |
| 6 | evaluate 支持 --prompt-file | prompt 是最大质量风险，必须可版本化 | Karpathy 提出，全员认可 |
| 7 | 砍掉动态置信度计算 | 增加复杂度，简单字段存储即可 | 用户决策 |
| 8 | 砍掉审计日志 | 过度工程 | 用户决策 |
| 9 | MemoryKind 扩展为 5 种 | correction/preference/workflow/decision/fact | 4/4 一致 |
| 10 | ID 格式 `{type}_{hex_ts}_{rand4}` | 可读、可排序、可 grep、防碰撞 | 4/4 全票 |

### 参与者

| 角色 | Runtime | 核心贡献 |
|------|---------|---------|
| Steve Jobs（产品视觉家） | Claude/Opus | Memory/Insight 分离哲学、pin/unpin 隐喻、recall 默认 md |
| Elon Musk（第一性原理工程） | Codex/GPT-5.4 | promote/degrade 物理语义、recall 预算概念、最小闭环 |
| Linus Torvalds（务实开发者） | Pi/Qwen3.5-27B | 数据结构驱动设计、SQLite schema、ID 生成、幂等性 |
| Andrej Karpathy（AI 系统工程师） | Claude/Sonnet | evaluate prompt 版本化、LLM 系统容错、eval 机制 |

---

## 行动计划

### Phase 1: 数据层（破坏性升级）

- [ ] 新建 `Memory` 和 `Insight` dataclass（替换旧 `CorrectionTrajectory` + `Insight`）
- [ ] 新建 SQLite schema（evidence_links + hit_logs）
- [ ] 实现 ID 生成函数
- [ ] 实现 YAML frontmatter 序列化/反序列化
- [ ] 编写迁移脚本 `migrate_v1.py`
- [ ] T1 测试覆盖：schema 创建、ID 生成、序列化

### Phase 2: CLI 重写

- [ ] 重写 `capture` 命令（LLM 提取 → Memory）
- [ ] 重写 `recall` 命令（预算机制 + hit_logs）
- [ ] 新增 `evaluate` 命令（memory 聚类 → insight 候选）
- [ ] 重写 `list` 命令（支持 --type 过滤）
- [ ] 新增 `promote` / `degrade` / `delete` 命令
- [ ] `--source` 默认值逻辑
- [ ] T1 测试覆盖：各命令基本流程

### Phase 3: Prompt 与质量

- [ ] 重写 capture prompt（5 种 MemoryKind 识别）
- [ ] 编写 evaluate prompt（memory 聚类 → insight 提炼）
- [ ] 实现 `--prompt-file` 参数
- [ ] 去重机制（content 语义相似度）
- [ ] evaluate 幂等性测试

### Phase 4: SKILL.md 与集成

- [ ] 重写 SKILL.md（capture + recall 两个动词）
- [ ] Session hook 集成（session 结束自动 capture）
- [ ] Cron 集成文档（evaluate 定时运行）
