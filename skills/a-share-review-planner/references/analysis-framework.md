# A股复盘分析框架

> 本文档是 LLM 执行复盘分析的详细思考模板。
> 按顺序完成 7 个步骤，每个步骤都必须有明确结论。
> 不要跳过任何步骤，不要遗漏任何必答问题。

---

## 第一步：市场环境判断

### 必须读取的数据

1. `market_sectors.json` — 板块资金摘要（净流入前5+后5板块）
2. `news_headline.json` — A股头条（含指数涨跌、成交额等宏观信息）
3. `news_daily.json` — 每日财经（政策/宏观）
4. 淘股吧热帖中关于大盘的讨论
5. `broker_account.json` — 账户资金及持仓盈亏（**如存在**）

### 必须回答的问题

1. **大盘指数表现如何？**
   - 沪指、深指、创业板、北交所的涨跌幅
   - 美股（道琼斯/纳斯达克）前一日表现
   - 来源：从新闻和舆情中提取

2. **市场成交额是多少？**
   - 今日总成交额
   - 与近期（5日/20日）平均比较，放量还是缩量
   - 来源：从新闻中提取

3. **板块涨跌格局如何？**
   - 上涨板块数 vs 下跌板块数
   - 涨幅前5和跌幅前5的板块
   - 来源：market_sectors.json

4. **资金流向什么方向？**
   - 资金净流入前5板块
   - 资金净流出前5板块
   - 是否有明显的板块资金聚集
   - 来源：market_sectors.json

5. **涨跌停情况如何？**
   - 涨停数量、跌停数量
   - 连板高度（最高几板）
   - 来源：`ths_snapshot.json`（同花顺涨停快照）

6. **账户健康度如何？**（仅当 broker_account.json 存在时作答）
   - 账户总资产和可用资金
   - 持仓盈亏（hold_earn）占总资产的比例 → 判断属于哪种 account_mode
   - 当前持仓明细（持有哪些股、各自盈亏）
   - account_mode 对本次仓位建议的影响（参考 strategy/active.yaml 中 account_mode 的 action）

   **account_mode 判断优先级高于 market_mode**：
   - critical 模式 → 不论市场多强，不接受任何新仓，复盘仅做分析不做计划
   - defensive 模式 → 仓位建议下调一档，不开新题材仓
   - growth 模式 → 仓位建议上调一档
   - normal 模式 → 按市场强弱正常执行

### 输出格式

```
市场环境判断：
- 强弱评级：强 / 中 / 弱
- 主线风格：题材驱动 / 趋势主导 / 混沌轮动
- 账户健康度：growth / normal / defensive / critical（无数据则填"未知"）
- 最终仓位建议：激进(6-8成) / 标准(3-5成) / 防守(1-2成或空仓) / 观望（critical时）
- 判断依据：（2-3句话总结，说明市场和账户因素各自如何影响仓位建议）
```

### 判断参考标准

- **强市**：指数涨幅>1%，成交额放量，涨停>50家，跌停<10家，板块普涨
- **中性**：指数涨跌幅<1%，成交额平稳，涨跌停均衡
- **弱市**：指数跌幅>1%，成交额萎缩或恐慌放量，跌停>30家，板块普跌

---

## 第二步：题材线索识别

### 必须读取的数据

1. `ths_snapshot.json` — 同花顺最强板块数据
2. `ths_snapshot.json` — 同花顺连板天梯数据
3. `news_headline.json` — A股头条
4. `news_opportunity.json` — 机会情报
5. `taoguba_recommend.json` — 淘股吧今日推荐（含 `content`，用于潜在/新题材挖掘）
6. `taoguba_hot_discussion.json` — 淘股吧热门讨论（`subject/body/quotecontent`，用于潜在/新题材挖掘）
7. `taoguba_hot.json` — 淘股吧精华帖（用于识别已发酵热点题材）

### 必须回答的问题

1. **当前市场有主线题材吗？**
   - 如有：名称、已持续几天、处于什么阶段（启动/加速/分歧/衰退）
   - 核心标的有哪些、龙头股是谁
   - 来源：连板天梯 + 最强板块 + `taoguba_hot.json`

2. **有什么新兴题材线索？**
   - 催化事件是什么（政策/新闻/突发事件）
   - 受益板块和个股
   - 参与价值评估：高（强催化+资金认可）/ 中（有催化但尚未确认）/ 低（概念炒作）
   - 来源：`news_opportunity.json` + `taoguba_recommend.json` + `taoguba_hot_discussion.json`

3. **哪些题材在衰退？**
   - 名称、衰退信号（龙头跌停/板块分化/资金撤离）
   - 如果持有相关个股，需要注意什么

4. **市场情绪如何？**
   - 淘股吧热帖的整体基调：乐观 / 谨慎 / 恐慌（优先看 `taoguba_hot.json`，并与热门讨论交叉验证）
   - 散户关注的热点是否与机构资金方向一致
   - 是否有明显的一致性预期（注意反向风险）

### 输出格式

```
题材线索：
主线题材：
  - [题材名] | 阶段：[启动/加速/分歧/衰退] | 持续：[X天]
    龙头：[个股名]
    核心标的：[个股列表]

新兴线索：
  - [题材名] | 催化：[事件] | 评估：[高/中/低]
    受益标的：[个股列表]

衰退警示：
  - [题材名] | 信号：[具体衰退信号]

市场情绪：[乐观/谨慎/恐慌]
情绪判断依据：（1-2句话）
```

---

## 第三步：个股筛选

### 必须读取的数据

1. `trend_scan.json` / `trend_report.md` — 趋势扫描结果
2. 第一步和第二步的结论
3. `evolution/selection_rules.md` — 选股规则修正（如有内容）

### 筛选流程

#### 3.1 趋势股筛选

从 `trend_scan.json` 中筛选：
- 星级 >= 4星
- 优先选择情绪因子 L3 及以上（稳健上行 / 情绪偏强 / 主升强化）
- 参考交易信号（买入 > 观察 > 卖出）
- 排除 `evolution/selection_rules.md` 中的否定条件

#### 3.2 题材股筛选

从人气榜前200中筛选：
- 与第二步识别的主线/新兴题材相关
- 优先选择龙头股或确定性高的跟风股
- 注意：仅当第一步判断为"题材驱动"或存在强主线时才选题材股

#### 3.3 筛选数量

- 总候选：5-10只
- 趋势股：3-5只
- 题材股：0-5只（视市场风格而定）

### 每只候选股必须输出

```
[代码] [名称] [类型：趋势/题材]
- 选股理由：（为什么选它，2-3句话）
- 所属题材：（如适用）
- 趋势评分：（星级和总分，来自 trend_scan.json）
- 情绪因子：（颜色和等级）
- 风险点：（1-2个主要风险）
```

---

## 第3.5步：个股深度分析（情绪与事件校准）

> **触发条件**：第三步完成筛选，确定候选股列表后执行。
> **目的**：对每只候选股采集社区情绪与近期事件，**以仓位乘数和入场时机校准为主**；tier A 严重负面公告（监管处罚/立案调查等）作为强制例外，可触发候选股复核。

### 执行流程

对每只候选股（`{CODE}` 为6位代码，`{FULL_CODE}` 为如 `sz002050`），依次执行：

**第一步：运行采集脚本**

```bash
# 东方财富股吧采集
python3 {SKILL_DIR}/scripts/collect_eastmoney_guba.py \
  --code {CODE} \
  --output /tmp/a-share-review/{DATE}/dr_{CODE}_em.json \
  --post-limit 36 --detail-limit 5 --notice-days 3

# 淘股吧个股扩展采集
python3 {SKILL_DIR}/scripts/collect_taoguba_stock.py \
  --full-code {FULL_CODE} \
  --output /tmp/a-share-review/{DATE}/dr_{CODE}_tgb.json \
  --quotes-count 8
```

> 详细参数见 `references/commands.md` 的"Deep Research 预算参数"章节。

**第二步：运行 compact 提取脚本**

```bash
python3 {SKILL_DIR}/scripts/summarize_stock_brief.py \
  --code {CODE} \
  --em-raw /tmp/a-share-review/{DATE}/dr_{CODE}_em.json \
  --tgb-raw /tmp/a-share-review/{DATE}/dr_{CODE}_tgb.json \
  --output /tmp/a-share-review/{DATE}/dr_{CODE}_compact.json \
  --compact-only
```

> 此脚本**不调用任何 LLM**，纯规则提取，输出约 600 tokens 的精简 JSON。
> 原始 raw 文件（`_em.json` / `_tgb.json`）体积过大（~10k tokens），**不要**直接传给 LLM。

**第三步：读取 compact，生成 brief**

读取 `/tmp/a-share-review/{DATE}/dr_{CODE}_compact.json`，根据下方 schema 和分类规则，**由你直接生成 brief JSON**，然后用 bash 写入文件：

```bash
cat > /tmp/a-share-review/{DATE}/dr_{CODE}_brief.json << 'EOF'
{生成的 JSON 内容}
EOF
```

### brief 结构与生成规则

按以下 schema 生成（严格 JSON，不含注释）：

```json
{
  "code": "{CODE}",
  "summarized_at": "{当前时间 YYYY-MM-DD HH:MM:SS}",
  "positive_signals": [
    {"summary": "简洁描述（20字内）", "source_url": "原始数据中的url字段", "source_type": "announcement|stock_info|eastmoney_guba|taoguba", "evidence_tier": "A|B|C", "hours_ago": 数字}
  ],
  "negative_signals": [...],
  "uncertain_claims": [...],
  "stock_tags": ["题材1", "题材2"],
  "community_heat": "high|medium|low"
}
```

**数据字段映射（compact JSON 字段）：**

> compact 字段由 `summarize_stock_brief.py --compact-only` 从 raw 文件提取，与 raw 字段名不同。

| compact 字段 | brief 中的 source_type | evidence_tier |
|-------------|----------------------|---------------|
| `announcements`（公告） | `announcement` | `A` |
| `news_infos`（资讯列表） | `stock_info` | `B` |
| `guba_posts`（东方财富帖子） | `eastmoney_guba` | `C` |
| `taoguba_posts`（淘股吧讨论） | `taoguba` | `C` |

**分类规则：**
- `positive_signals`：有明确来源的利好（增持/回购/中标/业绩超预期/题材催化）
- `negative_signals`：有明确来源的利空（减持/亏损/诉讼/解禁/监管处罚）
- `uncertain_claims`：无一手来源的传言、推测、模糊情绪
- 每类最多 5 条，优先 tier A/B，同级别优先 `hours_ago` 小的（越新越优先）
- `hours_ago`：根据各条数据的时间字段与当前时间计算，单位小时（整数）
- `community_heat`：根据帖子总量和互动量判断（≥10条=high，4-9条=medium，<4条=low）

### 证据分级与约束规则

| tier | 来源 | 可影响范围 |
|------|------|-----------|
| **A**（公告/监管） | `stock_notices_recent` | 仓位/择时校准；严重负面（处罚/立案）可触发候选复核 |
| **B**（资讯媒体） | `stock_infos` | 仓位乘数和置信度评分 |
| **C**（社区帖子） | 股吧/淘股吧 | **仅**影响择时（入场时机）和仓位乘数 |

**硬性约束**（不可绕过）：
- C 层证据**不得**单独改变选股决策（是否选入候选股）
- B 层证据仅影响仓位乘数，不单独触发候选复核
- 若 `negative_signals` 中存在 tier A 严重负面（监管处罚/立案调查/重大违规公告），**必须**重新评估是否保留该候选股
- `uncertain_claims` 仅供参考，不得作为决策依据

### 时效性判断

- `hours_ago <= 6`：信号权重高，事件很可能尚未被市场充分定价
- `hours_ago 6-24`：正常权重
- `hours_ago 24-72`：权重降低，市场可能已反映
- `hours_ago > 72`：低权重，仅作背景参考

### 输出：仓位校准信息

每只候选股完成 brief 分析后，生成该股的校准信息，并在第四步直接并入该股交易计划条目。  
不要单独输出一节“DR校准结论”，避免同一股票重复出现两次。

---

## 第四步：交易计划制定

### 必须读取的数据

1. 第三步筛选的候选股列表
2. `strategy/active.yaml` — 当前策略
3. 用户提供的当前持仓（如有）

### 对每只候选股制定计划

根据 active.yaml 中的策略模板，结合具体个股情况制定：

#### 趋势股计划模板（含深度分析校准）

```
### [代码] [名称] [趋势]

- **趋势评分**：[星级] [总分] [情绪颜色]
- **选股理由**：...
- **深度分析校准**：
  - 情绪：[乐观/中性/谨慎/负面]
  - 关键事件：[1-2条最重要信号，tier A/B 优先]
  - 仓位乘数调整：[×1.0（不变）/ ×0.8（轻减）/ ×0.5（减半）/ ×1.2（小增）]
  - 调整依据：[1句话]
- **入场条件**：[参考 active.yaml 中 trend_stock.entry，结合个股具体均线位置]
- **目标仓位**：[基础仓位 × 深度分析仓位乘数 = 最终金额]
  （基础仓位来自 active.yaml trend_stock.position；深度分析乘数来自本条“深度分析校准”，无校准则乘1.0）
- **止盈条件**：[参考 active.yaml 中 trend_stock.take_profit]
- **止损条件**：[参考 active.yaml 中 trend_stock.stop_loss]
- **持有周期**：[参考 active.yaml 中 trend_stock.holding_period]
- **风险点**：...
```

#### 题材股计划模板（含深度分析校准）

```
### [代码] [名称] [题材-题材名]

- **选股理由**：...
- **所属题材**：[题材名] | 阶段：[启动/加速]
- **深度分析校准**：
  - 情绪：[乐观/中性/谨慎/负面]
  - 关键事件：[1-2条最重要信号，tier A/B 优先]
  - 仓位乘数调整：[×1.0（不变）/ ×0.8（轻减）/ ×0.5（减半）/ ×1.2（小增）]
  - 调整依据：[1句话]
- **入场条件**：[参考 active.yaml 中 theme_stock.entry]
- **目标仓位**：[基础仓位 × 深度分析仓位乘数 = 最终金额]
  （基础仓位来自 active.yaml theme_stock.position；深度分析乘数来自本条“深度分析校准”，无校准则乘1.0）
- **止盈条件**：[参考 active.yaml 中 theme_stock.take_profit]
- **止损条件**：[参考 active.yaml 中 theme_stock.stop_loss]
- **持有周期**：[参考 active.yaml 中 theme_stock.holding_period]
- **风险点**：...
```

### 整体仓位分配

确保：
- 总仓位符合第一步的仓位建议
- 单只不超过策略中规定的上限
- 题材股和趋势股的比例符合市场风格

---

## 第五步：风险检查

### 必须检查的项目

1. **持仓集中度**
   - 同一板块的个股是否超过3只？
   - 同一题材的仓位是否超过总仓位50%？
   - 如有集中，评估风险并给出建议

2. **与昨日计划对比**（如有昨日计划）
   - 新增了哪些标的？为什么？
   - 移除了哪些标的？为什么？
   - 保持的标的策略是否有调整？

3. **当前持仓检查**（如用户提供了持仓）
   - 持仓中哪些标的需要调整（减仓/清仓/加仓）？
   - 是否有触发止损条件的标的？
   - 是否有达到止盈条件的标的？

4. **特殊风险**
   - 是否临近长假？（长假前不宜新建仓）
   - 是否有重要政策/数据发布预期？
   - 是否有个股的业绩预告/定增/解禁等事件？

### 输出格式

```
风险检查：
- 集中度：[正常/偏高]，[具体描述]
- 计划变更：[新增X只/移除X只/调整X只]
- 持仓调整建议：[具体建议]
- 特殊风险：[如有]
```

---

## 第六步：策略回顾与微调

### 必须读取的数据

1. `strategy/active.yaml` — 当前策略
2. `strategy/default.yaml` — 默认基线（仅参考）
3. `evolution/feedback.md` — 交易诊断反馈（如有内容）
4. `evolution/known_pitfalls.md` — 已知陷阱（如有内容）

### 6a：提案生成

首先评估是否有必要调整策略，如有，生成具体的修改提案。
每条提案格式如下：

```
提案：[一句话描述修改内容]
修改目标：trend_stock.stop_loss / theme_stock.position / market_position.strong / ...
当前值："[当前内容]"
建议值："[修改为]"
```

### 6b：提案评分（ProposalJudge 机制）

对每条提案从 4 个维度评分（0-10 分）：

| 维度 | 问题 |
|------|------|
| **relevance（相关性）** | 这个修改与当前市场阶段、账户状态是否密切相关？ |
| **value（价值）** | 它能实质性改善选股/止盈/止损效果吗？ |
| **safety（安全性）** | 修改后策略是否会变得过于激进，提高爆仓或大亏风险？ |
| **feasibility（可行性）** | 用户的操作习惯和执行能力能落实吗？ |

**决策规则**（严格执行，不可绕过）：
- 平均分 **≥ 7** 且 **无任何维度 < 4** → 修改 active.yaml
- 否则 → 记录提案但不执行，在输出中说明原因

### 策略修改规则

- 每次最多修改1-2个参数，避免大幅调整
- 通过评分的修改必须追加到 active.yaml 的 evolution_log 中
- 如果 active.yaml 偏离 default.yaml 过多，需要提醒用户审核

### 输出格式

```
策略回顾：
- 当前策略评估：[适用/需微调]

提案（如有）：
  提案1：[描述]
  评分：relevance=[X] value=[X] safety=[X] feasibility=[X] 均值=[X]
  决策：[执行修改 / 不执行（原因：...）]

- 调整内容：[无调整 / 具体修改内容]
- 调整原因：[如有调整]
```

---

## 第七步：知识库自动积累

> 这一步是本次复盘的最后收尾，**不得跳过**。目的是将当日发现的新规律沉淀到知识库。

### 必须执行的检查

**检查一：是否发现新的选股规律或陷阱？**

回顾本次分析中，是否遇到以下任何情况：
- 某题材或个股的行为规律与 `known_pitfalls.md` 中已有记录**不同**，发现了新陷阱
- 某选股方法在今天特别奏效或失效，值得记录为规律
- 某市场特征（政策/季节/节假日）对行情有明显影响

如果**发现了新规律/陷阱**：
1. 检查 `evolution/known_pitfalls.md` 是否已有类似记录
2. 如果没有，将新发现追加到文件末尾，格式：
   ```
   [序号]. [规律描述]（发现于 {DATE}）
   ```

**检查二：是否有新的选股规则修正？**

回顾本次个股筛选，是否发现某些技术面/题材面条件在今天的市场中失效？
如有，追加到 `evolution/selection_rules.md`，格式：
```
[序号]. [规则描述]（添加于 {DATE}）
```

**如果什么都没有发现**，明确输出：
```
知识库积累：本次复盘未发现新规律/陷阱，知识库无更新。
```
