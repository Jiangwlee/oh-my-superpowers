# 圆桌讨论：设计 insight skill/agent：从 AI 对话中提取高质量经验洞察，替代 ECC instinct 系统

- **日期**：2026-03-27
- **参与者**：Andrej Karpathy (claude/sonnet),Elon Musk (codex/gpt-5.4) Linus Torvalds (pi/qwen3.5-27b),Alan Kay (claude/sonnet)
- **轮次**：6

## 背景

# 讨论背景

**议题**：设计 insight skill/agent：从 AI 对话中提取高质量经验洞察，替代 ECC instinct 系统

## 问题

从 Claude Code/Codex/Pi 的对话中提取高质量经验洞察，特别是用户反复纠正 AI 后最终产生的正确工作思路和流程，将这些经验沉淀为结构化可检索的内容，以提高 AI 助手在后续对话中的表现。

## 已有系统：ECC Continuous Learning v2.1（Instinct 系统）

已存在一套完整的 instinct 系统（~/.claude/homunculus/），我们要在 oh-my-superpowers 中替代它：

**架构**：
- Hook 驱动观察捕获（PreToolUse/PostToolUse），100% 可靠
- 原子行为模型：trigger + action + confidence(0.3-0.9) + domain + scope
- 项目级隔离（基于 git remote SHA256[:12] hash）
- 进化管道：instinct → 聚类 → skill/command/agent
- CLI：instinct-cli.py（1426行 Python），命令有 status/import/export/evolve/promote/projects/prune

**ECC instinct 的弱点**：
1. Instinct 是原子行为（"当X时做Y"），缺少更高阶的"洞察"层
2. Observer 默认禁用，数据积累了 2100+ 条但从未分析
3. 只覆盖 Claude Code，不覆盖 Codex/Pi
4. 输出是机器可读的 YAML，人类不易消费
5. 缺少"纠正模式"识别——用户反复纠正→最终正确方案，这是最有价值的信号
6. 置信度衰减未实现
7. 聚类算法过于简单（仅 trigger 文本匹配）

## 设计约束

1. **方向 C**：Skill + Agent 组合
   - Skill（insight）：定义提取流程、存储格式、检索接口
   - Agent（insight-miner）：有专业判断力的角色，能识别纠正模式、总结经验
2. **输入源**：Claude Code / Codex / Pi 全部覆盖
3. **作用域**：执行时只处理当前 project，经验分项目级和用户级
4. **触发方式**：手动触发
5. **与 ECC instinct 关系**：替代——拷贝 ECC instinct 代码，再改造
6. **项目铁律**：独立自治、CLI 化、无相对路径引用

## 核心讨论问题

1. **Insight vs Instinct 的本质区别**：insight 应该是什么层级的认知单元？
2. **多 runtime 输入统一**：如何适配 Claude Code/Codex/Pi 不同的对话格式？
3. **纠正模式提取算法**：如何可靠识别"用户不停纠正→最终正确方案"？
4. **分级存储策略**：project level vs user level 的边界？提升标准？
5. **数据模型设计**：insight 的 schema 应该包含什么字段？
6. **输出双消费**：同时满足人（复盘）和 AI（提升表现）的消费需求

## 技术栈约束

- 脚本：Bash（简单任务）/ Python 3.10+（数据处理）/ Node.js（浏览器相关）
- 测试：unittest/pytest
- 包管理：uv（Python）
- Agent 运行时：Pi（核心）/ Claude Code（开发辅助）

## 讨论记录

### Round 1

- 【Andrej Karpathy】【陈述】：Insight核心是识别correction signal并保留错误→纠正轨迹
- 【Elon Musk】【质疑】：先定义能改变行为的最小原子单位，否则只是噪音结构化
- 【Linus Torvalds】【质疑】：数据结构先行，别把日志记录包装成学习系统
- 【Alan Kay】【质疑】：需要的不是更好的记忆系统，而是更好的理解协议
- **【主持人】【综合】**：核心争议：insight是规则还是故事？第二轮聚焦schema设计

### Round 2

- 【Andrej Karpathy】【反驳】：Insight最小原子是delta而非规则，需N次纠正收敛才是signal
- 【Elon Musk】【补充】：四步最短闭环：检测纠正→提炼差分→未来触发→验证复用
- 【Linus Torvalds】【质疑】：先定义struct insight的具体字段，别用抽象名词糊弄
- 【Alan Kay】【反驳】：Schema应该建模协议失配而非错误记录
- **【主持人】【综合】**：收敛于behavioral delta，分歧在是否需建模why；第三轮要求融合schema+真实例子

### Round 3

- 【Andrej Karpathy】【修正】：Schema核心是examples字段，让insight成为LLM可消费的few-shot样本
- 【Elon Musk】【综合】：5字段最小schema：trigger/bad_default/corrected_behavior/evidence/reuse_check
- 【Linus Torvalds】【质疑】：给出C struct实例+真实query场景，反对自然语言搜索
- 【Alan Kay】【修正】：mismatch_type枚举是系统进化的核心，沉默失配比纠正更有价值
- **【用户】**：【用户】【补充】：我提出一个架构层次问题。你们一直在讨论 insight 的 schema，但跳过了一个关键问题：数据管道的分层。

我认为应该是三层架构：

```
Session (raw data) → Memory (structured data) → Insight (high value experience)
```

- **Session 层**：原始对话/tool call 日志，临时数据，各 runtime 格式不同
- **Memory 层**：从 session 中提取的结构化事实/偏好/反馈，单条记录粒度，中期生命周期
- **Insight 层**：从 memory（和必要时回溯 session）中提炼的跨会话行为差分，长期有衰减

但不是简单线性管道，而是双路径：
- 日常事实走 session → memory（现有 auto-memory 机制已覆盖）
- 纠正模式走 session → insight（需要原始对话上下文识别 correction trajectory）
- 跨会话模式走 memory → insight（多次相似 feedback 聚合为 insight）

现有系统中 Session 和 Memory 层已经部分存在（Claude Code 的 observations.jsonl + auto-memory，Codex 的 memories），但 Insight 层缺失。请各位评估这个三层模型，讨论：insight skill 的设计应该如何适配这个分层？Memory 层是否需要统一？

### Round 4

- 【Andrej Karpathy】【补充】：三层正确，memory层存delta非结论，append-only硬约束，双路径按信噪比分优先级
- 【Elon Musk】【综合】：skill产出行为增量+agent强制消费，双路径=显式纠正+隐式路径偏航
- 【Linus Torvalds】【质疑】：用自由标签替代枚举，从真实数据聚类出tag，检索用模糊匹配
- 【Alan Kay】【补充】：Insight是Memory的diff，三种失配对应三种干预，系统要能修改自身结构
- **【用户】**：【用户】【补充】：我带来了外部研究成果，供各位参考。这是关于 AI 编程助手记忆解决方案的社区调研结果。

## 技术方案速览

**QMD (Quantized Memory Database)** — Tobi Lütke（Shopify CEO）
- SQLite + BM25 + 本地 GGUF 嵌入模型（embeddinggemma-300M + qwen3-reranker-0.6b）
- 全本地运行，社区评为 "S tier — Free, local, surgical"

**LanceDB 向量存储** — LOCOMO 基准测试：
- memory-core (SQLite FTS5) = 52% / 8.4s
- memory-lancedb (纯向量) = 76% / 4.8s
- memory-lancedb-pro (向量+reranker) = 80% / 14.3s

**TinkerClaw 认知记忆栈**（OpenClaw 生态最前沿）
- 五组件：ENGRAM → CORTEX → HIPPOCAMPUS → LIMBIC → SYNAPSE
- 三大技术：RAPTOR 分层摘要 + Spreading Activation 图遍历 + Zettelkasten 笔记
- 已稳定运行 8+ 周

**多层记忆架构（学术前沿）**
- MAGMA：语义/时间/因果/实体四图架构
- A-MEM：Zettelkasten 风格原子笔记
- 四层模型：Working Memory → Episodic → Semantic → Procedural

## 社区评价关键结论

1. **没有一致认可的最佳方案**——取决于场景
2. **S-Tier**：Lossless Claw + LanceDB（OpenClaw 公认 no-amnesia stack）、Hindsight（91% LoCoMo 准确率）
3. **记忆架构 > 记忆容量**——成功方案的共同点是有明确的数据生命周期管理
4. **三大争议**：Benchmark 信任危机（厂商自测不可信）、是否需要插件（4个Markdown文件 vs 向量DB）、隐私 vs 便利
5. **真实踩坑**：Markdown 记忆膨胀到 300 行后 agent 开始 skim 而非精读；向量 DB 记忆无法人类直接编辑调试

## 我的问题

结合这些外部研究，我们的 insight 系统的存储和检索层应该怎么选型？是 Markdown+git（可追溯、人可读）还是向量数据库（语义匹配）？还是混合方案？请结合我们之前讨论的三层架构和 schema 来评估。

### Round 5

- 【Andrej Karpathy】【补充】：memory层用SQLite，insight层用LanceDB只embed context字段，跟着检索模式走
- 【Elon Musk】【综合】：SQLite+LanceDB双层存储，agent强制消费insight，直接替换ECC
- 【Linus Torvalds】【质疑】：少于1000条别碰向量DB，先SQLite+FTS5跑通，用真实数据决定策略
- 【Alan Kay】【质疑】：Insight会反向重标注Memory，需要双向引用图而非单向管道
- **【用户】**：【用户】【质疑】：你们的存储选型忽略了 QMD。

QMD (Quantized Memory Database) 是 Shopify CEO Tobi Lütke 的方案：
- SQLite + BM25 + 本地 GGUF 嵌入模型（embeddinggemma-300M + qwen3-reranker-0.6b）
- 全本地运行，零 API 成本，社区评 "S tier — Free, local, surgical"
- 支持 MCP 服务器模式，可直接被 Claude Code/Codex 调用

QMD 本质上已经融合了 Torvalds 要的 SQLite 和 Karpathy 要的向量检索，而且是全本地的。这比"先 SQLite+FTS5，后加 LanceDB"的分阶段方案更简洁——一步到位，BM25 关键词 + 向量语义混合检索。

而且 QMD 的本地 GGUF 嵌入模型意味着：
1. 零隐私风险（数据不出本地）
2. 零 API 成本（不需要 OpenAI embedding API）
3. 低延迟（本地推理）
4. 已有 MCP 集成（可被现有 runtime 直接调用）

我认为 QMD 作为 insight 系统的存储+检索层是更好的选择。请评估。

### Round 6

- 【Andrej Karpathy】【修正】：QMD不是因为简洁，而是因为混合检索+无迁移成本——让数据增长驱动能力涌现
- 【Elon Musk】【反驳】：先证明insight有用，再证明向量检索必要，别把少零件伪装成一步到位
- 【Linus Torvalds】【质疑】：少于1000条真实数据之前，任何融合方案都是空中楼阁——先让SQLite FTS5跑起来
- 【Alan Kay】【修正】：先定义组件间的消息协议，存储是私有实现——协议错了，换多少次数据库都白搭
- **【主持人】【总结】**：6轮讨论总结：共识(behavioral delta+三层架构+强制消费)、分歧(存储选型+架构拓扑)、分阶段路线图

## 最终决策

### 存储选型：QMD 一步到位
**用户决策**：跳过 SQLite+FTS5 过渡阶段，直接采用 QMD（Quantized Memory Database）。

理由：
- 混合检索（BM25 + 本地 GGUF 嵌入）覆盖关键词和语义两种召回
- 零迁移成本——数据量从 10 到 10000 无需切换存储
- 全本地运行，零隐私风险，零 API 成本
- 已有 MCP 服务器模式，可被 Claude Code/Codex 直接调用
- 本地嵌入模型（embeddinggemma-300M + qwen3-reranker-0.6b）延迟低

### 架构：三层 + 最小双向引用
- Session → Memory → Insight 单向管道为主体
- Insight schema 中保留 `source_session_ids` 和 `reframes: [memory_ids]` 实现回溯
- 四个核心实体：memories, insights, evidence_links, consumption_logs

### Insight Schema（融合版）
```json
{
  "id": "string",
  "trigger": "string",
  "wrong_default": "string",
  "corrected_behavior": "string",
  "examples": [{"session_id", "before", "after", "context"}],
  "tags": ["自由标签"],
  "correction_count": "int (≥2)",
  "confidence": "float (带时间衰减)",
  "first_seen": "datetime",
  "last_confirmed": "datetime",
  "scope": "project | user",
  "why": "string (可选)",
  "source_session_ids": ["string"],
  "reframes": ["memory_id (可选)"]
}
```

### 实施方向
- **方向 C**：Skill（insight）+ Agent（insight-miner）组合
- 替代 ECC instinct，不做兼容层
- 手动触发，处理当前 project 下的 Claude Code / Codex / Pi 会话
- Agent 强制消费：任务前检索 top-k insight，声明要避免的旧错误

## 行动建议

1. 拷贝 ECC instinct 代码到 oh-my-superpowers，作为参考基础
2. 创建 `skills/insight/` 目录，实现提取→压缩→存储→检索流程，存储层用 QMD
3. 创建 `agents/insight-miner.md`，定义消费 insight 的 agent 角色
4. 用真实对话数据验证闭环，盯三个指标：命中率、采用率、纠错后复发率
