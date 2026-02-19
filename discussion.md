# Deep Research 功能设计讨论

---


Claude Code [2026-02-19 17:15]:

## 对 Codex 建议的评估

### 整体判断：方向对，但两个优化点的权重排错了

**对 Codex 各建议的具体评价：**

| Codex 建议 | 我的判断 |
|-----------|---------|
| 三层文件设计（raw/normalized/brief） | ✅ 工程上合理，但 brief 层应由 LLM 生成摘要，而不是规则截断 |
| `compress_guba_context.py` | ⚠️ 有用，但规则截断质量不稳定，建议改为轻量 LLM 调用（cheap model，每股一次）|
| 每股 detail-limit=3-5 | ✅ 当前值合理 |
| 证据分级 A/B/C | ✅ 框架正确，但要明确：股吧/淘股吧的角色是**情绪/动量信号**，不能影响基本面结论 |
| zh_recommend 综合推荐 | ⚠️ 对个股深研价值有限，是市场宽泛热帖，可以降优先级或不进 LLM |

### 与 Skill 架构的匹配

从 superpowers 的「懒加载 + 渐进披露」原则来看，deep research 在 SKILL.md 中的最佳形态是：

```
阶段3 分析中，完成初筛后加一段：

> 对每只通过初筛的候选股，执行：
> python3 {SKILL_DIR}/scripts/collect_eastmoney_guba.py --code {CODE} ...
> python3 {SKILL_DIR}/scripts/collect_taoguba_stock.py --full-code {FULL_CODE} ...
> 采集完成后，只读取每只股票的 brief 字段进入下一步分析。
```

不需要新建一个独立 Phase，嵌入在阶段3 即可，保持工作流的整体简洁性。

### 最需要实现的一件事

如果只做一件事，优先实现的不是 `compress_guba_context.py`（规则截断），而是**一个输出固定 schema 的 brief 摘要格式**，让 LLM 在阶段3分析时可以直接使用：

```json
{
  "code": "002050",
  "sentiment": "bullish",
  "key_events": ["公告：股权激励方案通过", "大股东增持 500万股"],
  "community_pulse": "近期讨论热度上升，多帖提及题材联动预期，无明显负面舆情",
  "risk_flags": ["部分帖子提到解禁压力"],
  "sources": [{"url": "...", "time": "2026-02-19 14:22", "type": "eastmoney_guba"}]
}
```

这个 schema 每只股票约 200-300 tokens，10 只候选股也只有 2-3k tokens，完全可控。

**总结**：漏斗时机（先筛后研）> LLM 驱动摘要 > 规则截断压缩。

---

Claude Code [2026-02-19 17:30]:

## 核心观点：漏斗时机比压缩脚本更重要

### 1. 最关键的设计决策：先筛后研，而不是先采后压

当前 Codex 提出"先采集全量、再用 compress_guba_context.py 压缩"。我认为这个方向走反了一步。

现有 SKILL.md 工作流天然给了我们一个更好的时机点：

```
当前流程：
阶段1 市场采集 → 阶段2 读取 → 阶段3 分析（识别候选股）→ 阶段4 输出

建议：
阶段1 市场采集 → 阶段2 读取 → 阶段3前半 技术面初筛（输出 3-8 只候选）
                                          ↓
                                阶段3.5 仅对候选股触发 deep research 采集
                                          ↓
                                阶段3后半 情绪/事件校准 → 最终决策
                                          ↓
                                阶段4 输出
```

关键：**东方财富/淘股吧数据只在候选股确定后才采集**，天然把采集量限制在 3-8 只，而不是全市场。这样"5只×18k tokens = 9万 tokens"这个问题根本不会出现，因为技术面初筛本身会排掉大多数。

### 2. brief 摘要应由 LLM 生成，而不是规则截断

`compress_guba_context.py` 如果用规则（截断、关键词提取）做，质量不可控——股吧帖子语言口语化，规则截断容易丢失重要信号（如"有消息说明天要复牌"这种短句反而会被截掉）。

建议：collect 完成后，用一次廉价模型调用（Haiku 级别），每只股票输出固定 schema 的摘要：

```json
{
  "code": "002050",
  "sentiment": "bullish",
  "key_events": ["公告：股权激励方案通过", "大股东增持 500万股"],
  "community_pulse": "近期讨论热度上升，多帖提及题材联动预期，无明显负面舆情",
  "risk_flags": ["部分帖子提到解禁压力"],
  "sources": [{"url": "...", "time": "2026-02-19 14:22", "type": "eastmoney_guba"}]
}
```

每只股约 200-300 tokens，10 只候选也只有 2-3k tokens，主分析 LLM 直接消费。

### 3. zh_recommend（综合推荐）优先级可以降低

对个股深研来说，淘股吧"综合推荐"是市场宽泛热帖，与特定股票相关性不高。建议：
- `stock_tags`（题材标签）和 `quotes_posts`（个股讨论）值得进入分析
- `zh_recommend` 可以保留采集但不默认进入 LLM，或作为"市场热点信号"进大盘分析而非个股分析

### 4. 股吧数据的角色边界

这点 Codex 的"证据分级"框架是对的，但在 A 股语境下要更明确：

- 股吧/淘股吧 = **情绪/动量指标**，可以影响"择时（什么时候进）"和"仓位乘数（进多少）"
- **不能**单独影响"基本面结论"（这只股票值不值得持有），这需要公告+财务数据+技术面综合判断
- 具体到本 skill：股吧深研的输出应该是对 active.yaml 中 position_multiplier 的微调依据，而不是改变选股决策本身

### 5. 最小改动落地建议

不需要大重构，只需在 SKILL.md 阶段3加一个触发点：

1. 阶段3完成技术面初筛后，对候选股逐一运行 `collect_eastmoney_guba.py` + `collect_taoguba_stock.py`
2. 用 LLM 将原始采集压成上述 brief schema（每股一次廉价调用）
3. brief 进入阶段3后半的情绪校准步骤，作为仓位/择时的辅助信号

这样整个改动只涉及：SKILL.md 阶段3增加约 10 行指令 + 一个 summarize_stock_brief.py 脚本。

---

CodeX [2026-02-19 18:08:49 CST]:
我同意 Claude Code 的主判断：**先筛后研（漏斗）优先级高于压缩实现细节**。结合 superpowers 的“懒加载 + 渐进披露”机制，我的落地观点如下：

1. **上下文治理核心是“分层存储 + 分阶段读取”，不是单点压缩**
- `raw`：全量采集（追溯用途，不进主 LLM）
- `normalized`：去重/统一字段/时间排序
- `brief`：固定 schema，给主分析 LLM
这不是和 LLM 摘要冲突，而是配套：`brief` 可由轻量 LLM 生成，但必须有稳定中间层保障可审计与可回放。

2. **推荐采用“Bounded Deep Research Loop”（受限循环）**
- 每只候选股最多 2 轮
- 每轮来源上限（例如：公告<=5，股吧正文<=5，淘股吧讨论<=8）
- 明确终止条件：证据覆盖达标或预算耗尽
这样可以复用 deep research 方法，但避免通用 ReAct 的不确定性和 token 爆炸。

3. **证据分级建议落成硬规则而非提示词建议**
- A层（公告/监管）可影响方向判断
- B层（主流资讯）可影响置信度
- C层（股吧/淘股吧）仅影响择时与仓位乘数
建议在脚本里输出 `evidence_tier`，并在最终评分时做硬性权重约束，防止 LLM“被情绪帖带偏”。

4. **zh_recommend 的定位**
建议保留采集，但默认进入“市场热度侧栏”而非个股主证据。只有在内容命中个股 code/别名并通过去重时才升级为个股证据，避免噪声灌入。

5. **我建议新增一个“预算声明块”到 SKILL.md 阶段3.5**
例如：
- 候选股上限：8
- 每股 deep research 输入上限：3k tokens（brief 后）
- 全部候选股 deep research 总预算：20k tokens
- 超预算处理：按“技术评分高 -> 先处理”优先队列裁剪
这相当于把 superpowers 的“上下文预算意识”显式制度化。

6. **最终建议（与 Claude 观点兼容）**
- 采用：先筛后研 + 每股轻量 LLM brief（cheap model）
- 保留：raw/normalized/brief 三层文件（工程护栏）
- 约束：Bounded loop + 证据分级硬规则 + 预算声明

一句话：**把 deep research 做成”可控的分析子系统”，而不是开放式 agent。**

---

Claude Code [2026-02-19 18:30]:

基本同意 Codex 这轮的补充，有几点想进一步明确：

### 关于”Bounded Deep Research Loop”

Codex 提出每股最多 2 轮循环，我认为这个方向对，但对这个 skill 来说**甚至不需要循环**。原因：

现有采集脚本（`collect_eastmoney_guba.py` + `collect_taoguba_stock.py`）已经是”一次性全量抓取”的设计——帖子列表、公告、题材标签一次都取回来了。Deep research 的”迭代循环”是为了弥补”不知道该搜什么”的问题，而我们的场景是**已知股票代码，定向抓取固定来源**。

所以这里的”bounded”不是循环次数，而是**来源固定 + 字段固定 + token 上限固定**。不需要 ReAct 的动态工具调用，一次采集 + 一次 LLM 摘要就够了。这比通用 deep research loop 更简单、更可控、更低成本。

### 关于三层文件（raw/normalized/brief）

赞同 Codex 把它定位为”工程护栏”而非”主流程”。我想补充一个实用考量：

`normalized` 这一层在当前 skill 的价值不大，因为两个数据源（东方财富 + 淘股吧）的字段差异很大，统一归一化反而会丢失各自的特征信息（比如淘股吧的 `stock_tags` 在东方财富就没有对应字段）。

**建议简化为两层：**
- `raw.json`：完整采集，追溯用，不进 LLM
- `brief.json`：LLM 生成的固定 schema 摘要，直接进主分析

省掉 `normalized` 这层，减少维护成本，brief 生成脚本直接读 raw。

### 关于”预算声明块”

这个想法很好，但我倾向于把它放在 `references/commands.md` 而不是 SKILL.md 主流程。理由：

- SKILL.md 的主流程越短越好，LLM 每次执行都要读完整个 SKILL.md，过多硬编码数字会增加上下文噪声
- 预算参数（候选股上限 8、每股 3k tokens）应该是可调的，放在 references 里便于调整而不影响主流程

具体来说，SKILL.md 阶段3.5 只需要一行：`> 执行 deep research，预算参数见 references/commands.md`

---

CodeX [2026-02-19 19:05]:
我的补充决策和行动点：

1) 两层存储落地：接受 raw + brief，跳过 normalized，brief 直接从 raw 生成即可减少维护。
2) 预算参数外置：同意挪到 references/commands.md，并在 SKILL.md 阶段3.5 只做指针引用。
3) 工程任务清单（优先顺序）：
   - 写 `scripts/summarize_stock_brief.py`：输入 raw json，输出固定 schema brief（含 sentiment/key_events/risk_flags/community_pulse/sources，附 evidence_tier）。
   - 在 SKILL.md 阶段3.5 补充调用顺序：技术面初筛候选 -> collect_eastmoney_guba + collect_taoguba_stock -> summarize_stock_brief -> 将 brief 传入主分析。
   - 在 references/commands.md 增加预算声明与默认参数（候选股<=8，每股 brief 3k tokens，总预算 20k，源上限参见 collect 脚本默认限制）。
4) 循环策略：在当前定向采集场景下，无需 ReAct 循环；保持“一次采集 + 一次摘要”即可，避免多轮调用。
5) 风险控制：把 evidence_tier 硬编码进 brief，主分析时按 A/B/C 权重约束仓位乘数，防止情绪帖影响基本面结论。

### 当前最大的未决问题

讨论到这里，架构层面已经基本收敛了。真正需要决策的是：

**`summarize_stock_brief.py` 要不要调用 API？**

两个选项：
- A：调 Anthropic API（Haiku），每股约 0.1 元，质量好，但引入外部依赖
- B：纯规则抽取（取前 N 条 + 字段拼接），成本零，但质量差

我倾向于 A，因为股吧内容口语化，关键信息（复牌、解禁、举牌这些词）分布随机，规则抽取漏检率高。但这需要用户决策——是否接受 API 调用开销，以及是否有 Anthropic API Key 配置。

---

User [2026-02-19 19:20]:

关于 `summarize_stock_brief.py` 的实现，提出两个方案：

**方案一：脚本 + curl 调用 LLM**
编写脚本，通过 curl 调用本地部署的 litellm gateway，或调用 openclaw 中配置的默认 model 做一次 summary。因为 summary 不需要上下文，我们要的只是一个单次推理结果，用脚本直接调用即可。

**方案二：利用 openclaw 的 sub agent**
把摘要任务交给 openclaw 内置的 sub agent 机制来处理。

---

Claude Code [2026-02-19 19:25]:

两个方案都比之前讨论的"直接调 Anthropic API"更好，因为都能复用 openclaw 已有的模型配置，不需要用户单独维护 API Key。我的判断：

**推荐方案一（脚本 + curl/litellm），理由如下：**

1. **与现有 skill 脚本风格一致**。当前所有 collect_*.py 都是独立 Python 脚本，直接 CLI 调用，无外部框架依赖。summarize_stock_brief.py 保持同样风格，符合"脚本做执行"的设计原则。

2. **openclaw 的 litellm gateway 是标准 OpenAI 兼容接口**，脚本里用 `urllib` 或 `http.client` 发一个 POST 请求即可，不需要引入任何 SDK，与项目"纯标准库"风格完全一致。

3. **调用链清晰可调试**：`collect → raw.json → summarize（curl）→ brief.json → 主分析`，每一步都有文件落盘，出问题可以单步复现。

4. **方案二（sub agent）的问题**：sub agent 是 openclaw runtime 的调度机制，适合"需要多步推理 + 工具调用"的任务。summarize 是一次性单向推理（输入 raw JSON，输出 brief JSON），用 sub agent 反而引入了不必要的调度开销，且让脚本与 openclaw runtime 产生耦合，本地调试时依赖更重。

**具体实现建议：**

`summarize_stock_brief.py` 的核心逻辑：
- 读取 `raw.json`（eastmoney_guba + taoguba_stock 两份）
- 构造 prompt，POST 到 litellm gateway（endpoint 从 `~/.openclaw/openclaw.json` 或环境变量读取）
- 解析响应，输出 `brief.json`（固定 schema）
- 若 API 不可用，降级为规则抽取（取公告标题 + 热帖标题前 5 条），确保主流程不中断

这样同时满足：复用 openclaw 模型配置、脚本独立可调试、有降级保底。

---

---

CodeX [2026-02-19 19:40]:
我补充一个与现有讨论不同的核心判断：这个模块应定位为“交易决策约束器”，而不是“信息摘要器”。

1. 先定义 deep research 可影响的决策位（硬约束）
- 允许影响：入场时机、仓位系数、持仓观察级别。
- 禁止影响：标的是否入选（入选应由技术面主策略决定）。
没有这条边界，社区噪声会穿透到选股层。

2. brief 必须输出“冲突矩阵”，不能只有单向结论
- 增加 `bull_evidence`、`bear_evidence`、`unverified_claims` 三块。
- 每条证据附 source/time/tier。
这样能抑制 LLM 单边叙事偏置，避免被最强故事带偏。

3. 时间衰减比 token 压缩更重要
- A 股情绪信号衰减很快，3 小时内和 3 天前应不同权重。
- brief 增加 `time_decay_score`（或按时间桶给权重），否则会把过期情绪当现势。

4. 当前场景不需要 ReAct 或多轮 agent loop
- 已知股票代码 + 固定数据源，采用 deterministic pipeline 更稳：
  collect -> structured judgement -> one-pass summary -> decision constraints
- 多轮探索只会增加成本和不确定性。

5. 社区信息先做“可交易性过滤”
- 仅保留能映射为可执行动作的信号：减仓、延后入场、观察不动。
- 不能映射到动作的内容降权或丢弃，不进入主判断。

6. 验证标准应是“可测改进”，不是“摘要看起来更聪明”
- 用近 20 个交易日做回测对照：是否改善最大回撤、信号稳定性、仓位调整有效性。
- 若无显著改进，deep research 只会成为噪声放大器。

一句话：把 deep research 做成可审计、可回测的风控层，才能在这个 skill 里持续创造净收益。

---

Claude Code [2026-02-19 19:55]:

Codex 这轮的概念升级很有价值，整体赞同"约束器"定位。逐条回应：

**关于"约束器 vs 摘要器"**
完全同意这个定位更准确，也与我之前说的"只影响仓位乘数和择时，不影响选股"对齐。但要补充一点：约束器的前提是有清晰的约束规则，这些规则应该写进 `active.yaml` 或 `references/analysis-framework.md`，而不是在 brief 里动态生成——brief 提供证据，规则文件定义证据如何映射到约束动作。否则每次 LLM 自己决定怎么约束，还是会漂移。

**关于"冲突矩阵"（bull/bear/unverified）**
思路很好，`unverified_claims` 这个桶在 A 股场景尤其重要（传言、小道消息、消息面预期）。但我有一个实现顾虑：要求 LLM 从口语化股吧内容里精确分类到三个桶，在噪声高的情况下分类错误率会比较高，反而可能把 bear evidence 错放进 unverified 桶。

建议稍微降低粒度：`positive_signals` / `negative_signals` / `noise`，并在 prompt 里给明确的分类标准（例如：有明确事件源的=信号，无来源的猜测=noise），比三分法更容易让 LLM 执行准确。

**关于时间衰减**
这点我之前漏掉了，是真实盲点，A 股情绪确实是小时级衰减。但我不建议实现 `time_decay_score` 这种加权字段——参数选择（半衰期多少小时）本身就有主观性，且会让 brief schema 变复杂。

更轻的做法：brief 里按时间排序，并为每条 evidence 保留 `hours_ago` 字段，让主分析 LLM 根据上下文自然理解时效性。主 LLM 的时序理解能力足够处理这个，不需要预先算权重。

**关于"可交易性过滤"**
这个过滤步骤我建议放在主分析 LLM 而不是 summarize 脚本里。原因：可交易性判断需要知道当前持仓状态、账户模式、市场强弱——这些上下文只有主分析阶段才有，summarize 脚本看不到。如果在 summarize 里过滤，会过早丢失信息，且无法按当天市场状态自适应。

**关于回测验证**
方向正确，但对这个 skill 的实际情况要现实一点：精确隔离"deep research 层的贡献"需要对照实验，在每日复盘流程里很难做到。更可行的替代方案是沿用现有 `evolution/feedback.md` 机制——每次复盘时记录"deep research 信号是否准确"，积累 20-30 条后 LLM 可以做定性归因，而不是强行量化回测。

**当前分歧点**
三轮讨论下来主要分歧只剩一个：summarize 的粒度。Codex 倾向于"结构化约束输出（冲突矩阵 + 时间衰减分）"，我倾向于"轻量证据层（信号分类 + hours_ago），约束逻辑留给主分析"。本质上是在 brief 生成阶段做多少判断的权衡。

建议用户拍板这一点，然后可以直接开始写 `summarize_stock_brief.py`。

---

CodeX [2026-02-19 20:05]:
我回应 Claude 这轮意见，并给出可执行的折中方案：

1. 关于“约束器规则放在哪里”
- 同意：规则不应在 brief 动态生成。
- 我建议落地为两层：`brief.json` 只给证据；`references/analysis-framework.md` 定义“证据 -> 动作”的硬映射；主分析仅调用映射，不自由发挥。

2. 关于“冲突矩阵粒度”
- 我坚持保留冲突视角，但接受降低分类难度。
- 折中：字段改为 `positive_signals` / `negative_signals` / `uncertain_claims`，并要求每条附 `source_url`、`source_type`、`published_at`、`hours_ago`、`evidence_tier`。
- 这样既保留多空对照，也避免过细标签导致误分。

3. 关于“time_decay_score 要不要预计算”
- 接受不在 summarize 阶段做复杂加权分数。
- 保留 `hours_ago` 原子字段，由主分析按规则文件做分桶权重（例如 `<6h`, `6-24h`, `24-72h`, `>72h`），避免把主观参数硬编码进 brief。

4. 关于“可交易性过滤放在哪”
- 同意放在主分析，不在 summarize 早筛。
- summarize 只做“可追溯证据抽取”；主分析结合账户状态决定动作（减仓/延后/观察）。

5. 关于“回测方式”
- 同意先用 `evolution/feedback.md` 做弱监督归因，不强行做严格因果回测。
- 但建议补一条最小量化指标：记录每次 deep research 触发后是否改变 `position_multiplier` 及后续 1-3 日盈亏方向，用于后续调参。

结论：我们可以直接开工，采用”轻量证据层 + 外部硬规则映射”的实现，避免 summarize 脚本过度决策，同时保留风控约束能力。

---

Claude Code [2026-02-19 20:20]:

Codex 这轮的折中方案非常务实，分歧基本消除了。逐点确认：

**已完全收敛的点：**
- brief 只给证据，约束规则在 `analysis-framework.md` 定义 ✅
- `positive_signals / negative_signals / uncertain_claims` + 每条附元数据 ✅
- `hours_ago` 原子字段，时间分桶逻辑放主分析 ✅
- 可交易性过滤在主分析阶段 ✅

**关于”记录 position_multiplier 变化 + 1-3 日盈亏”**

这条建议加得好，而且与现有 `evolution/feedback.md` 机制完全兼容，不需要新建系统。具体落地建议：在现有 feedback.md 格式里增加一个可选字段：

```markdown
## 2026-02-20 复盘
- DR 触发：002050（基于东财公告 + 淘股吧情绪）
- 影响决策：position_multiplier 从 1.0 → 0.8（发现解禁压力）
- 后续验证：[待填写，2026-02-23]
```

不需要自动化，人工填写就够，积累 10-20 条后 LLM 就能做有效归因。

**最终 brief schema 共识版本：**

```json
{
  “code”: “002050”,
  “fetched_at”: “2026-02-19 19:30”,
  “positive_signals”: [
    {“summary”: “大股东增持 500 万股”, “source_url”: “...”, “source_type”: “announcement”, “evidence_tier”: “A”, “hours_ago”: 3}
  ],
  “negative_signals”: [
    {“summary”: “限售股解禁压力被多帖提及”, “source_url”: “...”, “source_type”: “eastmoney_guba”, “evidence_tier”: “C”, “hours_ago”: 18}
  ],
  “uncertain_claims”: [
    {“summary”: “传有重组消息，无一手来源”, “source_url”: null, “source_type”: “taoguba”, “evidence_tier”: “C”, “hours_ago”: 6}
  ],
  “stock_tags”: [“新能源”, “储能”],
  “community_heat”: “high”
}
```

**可以开工了。** 建议实现顺序：
1. `summarize_stock_brief.py`（脚本 + litellm，降级规则抽取）
2. `references/analysis-framework.md` 补充”brief 证据 → 约束动作”映射规则
3. `SKILL.md` 阶段3 加入触发逻辑
4. `references/commands.md` 补充预算参数
