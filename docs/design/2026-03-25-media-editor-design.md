# media-editor Agent

> AI 领域媒体编辑 Agent：自主探索 X.com / Reddit，增量归档，生成结构化报告，随时间学习用户偏好。

## 目录

- [设计方案](#设计方案)
  - [背景与目标](#背景与目标)
  - [架构](#架构)
  - [存储结构](#存储结构)
  - [关键决策](#关键决策)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 背景与目标

AI 领域信息爆炸，用户需要每天在 X.com / Reddit 处理数百条内容，手动筛选耗时且容易形成信息茧房。

**目标：** 一个有编辑判断力的 Agent，能自主探索社交媒体、筛选高价值内容、增量归档、生成多种形式的结构化报告，并随时间学习用户偏好。

**成功标准：**
- 每次 daily-brief 调用，Agent 自主完成「多轮搜索 → 阅读 500+ → 推荐 100 条（X+Reddit 各 50）」，无需用户干预
- 增量采集，同天多次调用不重复
- 知识树自动生长，用户可观测各分类关注分布
- 语义检索可用（QMD），支持话题深挖

---

### 架构

```
用户指令
    ↓
media-editor Agent（编辑判断层）
    ├── chrome-cdp skill     ← 网页访问（搜索 / 阅读 / 推荐流）
    ├── media-editor skill   ← 数据层（存档 / 检索 / 晋升）
    ├── qmd CLI              ← 语义检索（BM25 + 向量 + 重排）
    └── bash / read / write  ← 报告输出、文件管理

~/.local/share/oh-my-superpowers/media-editor/   ← 数据根（仓库外）
```

**4 种调用模式（Agent 自动识别意图）：**

| 用户说 | 模式 | Agent 行为 |
|--------|------|-----------|
| 「给我简报」 | `daily-brief` | 增量抓取 → 阅读 500+ → 推荐 100 条 → 写报告 |
| 「读一下这个链接」 | `article-summary` | 阅读单篇 → 结构化摘要 → 提炼偏好 |
| 「深挖 X 话题」 | `topic-deep-dive` | QMD 语义检索 + 聚合近期相关 → 趋势分析 |
| （自动触发）| `pref-update` | 偏好画像变更说明，附于 article-summary 末尾 |

**daily-brief 执行循环：**

```
读取 preferences.json → last_fetch_time
→ 多轮迭代搜索（覆盖 6 个 L1 分类 + 人物关键词）
→ 抓取 X.com/explore 推荐流 + Reddit 首页 / 各板块热帖
→ 阅读 500+ 条（标题 / 摘要 / 转发数 / 评论数）
→ 编辑筛选：热推优先 + 随机小众内容补充，避免茧房
→ omp-media-save（写 daily JSONL + SQLite + markdown card）
→ 更新 taxonomy.json（新 L2+ 节点）
→ 输出 reports/YYYY-MM-DDTHH-mm-daily.md
→ 更新 last_fetch_time
```

---

### 存储结构

```
~/.local/share/oh-my-superpowers/media-editor/
├── archive/
│   ├── root-archive.jsonl          ← 长期精选（用户主动阅读后晋升）
│   └── daily/
│       ├── 2026-03-25.jsonl        ← 当天 100 条选中记录
│       └── YYYY-MM-DD.jsonl        ← 每天一文件
├── cards/
│   └── YYYY-MM-DD/
│       └── <slug>.md               ← QMD 索引源（每条选中条目的 markdown 卡片）
├── stats/
│   └── daily-stats.jsonl           ← 每次调用汇总（counts_by_category, total_read）
├── index.db                        ← SQLite（FTS5 结构化检索）
├── taxonomy.json                   ← 知识树（L1 固定 / L2+ 自动生长）
├── preferences.json                ← 用户偏好画像 + last_fetch_time
└── reports/
    ├── 2026-03-25T14-30-daily.md
    ├── 2026-03-25T14-30-summary-<slug>.md
    └── 2026-03-25T14-30-topic-<slug>.md
```

**archive 条目 schema（JSONL 每行）：**

```json
{
  "url": "https://...",
  "title": "标题",
  "source": "x.com | reddit.com",
  "fetch_time": "2026-03-25T14:30:00Z",
  "tags": { "L1": "Claude Code", "L2": "MCP工具" },
  "engagement": { "retweets": 1200, "comments": 340 },
  "summary": "20字以内摘要",
  "selected": true
}
```

**taxonomy.json 结构：**

```json
{
  "LLM": { "本地部署": {}, "训练微调": {}, "推理优化": {} },
  "AI Agent": { "多智能体": {}, "记忆系统": {} },
  "Claude Code": {},
  "CodeX": {},
  "Vibe Coding": {},
  "AI Application": {}
}
```

L1 节点用户锁定，Agent 不得新增或删除。L2+ 由 Agent 自主生长。

**双轨检索：**

| 查询类型 | 工具 | 示例 |
|---------|------|------|
| 结构化过滤 | SQLite FTS5 | 按日期、L1 分类、来源过滤 |
| 语义检索 | QMD（BM25 + 向量）| 「找关于 agent memory 的内容」 |

QMD 索引 `cards/` 目录（markdown 卡片）和 `reports/` 目录。

---

### 关键决策

- **增量边界**：以 `preferences.json` 中的 `last_fetch_time` 为基准，按发帖时间过滤新内容。距上次超过 24 小时时自动降级为全量扫描。

- **存档晋升规则**：`daily/` 存放当天选中条目（原始记录）；用户主动调用 `article-summary` 时，该条目从 daily 晋升至 `root-archive.jsonl`（URL 去重），同时触发偏好更新。`daily-brief` 不触发偏好更新，避免噪音。

- **knowledge tree 生长规则**：Agent 遇到无法归入现有 L2 节点的内容时，自主在对应 L1 下新建节点并写入 `taxonomy.json`。每次调用结束后输出「本次新增分类节点」日志。

- **报告文件命名**：`YYYY-MM-DDTHH-mm-<type>[-slug].md`，同天多次调用不覆盖。

- **数据不入 git**：`~/.local/share/oh-my-superpowers/` 完全在仓库外，无需 `.gitignore`。

- **QMD 依赖声明**：Agent 在 `agents.json` 中通过 description 注明依赖 `qmd` CLI，首次运行时 Agent 检查 `qmd --version` 是否可用，不可用时给出安装指引。

- **media-editor Skill 的职责**：存档读写复杂度（JSONL + SQLite + markdown card 三写同步）足以独立为 Skill，CLI 化后 Agent prompt 保持干净，且 Skill 可独立测试（T1）。

---

## 行动原则

- **TDD: Red → Green → Refactor**：先写失败测试再写实现。**禁止：** 无测试的功能提交。

- **Break, Don't Bend（断裂优于弯曲）**：接口设计错误时直接修正，不建兼容层。**禁止：** `deprecated`、`legacy`、`v1/v2` 等兼容性标记。

- **Zero-Context Entry（零上下文入口）**：每个文件前 20 行让读者无需外部知识即可理解职责。**禁止：** Agent 文件无角色说明；脚本无入口注释。

- **Explicit Contract（显式契约）**：archive schema、CLI 参数、模式触发条件必须在代码和文档中明确声明。**禁止：** 魔法默认值；未声明的副作用。

- **Minimum Blast Radius（最小影响半径）**：每次提交只解决一个明确问题。**禁止：** Agent 文件和 Skill 在同一 PR 混合提交（除非强依赖）。

- **First Principles over Analogy（第一性原理）**：QMD + SQLite 双轨的选择基于实际查询场景，而非「通常用 Elasticsearch」。**禁止：** 引入未经验证的架构层。

- **Incremental over Batch** `[任务专属]`：优先增量采集，full-scan 仅在时间窗口超限（>24h）或用户显式要求时触发。**禁止：** 默认每次全量重扫。

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `skills/media-editor/SKILL.md` | 数据层 CLI 文档 |
| 新增 | `skills/media-editor/scripts/init.py` | 初始化数据目录 + SQLite schema |
| 新增 | `skills/media-editor/scripts/save.py` | 写 JSONL + SQLite + markdown card |
| 新增 | `skills/media-editor/scripts/query.py` | SQLite 结构化查询 |
| 新增 | `skills/media-editor/scripts/promote.py` | daily → root-archive 晋升 |
| 新增 | `skills/media-editor/tests/test_static.py` | T1 静态检查 |
| 新增 | `agents/media-editor.md` | Agent 本体（Pi frontmatter + system prompt）|
| 修改 | `agents/agents.json` | 注册 media-editor agent + skill 依赖 |

---

### 前置检查

- [ ] 确认 `chrome-cdp` skill 已存在（`ls skills/chrome-cdp/SKILL.md`）。若不存在，需先开发或安装该 skill，本计划所有任务均依赖它。

---

### Task 1：media-editor Skill（数据层）

**Files:**
- 新增: `skills/media-editor/SKILL.md`
- 新增: `skills/media-editor/scripts/init.py`
- 新增: `skills/media-editor/scripts/save.py`
- 新增: `skills/media-editor/scripts/query.py`
- 新增: `skills/media-editor/scripts/promote.py`
- 新增: `skills/media-editor/tests/test_static.py`

- [ ] **Step 1: 写失败测试（T1 静态检查）**

```python
# tests/test_static.py
# - SKILL.md 存在且无相对路径脚本调用
# - 所有脚本有类型注解和 Google Docstring
# - CLI 入口可用（--help 不报错）
```

- [ ] **Step 2: 运行测试确认失败**

```bash
omp test skill media-editor
# 预期：FAIL（文件不存在）
```

- [ ] **Step 3: 实现 init.py**

创建数据目录结构 + SQLite schema（FTS5 表 `items`，字段：url, title, source, fetch_time, tags, summary）。

```bash
omp-media-init
# ~/.local/share/oh-my-superpowers/media-editor/ 初始化完成
```

- [ ] **Step 4: 实现 save.py**

原子写入：JSONL append → SQLite insert → markdown card write（三步，任一失败回滚已写内容）。
回滚策略：JSONL 写入使用「写临时文件 + atomic rename」保证原子性；SQLite 使用事务（BEGIN / COMMIT / ROLLBACK）；任意步骤异常时撤销已完成步骤。

```bash
omp-media-save --json '{"url":...}'
```

- [ ] **Step 5: 实现 query.py**

支持 `--l1 <category>`、`--date <YYYY-MM-DD>`、`--source <x.com|reddit.com>`、`--limit <n>` 参数。

```bash
omp-media-query --l1 "Claude Code" --date 2026-03-25 --limit 10
```

- [ ] **Step 6: 实现 promote.py**

从 daily JSONL 读取指定 URL，写入 root-archive.jsonl（URL 去重），更新 preferences.json。

```bash
omp-media-promote --url "https://..."
```

- [ ] **Step 7: 运行测试确认通过**

```bash
omp test skill media-editor
# 预期：PASS
```

- [ ] **Step 8: 提交**

```bash
git add skills/media-editor/
git commit -m "feat: add media-editor skill (data layer)"
```

---

### Task 2：media-editor Agent

**Files:**
- 新增: `agents/media-editor.md`
- 修改: `agents/agents.json`

- [ ] **Step 1: 写 agents/media-editor.md**

Pi frontmatter：
```yaml
name: media-editor
description: >-
  Use when: 用户要求生成 AI 领域简报、阅读某个社交媒体链接、深挖某个 AI 话题、
  或查看偏好更新报告。
  Do NOT use when: 与 AI 媒体内容无关的任务。
tools: bash, read, write
model: claude-sonnet-4-6
```

System prompt 核心章节：
- Role（AI 媒体编辑身份声明）
- Variables（OMP_HOME、DATA_DIR、依赖检查）
- Input（4 种模式识别规则）
- Workflow（每种模式的执行步骤）
- Output Format（各模式报告模板）
- Done Criteria

- [ ] **Step 2: 更新 agents/agents.json**

```json
"media-editor": {
  "agent": "@agents/media-editor.md",
  "model": "claude-sonnet-4-6",
  "skills": [
    "@skills/media-editor/SKILL.md",
    "@skills/chrome-cdp/SKILL.md"
  ]
}
```

- [ ] **Step 3: 提交**

```bash
git add agents/media-editor.md agents/agents.json
git commit -m "feat: add media-editor agent"
```

---

### Task 3：文档更新

**Files:**
- 修改: `CLAUDE.md`（项目结构部分新增 media-editor 条目）

- [ ] **Step 1: 更新 CLAUDE.md 项目结构图**

在 `agents/` 下补充 `media-editor.md` 条目，在 `skills/` 下补充 `media-editor/` 条目。

- [ ] **Step 2: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for media-editor agent"
```
