# Evolution Skill 设计文档

> 基于实证数据驱动项目 skills 和 CLAUDE.md 的持续演进。

## 背景

来自对文章《从执行走向思考》的讨论。三把刀审计（独立性、一致性、完备性）发现了规则体系的重复、冲突和盲区。审计过程有效但手动成本高，且缺乏实证数据支撑。evolution skill 将审计流程工具化，用真实 session 数据驱动演进。

### 与社区 autoresearch 方案的区别

社区（uditgoenka/autoresearch、Balu Kosuri 通用 skill、GEPA 等）采用合成评估：自定义 eval 标准 + 自主循环。evolution 采用实证评估：真实 session 数据 + 人在回路。

| 维度 | 社区方案 | evolution |
|------|---------|-----------|
| 数据源 | 合成测试用例 | 真实 session JSONL + memory feedback |
| 触发 | 自主循环（overnight） | 手动触发 |
| 范围 | 单 artifact | 全项目扫描，逐条修复 |
| 决策 | 自动 keep/discard | 人确认 |

## Skill 元数据

```yaml
---
name: evolution
description: >-
  Evolve project skills and CLAUDE.md based on real usage data.
  Use when you want to audit and improve skills in the current project
  using cross-project session analysis, user feedback from memories,
  and rule consistency checks.
  Do NOT use for one-off skill fixes or new skill creation.
---
```

**设计模式**：Pipeline

## 目录结构

```
skills/evolution/
├── SKILL.md                  # Pipeline 流程 + CLI 文档
├── scripts/
│   └── omp-evolution         # CLI 入口（scan/history 子命令）
├── references/
│   ├── README.md             # 索引
│   ├── evidence-sources.md   # 数据源定义：session JSONL、memory、CLAUDE.md
│   ├── mutation-operators.md # 6 种具名变异算子 + 证据→算子映射
│   └── guard-checks.md       # 修改后的 guard 检查项
└── tests/
    └── t1_static.sh
```

## 状态管理

状态全部持久化到磁盘，不依赖对话记忆。

### 全局数据

```
~/.local/share/oh-my-superpowers/evolution/
└── state.json              # 扫描游标
```

state.json 结构：

```json
{
  "cursors": {
    "/home/bruce/Projects/oh-my-superpowers": {
      "last_scan_time": "2026-03-29T12:00:00Z",
      "scanned_sessions": ["uuid1", "uuid2"]
    }
  }
}
```

### 项目数据

```
~/.local/share/oh-my-superpowers/evolution/projects/
└── <project-basename>/
    ├── results.tsv         # 演进历史日志
    └── last-scan.json      # 最近一次扫描结果缓存
```

results.tsv 格式：

```
date	commit	target	operator	status	description
2026-03-29	a1b2c3d	skills/round-table	tighten-description	keep	收紧 description 边界，减少误触发
2026-03-29	b2c3d4e	CLAUDE.md	remove-redundancy	keep	删除与 specs 重复的 IRON RULES
```

设计决策：
- `scanned_sessions` 记录已扫描的 session UUID，避免重复处理
- `results.tsv` 不提交到 git，保留在本地作为演进记忆
- `last-scan.json` 缓存扫描结果，避免逐条讨论时重复��描
- 项目标识用目录 basename，简单可读

## Pipeline 流程

### 阶段一：扫描

1. 运行 `omp-evolution scan`，获取机械信号 + session 样本
2. 读取 `references/evidence-sources.md`，理解数据含义
3. 读取 `references/mutation-operators.md`，理解算子映射
4. 对 session 样本做语义分析（误触发、重试、纠正）
5. 综合机械信号 + 语义分析，生成发现表格
6. 呈现给用户，等待用户选择修复项

发现表格格式：

```
| # | 目标 | 类型 | 证据 | 建议算子 | 优先级 |
|---|------|------|------|---------|--------|
| 1 | CLAUDE.md | 规则重复 | IRON RULE #3 与 S6 完全重复 | remove-redundancy | 高 |
| 2 | skills/insight | 低使用率 | 30天2次调用，feedback 中有3条纠正 | tighten-description | 中 |
```

### 阶段二：修复（每条一个循环）

1. 用户选择一条 + 确认或覆盖算子
2. 记录基线 commit hash
3. 应用变异算子，生成修改
4. 呈现 diff，等待用户确认
5. 用户确认 → 运行 guard 检查
   - 机械 guard：`omp test skill <name>`
   - 语义 guard：对比修改前后 description 覆盖范围
6. guard 通过 → 提交，追加 results.tsv
7. guard 失败或用户拒绝 → git revert，追加 results.tsv（status=discard）
8. 回到发现表格，选下一条

**Hard Gate：** 每一步修改都必须经用户确认才执行。不允许批量自动修复。

## 扫描输出（omp-evolution scan）

脚本输出分两段，机械信号 + session 样本：

```json
{
  "mechanical": [
    {"skill": "insight", "signal": "low_usage", "value": "2 calls / 30 days"},
    {"skill": "round-table", "signal": "skill_md_too_long", "value": "623 lines"},
    {"skill": "brainstorming", "signal": "has_feedback", "value": "3 corrections"}
  ],
  "session_samples": [
    {"skill": "team", "session": "uuid", "file": "/path/to/session.jsonl", "context": "...relevant snippet..."}
  ]
}
```

- `mechanical`：脚本直接产出，确定性、可复现
- `session_samples`：脚本提取相关片段���交给 LLM 做语义分析

### 机械信号类型

| 信号 | 检测方式 |
|------|---------|
| `low_usage` | session JSONL 计数，30 天内 ≤ 2 次 |
| `high_usage` | session JSONL 计数，30 天内 ≥ 10 次 |
| `zero_usage` | session JSONL 计数，30 天内 0 次 |
| `skill_md_too_long` | `wc -l SKILL.md` > 500 |
| `has_feedback` | memory 文件中 type: feedback 的记录数 |
| `has_correction` | memory 文件中包含纠正性 feedback 的记录数 |

### 语义分析（LLM 完成）

| 分析项 | 数据来源 |
|--------|---------|
| 误触发检测 | session 中 skill 被调用但上下文不匹配 |
| 用户重试模式 | session 中同一 skill 短时间内被多次调用 |
| 方向纠正 | session 中 skill 调用后用户立即纠正 |
| 规则重复/冲突 | CLAUDE.md vs specs 文本对比 |

## 变异算子

6 种具名算子，每次修复只用一种：

| 算子 | 适用场景 | 操作 |
|------|---------|------|
| `remove-redundancy` | 规则/描述与其他位置重复 | 删除重复内容，保留权威位置 |
| `tighten-description` | 触发不精确，误触发或漏触发 | 收紧 description 边界，加 "Do NOT use when" |
| `add-constraint` | 缺少必要的行为约束 | 在 SKILL.md 或 references 中增加约束 |
| `add-boundary` | 与其他 skill 职责边界模糊 | 明确区分，加排他描述 |
| `simplify` | 指令过长或过于复杂 | 精简内容，将细节下沉到 references |
| `restructure` | 流程顺序不合理或缺少检查点 | 重组步骤，调整顺序或加 gate |

证据→算子推荐映射：

| 证据特征 | 推荐算子 |
|---------|---------|
| 同一规则出现在两处以上 | `remove-redundancy` |
| 被其他 skill 的场景误触发 | `add-boundary` |
| 调用频率高但 feedback 中有纠正 | `tighten-description` |
| SKILL.md 超 500 行 | `simplify` |
| 用户在 session 中多次重试 | `add-constraint` |
| 流程中途被用户打断/纠正方向 | `restructure` |

决策流程：LLM 推荐算子 → 用户确认或覆盖。

## Guard 检查

每次修复后、提交前执行：

| 层 | 检查项 | 方式 | 失败后果 |
|----|--------|------|---------|
| 机械 guard | frontmatter 合法、引用文件存在、无相对路径脚本调用 | `omp test skill <name>` | 必须修复或 discard |
| 语义 guard | 修改后的 description 是否仍准确覆盖触发场景 | LLM 对比前后 | 警告，用户决定 |

执行顺序：机械 guard → 语义 guard → 用户最终确认。

## CLI 设计

```
omp-evolution scan [--source <dir>] [--days <n>]
omp-evolution history [--limit <n>]
```

| 子命令 | 作用 | 输出 |
|--------|------|------|
| `scan` | 增量扫描 session，输出机械信号 + session 样本 | JSON 到 stdout + last-scan.json |
| `history` | 查看当前项目的演进历史 | results.tsv 格式化输出 |

scan 参数：
- `--source <dir>`：扫描哪个目录下的项目 session，默认 `~/Projects`
- `--days <n>`：只扫描最近 N 天的 session，默认 30

脚本只做数据采���（确定性、可复现），所有需要判断的事留给 LLM + 用���。

## 参考

- [Karpathy autoresearch](https://github.com/karpathy/autoresearch) — 原始模式：modify → run → measure → keep/discard
- [uditgoenka/autoresearch](https://github.com/uditgoenka/autoresearch) — Claude Code 技能化实现，8 阶段协议
- [Balu Kosuri 通用 skill](https://medium.com/@k.balu124/i-turned-andrej-karpathys-autoresearch-into-a-universal-skill-1cb3d44fc669) — 6 种变异算子 + 二值评估
- [Autoresearch 101 Playbook](https://sidsaladi.substack.com/p/autoresearch-101-builders-playbook) — 非数值领域的度量方法
- [awesome-autoresearch](https://github.com/alvinunreal/awesome-autoresearch) — 社区项目索引
