# Insight v2：Hook 自动化 + 遗忘机制

> 为 Insight skill 增加 Claude Code hook 集成（自动 capture/recall）和基于 time decay 的遗忘机制，同时建立 skill hooks 通用安装框架。

## 目录

- [设计方案](#设计方案)
  - [背景与目标](#背景与目标)
  - [架构](#架构)
  - [改动 1：Skill hooks 通用机制](#改动-1skill-hooks-通用机制)
  - [改动 2：Insight hook 声明](#改动-2insight-hook-声明)
  - [改动 3：Recall 排序加入 time decay](#改动-3recall-排序加入-time-decay)
  - [改动 4：新增代码测试](#改动-4新增代码测试)
  - [关键决策](#关键决策)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 背景与目标

Insight skill 在数据模型和多运行时支持上已经成熟（三层蒸馏、4 运行时 reader、SQLite + YAML 双存储），但存在两个核心缺陷：

1. **零自动化**：capture 和 recall 完全依赖手动 CLI，用户摩擦大，实际使用率低
2. **无遗忘机制**：记忆只增不减，recall 输出会随时间膨胀，低质量条目永远占位

参考项目 [fireworks-skill-memory](https://github.com/yizhiyanhua-ai/fireworks-skill-memory) 的 hook 驱动设计，但不照搬其实现——Insight 有更丰富的数据模型，需要保留自身优势。

**成功标准**：
- `omp install skill insight` 后，无需额外配置即可自动 capture/recall
- 陈旧记忆自然衰减，recall 输出始终保持在 token budget 内且优先返回高价值条目

### 架构

```
omp install skill insight
        │
        ▼
┌─────────────────────────────┐
│  omp CLI (bin/omp)          │
│  检测 hooks.json → 合并到   │
│  ~/.claude/settings.json    │
│  安全写入：backup → tmp →   │
│  edit → verify → copy back  │
└─────────────────────────────┘

会话运行时：

SessionStart hook (同步)
        │
        ▼
┌─────────────────────────────┐
│ omp-insight recall --format md │
│ → additionalContext 注入     │
│ → ## Insight Memory 命名空间 │
│ → 排序含 time decay          │
│ → 每条含元数据（confidence,  │
│   age, hit_count）           │
└─────────────────────────────┘

PostCompact hook (异步，主要)
        │
        ▼
┌─────────────────────────────┐
│ omp-insight capture          │
│ → 从 JSONL 增量提取记忆      │
│ → cursor 防重复              │
└─────────────────────────────┘

Stop hook (异步，兜底)
        │
        ▼
┌─────────────────────────────┐
│ omp-insight capture          │
│ → 仅在本次会话未触发过       │
│   PostCompact 时执行         │
│ → 覆盖短会话场景             │
└─────────────────────────────┘
```

### 改动 1：Skill hooks 通用机制

**新增约定**：skill 目录下可选 `hooks.json`，声明该 skill 需要的 Claude Code hooks。

```
skills/<name>/
├── SKILL.md
├── hooks.json    ← 新增，可选
├── scripts/
└── ...
```

**hooks.json 格式**（与 Claude Code settings.json 的 hooks 结构对齐）：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "omp-insight recall --source $PWD --format md",
            "timeout": 5000
          }
        ]
      }
    ],
    "PostCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "omp-insight capture --source $PWD --since 1d",
            "timeout": 30000,
            "async": true
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "omp-insight capture --source $PWD --since 1d --if-no-compact",
            "timeout": 30000,
            "async": true
          }
        ]
      }
    ]
  }
}
```

**omp install 逻辑变更**（`bin/omp` install 命令）：

```python
# 现有 symlink 逻辑之后新增：
hooks_json = src / "hooks.json"
if hooks_json.is_file():
    _install_hooks(hooks_json, name)
```

**`_install_hooks(hooks_json, name)` 实现要点**：

1. 读取 skill 的 hooks.json
2. 读取 `~/.claude/settings.json`（不存在则创建 `{}`）
3. 对每个 hook event（如 SessionStart），将 skill 的 hook 条目追加到 settings.json 对应数组
4. 每个注入的条目附带 `"_omp_skill": "<name>"` 标记，用于卸载时精准移除
5. 去重：如果同 skill 同 command 已存在，跳过
6. **安全写入流程**：
   - backup：复制 `settings.json` → `settings.json.bak`
   - cp to tmp：写入临时文件 `settings.json.tmp`
   - edit：在临时文件上完成合并
   - verify：`json.loads()` 验证临时文件是合法 JSON
   - copy back：验证通过后 `os.replace()` 原子替换
   - 失败时保留 `.bak`，报错并中止（不影响 skill symlink 安装）

**omp remove 逻辑变更**：

```python
# 现有 unlink 逻辑之后新增：
hooks_json = src / "hooks.json"
if hooks_json.is_file():
    _remove_hooks(name)
```

**`_remove_hooks(name)` 实现要点**：

1. 读取 `~/.claude/settings.json`
2. 遍历所有 hook event 数组，移除 `_omp_skill == name` 的条目
3. 清理空数组
4. 写回

### 改动 2：Insight hook 声明

新增 `skills/insight/hooks.json`：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "omp-insight recall --source $PWD --format md",
            "timeout": 5000
          }
        ]
      }
    ],
    "PostCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "omp-insight capture --source $PWD --since 1d",
            "timeout": 30000,
            "async": true
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "omp-insight capture --source $PWD --since 1d --if-no-compact",
            "timeout": 30000,
            "async": true
          }
        ]
      }
    ]
  }
}
```

**SessionStart hook 输出**：recall 结果通过 stdout JSON 注入 additionalContext，使用 `## Insight Memory` 命名空间隔离：

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "## Insight Memory\n\n- **pattern** → action [confidence:0.8 | age:2mo | hits:5]\n- ..."
  }
}
```

每条记忆附带源数据元信息（confidence、age、hit_count），帮助 LLM 判断可信度。

**PostCompact hook**（主要 capture 时机）：异步执行，不阻塞会话。compaction 意味着上下文即将丢失，是提取记忆的最佳时机。capture 自动检测项目、发现 session、增量提取。

**Stop hook**（capture 兜底）：异步执行。仅在本次会话未触发过 PostCompact 时执行（`--if-no-compact` 标志），覆盖短会话从未触发 compaction 的场景。通过锁文件或环境变量判断 PostCompact 是否已执行过。

### 改动 3：Recall 排序加入 time decay

修改 `skills/insight/scripts/store.py` 中的 recall 方法。

**当前排序**（仅 Memory，Insight 按 confidence）：
```python
score = hit_count * confidence
```

**改为**：
```python
from datetime import datetime

DECAY_GRACE_MONTHS = 3   # 宽限期：此期间内无衰减
DECAY_RATE = 0.5         # 每超出宽限期 1 个月的惩罚值

def _decay_score(hit_count: int, confidence: float, last_hit_at: datetime) -> float:
    """计算含 time decay 的排序分数。

    基于 last_hit_at（最后命中时间）而非 created_at，
    因为持续被引用的记忆不应衰减。
    """
    now = datetime.now()
    months = (now.year - last_hit_at.year) * 12 + (now.month - last_hit_at.month)
    age_penalty = max(0.0, (months - DECAY_GRACE_MONTHS) * DECAY_RATE)
    return hit_count * confidence - age_penalty
```

**关键设计决策**：使用 `last_hit_at` 而非 `created_at` 作为衰减基准。一条古老但持续被引用的记忆（last_hit_at 近期）不应被衰减惩罚，而一条新建但从未被引用的记忆应该自然下沉。

**应用范围**：
- Memory 排序：`_decay_score(m.hit_count, m.confidence, m.last_hit_at)`
- Insight 排序：`_decay_score(len(i.evidence), i.confidence, i.last_hit_at)`
  - Insight 的 "hit_count" 等价物是 evidence_count
  - `last_hit_at` 取最近一条 evidence 的时间戳

**效果示例**（月龄 = 距 last_hit_at 的月数）：

| 条目 | hits | confidence | 月龄 | 旧 score | 新 score |
|------|------|-----------|------|---------|---------|
| Memory A | 5 | 0.8 | 1 | 4.0 | 4.0（宽限期内，无衰减） |
| Memory B | 2 | 0.6 | 6 | 1.2 | -0.3（超宽限期 3 月，惩罚 1.5） |
| Memory C | 10 | 0.9 | 12 | 9.0 | 4.5（高频抵消衰减） |

### 改动 4：新增代码测试

只测新增代码：

1. **hooks 合并测试**（新文件 `tests/test_hooks.py`）
   - 合并到空 settings.json
   - 合并到已有 hooks 的 settings.json
   - 重复安装幂等性
   - 卸载精准移除（不影响其他 skill 的 hooks）
   - 卸载后清理空数组

2. **decay score 测试**（追加到 `skills/insight/tests/test_store.py`）
   - 3 个月内无衰减
   - 超过 3 个月线性衰减
   - 高频条目抵消衰减
   - 负分条目排在最末

### 关键决策

- **hooks.json 而非 install-hooks.sh**：声明式优于命令式。skill 作者只声明意图，框架负责合并/去重/卸载，多 skill hooks 可安全共存。
- **SessionStart 注入而非 PostToolUse**：Insight 是项目级记忆，不是 skill 级。会话开始时一次性注入比每次读 SKILL.md 时注入更合理。
- **PostCompact + Stop 兜底**：PostCompact 是主要 capture 时机（compaction = 上下文即将丢失），Stop 作为兜底覆盖短会话从未触发 compaction 的场景。通过 `--if-no-compact` 避免重复 capture。
- **`_omp_skill` 标记**：在 settings.json 的 hook 条目中附带来源标记，使卸载可以精准定位而非依赖 command 字符串匹配。
- **保留 5 种 memory kind**：不照搬 Fireworks 的 error-only gating。correction/preference/workflow/decision/fact 的多维度覆盖是 Insight 的设计优势。
- **recall 输出体积控制而非磁盘 eviction**：陈旧条目在 recall 排序中自然下沉被 budget 裁掉，但仍保留在磁盘上作为 evidence 和历史记录。
- **last_hit_at 而非 created_at 衰减**：持续被引用的古老记忆不应衰减，未被引用的新记忆应自然下沉。衰减惩罚基于"最后命中时间"更准确反映记忆价值。
- **安全写入 settings.json**：hooks 安装不应搞坏全局配置。采用 backup → tmp → edit → verify → copy back 流程，安装失败只影响自动化，不影响 skill 自身能力。
- **`## Insight Memory` 命名空间**：recall 输出以 markdown heading 隔离，多 skill 各自注入 additionalContext 时互不干扰。
- **每条记忆附带元数据**：recall 输出中每条记忆附带 confidence、age、hit_count，帮助 LLM 判断可信度并做出更好的决策。

---

## 行动原则

- **TDD: Red → Green → Refactor**：hooks 合并逻辑和 decay score 先写测试，再实现。**禁止：** 先写实现再补测试。
- **Break, Don't Bend**：直接修改 `omp install` 流程，不建兼容层。**禁止：** `--legacy` 模式或条件分支保留旧行为。
- **Explicit Contract**：hooks.json 格式与 Claude Code settings.json 结构对齐，`_omp_skill` 标记显式声明来源。**禁止：** 依赖 command 字符串隐式匹配来判断 hook 归属。
- **Minimum Blast Radius**：4 个改动独立提交，每个可独立 review 和回滚。**禁止：** 一个 PR 混合所有改动。
- **Fail at the Boundary**：hooks.json 解析失败时立即报错并中止安装，不静默跳过。**禁止：** 吞掉 JSON 解析错误继续 symlink。

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 修改 | `skills/insight/scripts/store.py` | recall 排序加入 `_decay_score`（基于 `last_hit_at`） |
| 修改 | `skills/insight/tests/test_store.py` | 追加 decay score 测试 |
| 修改 | `bin/omp` | install/remove 中增加 hooks.json 检测和安全合并/移除逻辑 |
| 新增 | `tests/test_hooks.py` | hooks 合并/移除的单元测试 |
| 新增 | `skills/insight/hooks.json` | Insight 的 hook 声明（SessionStart + PostCompact + Stop） |
| 修改 | `skills/insight/scripts/cli.py` | recall 命令输出 hookSpecificOutput JSON + `## Insight Memory` 命名空间 + 元数据 |
| 修改 | `skills/insight/SKILL.md` | 更新文档，说明 hook 自动化 |
| 修改 | `docs/specs/00_skills/README.md` | Skill 目录结构增加 hooks.json 说明 |

### 任务步骤

#### Task 1: Recall time decay

> 先实现 decay，因为 Task 2 的 hook 输出需要依赖 decay 排序后的结果。

**Files:**
- 修改: `skills/insight/scripts/store.py`
- 修改: `skills/insight/tests/test_store.py`

- [ ] **Step 1: 写 decay score 测试**

```python
def test_decay_score_no_penalty_within_grace_period():
    """DECAY_GRACE_MONTHS 内 score = hit_count * confidence"""

def test_decay_score_linear_penalty_after_grace():
    """6 个月时 penalty = (6 - DECAY_GRACE_MONTHS) * DECAY_RATE = 1.5"""

def test_decay_score_high_frequency_resists_decay():
    """高频条目即使老旧仍有正分"""

def test_decay_score_uses_last_hit_at_not_created_at():
    """验证衰减基于 last_hit_at 而非 created_at"""

def test_recall_order_with_decay():
    """recall 输出按 decay score 降序"""
```

- [ ] **Step 2: 运行测试确认失败**
- [ ] **Step 3: 实现 `_decay_score`（含 `DECAY_GRACE_MONTHS`、`DECAY_RATE` 常量）并修改 recall 排序**
- [ ] **Step 4: 运行测试确认通过**
- [ ] **Step 5: 提交**

```bash
git add skills/insight/scripts/store.py skills/insight/tests/test_store.py
git commit -m "feat(insight): add time decay to recall ranking"
```

#### Task 2: Skill hooks 通用机制（omp CLI）

**Files:**
- 修改: `bin/omp`
- 新增: `tests/test_hooks.py`

- [ ] **Step 1: 写 hooks 合并测试**

```python
def test_install_hooks_to_empty_settings():
    """合并到空 settings.json"""

def test_install_hooks_to_existing():
    """合并到已有 hooks 的 settings.json，不覆盖其他 skill"""

def test_install_hooks_idempotent():
    """重复安装同一 skill 不产生重复条目"""

def test_install_hooks_safe_write():
    """验证 backup → tmp → verify → copy back 流程"""

def test_install_hooks_abort_on_invalid_json():
    """hooks.json 格式错误时中止，不影响 settings.json"""

def test_remove_hooks_precise():
    """卸载只移除目标 skill 的 hooks"""

def test_remove_hooks_cleanup_empty():
    """卸载后清理空的 hook event 数组"""
```

- [ ] **Step 2: 运行测试确认失败**
- [ ] **Step 3: 实现 `_install_hooks`（含安全写入流程）和 `_remove_hooks`**
- [ ] **Step 4: 运行测试确认通过**
- [ ] **Step 5: 提交**

```bash
git add bin/omp tests/test_hooks.py
git commit -m "feat: add hooks.json support to omp install/remove"
```

#### Task 3: Insight hook 声明

**Files:**
- 新增: `skills/insight/hooks.json`
- 修改: `skills/insight/scripts/cli.py`

- [ ] **Step 1: 创建 hooks.json**（含 SessionStart、PostCompact、Stop 三个 hook）
- [ ] **Step 2: 修改 recall 命令，支持 hook 输出格式**

当检测到 hook 上下文（`--hook` 标志或环境变量），输出 `hookSpecificOutput` JSON：
- 使用 `## Insight Memory` 命名空间 heading
- 每条记忆附带元数据：`[confidence:0.8 | age:2mo | hits:5]`

- [ ] **Step 3: 实现 `--if-no-compact` 逻辑**

capture 命令增加 `--if-no-compact` 标志，检查本次会话是否已触发过 PostCompact（通过临时锁文件判断），若已触发则跳过。

- [ ] **Step 4: 手动验证**

```bash
omp install skill insight
cat ~/.claude/settings.json | python3 -m json.tool  # 确认 3 个 hooks 已注入
omp remove skill insight
cat ~/.claude/settings.json | python3 -m json.tool  # 确认 hooks 已移除
```

- [ ] **Step 5: 提交**

```bash
git add skills/insight/hooks.json skills/insight/scripts/cli.py
git commit -m "feat(insight): add hook declarations for auto capture/recall"
```

#### Task 4: 文档更新

**Files:**
- 修改: `skills/insight/SKILL.md`
- 修改: `docs/specs/00_skills/README.md`

- [ ] **Step 1: 更新 SKILL.md**

  增加"自动化"章节，说明 hooks 机制和安装后的行为。

- [ ] **Step 2: 更新 Skills 规范**

  Skill 目录结构增加 `hooks.json` 说明。

- [ ] **Step 3: 提交**

```bash
git add skills/insight/SKILL.md docs/specs/00_skills/README.md
git commit -m "docs: add hooks.json convention to skill spec and insight docs"
```
