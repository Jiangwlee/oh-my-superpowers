# A-Share Review Planner Skill 设计文档

> 日期：2026-02-17
> 状态：设计完成，待实现
> 范围：A股每日复盘、选股、交易计划制定的 Agent Skill

---

## 1. 项目背景与目标

### 1.1 背景

用户是一位A股趋势交易者，交易风格为**趋势为主、题材为辅**：
- 趋势股：按周/月持股，市场缺乏主线时100%趋势交易
- 题材股：主线题材形成时积极参与，可将8成仓位给到题材，按日持股，一般不超过两周

用户已有多个数据采集脚本（smartrade/smartrade-adk 项目），以及一个已部署运行的趋势选股 Skill（`a-share-trend-scanner`）。但这些工具分散，缺乏统一的分析和决策框架。

### 1.2 目标

构建一个 Agent Skill，实现：
1. **每日复盘**：采集多源数据，由 LLM 进行市场环境分析、题材线索识别
2. **选股与交易计划**：基于复盘结论，筛选候选标的并制定明确的交易计划
3. **可进化策略**：策略以自然语言模板存储，LLM 每次复盘时可读取并调整
4. **历史经验注入**：为未来的"交易诊断 Skill"预留接口，形成进化闭环

### 1.3 非目标（当前版本不做）

- 实时行情监控和盘中自动执行（需要常驻进程，不适合 Skill）
- 风控规则引擎（纯确定性逻辑，用代码实现而非 LLM）
- broker API 对接和自动下单（后续独立 Skill 或服务）
- 交易诊断与归因分析（第二个 Skill，待交易数据积累后开发）

---

## 2. 设计理念

### 2.1 核心原则：LLM 做判断，代码做执行

明确区分 LLM 擅长和不擅长的事情：

| 类别 | LLM 适合 | 代码适合 |
|------|---------|---------|
| 数据采集 | 非结构化信息理解（新闻、帖子） | API 调用、数据拉取 |
| 数据分析 | 跨数据源归因推理、题材识别、模糊判断 | 技术指标计算、统计汇总 |
| 交易决策 | 选股理由、入场逻辑、策略调整 | 精确价格计算、仓位计算 |
| 执行 | 异常情况判断 | 条件触发、API 下单、风控校验 |

**结论**：Skill 的 scripts 负责数据采集和结构化，LLM 负责分析推理和决策。

### 2.2 不重复造轮子

已有的 `a-share-trend-scanner` Skill 包含完整的趋势评分体系（1467行 Python），本 Skill 不重写趋势分析逻辑，而是：
- 调用 `a-share-trend-scanner` 获取趋势股筛选结果
- 在其基础上叠加舆情、新闻、大盘环境等增量数据
- 由 LLM 综合所有信息做出最终决策

### 2.3 数据是一次性燃料

每次复盘采集的数据（舆情帖子、新闻、行情快照）是即时性的，没有长期存储价值。设计上：
- 临时存储到 `/tmp` 或 `.cache` 目录
- 每次运行自动清理旧数据
- LLM 分析后的**结论**（交易计划、策略调整）才是持久化的产出

### 2.4 策略是可进化的自然语言

止盈、止损、持股周期等策略不是硬编码的 if-else，而是自然语言描述的规则模板。LLM 每次复盘时：
1. 读取当前策略
2. 结合实际交易表现和市场环境
3. 判断是否需要调整
4. 更新策略文件并记录修改原因

---

## 3. 数据源全景

### 3.1 已有数据源（a-share-trend-scanner 提供）

| 数据源 | 数据类型 | 说明 |
|-------|---------|------|
| 东方财富 | 人气榜前200 | 选股基础池，使用 xuangu 接口支持200只 |
| 同花顺 | 涨停板/连板天梯/最强板块 | 市场情绪指标 |
| 金融界 | 日K线行情 | 趋势判断的技术数据 |

### 3.2 本 Skill 新增数据源

#### 3.2.1 东方财富人气榜前200（增强版）

```
GET https://data.eastmoney.com/dataapi/xuangu/list
参数：
  st=CHANGE_RATE&sr=-1&ps=50&p={page}
  sty=SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,NEW_PRICE,CHANGE_RATE,
      VOLUME_RATIO,HIGH_PRICE,LOW_PRICE,PRE_CLOSE_PRICE,VOLUME,DEAL_AMOUNT,
      TURNOVERRATE,POPULARITY_RANK
  filter=(POPULARITY_RANK>0)(POPULARITY_RANK<=200)
  source=SELECT_SECURITIES&client=WEB&hyversion=v2
说明：分页获取，每页50条，最多200条。这是选股的基础——只看人气榜前200。
```

#### 3.2.2 金融界新闻（4个频道）

统一接口：`POST https://gateway.jrj.com/jrj-news/news/queryNewsList`

| 频道 | channelNum | infoCls | 用途 |
|------|-----------|---------|------|
| A股头条 | 010 | 001062 | 每日重要新闻汇总 |
| 市况直击 | 010 | 001140 | 盘中实时市况 |
| 机会情报 | 010 | 001161 | 题材/事件催化剂识别 |
| 每日财经 | 103 | 001116 | 宏观/政策信息 |

请求体格式：
```json
{"sortBy":1,"pageSize":20,"makeDate":"","channelNum":"010","infoCls":"001062"}
```

#### 3.2.3 金融界 7x24 要闻

```
POST https://gateway.jrj.com/jrj-news/news/queryNewsFlash
```

#### 3.2.4 金融界重要新闻（按日期）

```
GET https://stockjs.jrj.com.cn/share/news/yaowen/yw{YYYY-MM-DD}.js?_={timestamp}
Headers: Referer: https://24h.jrj.com.cn/
```

#### 3.2.5 大盘云图（板块结构 + 个股权重）

```
POST https://gateway.jrj.com/quot-dpyt/v1/market
Body: {"mkt":1}
Headers: Origin: https://summary.jrj.com.cn, Referer: https://summary.jrj.com.cn/

返回结构：
{
  "code": 20000,
  "data": {
    "td": "20260213",          // 交易日期
    "indus": [                  // 31个一级行业
      {
        "sid": 270000,          // 行业唯一ID
        "name": "电子",
        "scale": 12.74,         // 市值占比权重
        "children": [           // 二级子行业
          {
            "sid": 270100,
            "name": "半导体",
            "children": [       // 个股列表
              {
                "code": "688041",
                "mkt": 1,       // 1=SH, 2=SZ
                "name": "海光信息",
                "scale": 10.72, // 行业内权重
                "sid": 1688041  // 个股唯一ID，用于关联资金流向
              }
            ]
          }
        ]
      }
    ]
  }
}
```

#### 3.2.6 资金流向（通过 sid 关联云图）

```
POST https://gateway.jrj.com/quot-dpyt/v1/hq
Body: {"column":"netin"}
Headers: 同上

返回结构：
{
  "code": 20000,
  "data": {
    "td": "20260213",
    "tm": "155957",
    "hqs": {
      "1688041": {"np": 206.0, "var": -64742588.0},
      // key = sid（与 market API 的 sid 字段对应）
      // np = 最新价
      // var = 资金净流入金额（column=netin时）
    }
  }
}

关联方式：
  market.indus[].children[].children[].sid = hq.hqs 的 key
  可按行业/子行业聚合 var，得到板块级别资金净流入排名
```

#### 3.2.7 最近交易日期

```
POST https://gateway.jrj.com/quot-feed/tradedate
Body: （空）
Headers: Origin: https://summary.jrj.com.cn, Referer: https://summary.jrj.com.cn/
```

#### 3.2.8 淘股吧精华帖（舆情）

```
数据源：https://www.tgb.cn/jinghua/1-1
采集方式：HTML 解析（BeautifulSoup）
输出：帖子标题、正文、作者、日期、评论数、浏览数
用途：判断市场情绪、题材强度、市场龙头个股
重要性：最重要的舆情来源
```

### 3.3 已有但暂不纳入的数据源

| 数据源 | 原因 |
|-------|------|
| 东方财富资金净流入/流出 | 大盘云图已覆盖 |
| 新浪成交量排行 | 优先级低 |
| 搜狐周涨幅排行 | HTML 解析不稳定 |
| 东方财富股吧个股帖子 | 可按需后续加入 |

---

## 4. 趋势判断体系（来自 a-share-trend-scanner）

### 4.1 趋势硬门槛

一只股票被判定为上升趋势，必须同时满足：

1. **MA10 > MA20 占比 > 60%**：近20日中，MA10 高于 MA20 的天数占比超过60%
2. **MA20 持续抬升**：近20日中 MA20 逐日抬升天数 >= 15
3. **MA10 连续抬高**：连续10个交易日 MA10 逐日抬高
4. **排除顶部形态**：近10日收盘全低于30日最高收盘 且 MA5 < MA20（死叉状态）

### 4.2 评分体系（5维度 → 100分 → 星级）

| 维度 | 权重 | 衡量内容 |
|------|------|---------|
| 趋势 | 30% | 30日/60日涨幅 |
| 支撑 | 25% | MA5/MA10/MA20 站上天数 |
| 风险 | 15% | 跌破均线次数和连续跌破天数 |
| 稳健 | 20% | 进攻强度(涨8%天数) + 防守强度(跌5%天数) |
| 情绪 | 10% | 3/5/10/30日斜率加速结构 |

最终筛选：趋势通过 + 星级 >= 4星（总分 >= 75）

### 4.3 情绪因子（斜率加速结构）

通过 3日/5日/10日/30日 收盘价线性斜率的加速关系判断：

| 等级 | 标签 | 颜色 | 条件 |
|------|------|------|------|
| L5 | 主升强化 | 🔴 | 短线斜率严格递增 + 加速分 >= 8.2 |
| L4 | 情绪偏强 | 🟠 | 短线强于长线 + 加速分 >= 6.0 |
| L3 | 稳健上行 | 🟢 | 短线总体上行 + 加速分 >= 4.8 |
| L2 | 中性偏弱 | 🔵 | 短线强但结构分歧 |
| L1 | 情绪不佳 | ⚪ | 短线未明显强于长期 |

### 4.4 交易信号（均线偏离）

- **卖出**：最新价偏离 MA5 >= 15%
- **买入**：最新价回调至 MA5/MA10/MA20 附近（±1%）
- **观察**：未触发条件

### 4.5 现有脚本的改进空间

| 方面 | 现状 | 可改进 |
|------|------|-------|
| 选股池 | 仅基于人气榜+技术面 | 叠加舆情/新闻/题材维度 |
| 市场环境 | 无大盘判断 | 加入指数/成交额/板块涨跌 |
| 题材识别 | 仅同花顺板块数据 | 加入新闻+淘股吧热帖 |
| 策略建议 | 固定的均线偏离规则 | 可进化的自然语言策略 |
| 输出 | 排名表格 | 完整交易计划 |

---

## 5. Skill 架构设计

### 5.1 目录结构

```
skills/a-share-review-planner/
├── SKILL.md                        # 技能主文件：指导 LLM 完成复盘→选股→计划
├── scripts/
│   ├── collect_sentiment.py        # 一键采集增量数据入口
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── taoguba.py              # 淘股吧精华帖
│   │   ├── news.py                 # 金融界新闻（4频道 + 7x24 + 重要新闻）
│   │   ├── market_overview.py      # 大盘云图 + 资金流向 + 板块聚合
│   │   └── trade_date.py           # 最近交易日期
│   └── utils/
│       ├── __init__.py
│       └── http_client.py          # 统一 HTTP 客户端 + 重试
├── references/
│   └── analysis-framework.md       # LLM 分析思考模板（详细版）
├── strategy/                       # 可进化策略目录
│   ├── default.yaml                # 默认策略模板（不可修改，作为基线）
│   └── active.yaml                 # 当前生效策略（LLM 可修改）
└── evolution/                      # 历史经验注入目录
    ├── feedback.md                 # 最近一次交易诊断的改进建议
    ├── selection_rules.md          # 累积的选股规则修正
    └── known_pitfalls.md           # 已知的交易陷阱
```

### 5.2 工作流

```
用户触发（收盘后调用）
    │
    ▼
阶段1: 数据采集（scripts）
    ├─ 调用 a-share-trend-scanner 获取趋势股报告
    ├─ 运行 collect_sentiment.py 采集增量数据：
    │   ├─ 淘股吧精华帖
    │   ├─ 金融界新闻（4频道）
    │   ├─ 大盘云图 + 资金流向
    │   └─ 最近交易日期
    └─ 输出：临时目录下的结构化 JSON/MD 文件
    │
    ▼
阶段2: LLM 读取数据
    ├─ 读取趋势股扫描报告
    ├─ 读取增量数据文件
    ├─ 读取当前策略（strategy/active.yaml）
    └─ 读取历史经验（evolution/*.md，如存在）
    │
    ▼
阶段3: LLM 分析（按 analysis-framework.md）
    ├─ 第一步：市场环境判断
    ├─ 第二步：题材线索识别
    ├─ 第三步：个股筛选
    ├─ 第四步：交易计划制定
    ├─ 第五步：风险检查
    └─ 第六步：策略回顾与微调
    │
    ▼
阶段4: 输出
    ├─ 交易计划（Markdown，持久化）
    ├─ 策略更新（如有调整，更新 active.yaml）
    └─ 呈现给用户
```

### 5.3 数据流图

```
                    ┌──────────────────┐
                    │ a-share-trend-   │
                    │ scanner          │
                    │ (已有 Skill)      │
                    └───────┬──────────┘
                            │ report.md + JSON
                            ▼
┌─────────────┐    ┌──────────────────┐    ┌───────────────┐
│ 淘股吧热帖   │───▶│                  │    │ strategy/     │
│ 金融界新闻   │───▶│   LLM 分析引擎    │◀───│ active.yaml   │
│ 大盘云图     │───▶│                  │    │ (当前策略)     │
│ 资金流向     │───▶│                  │    └───────────────┘
└─────────────┘    │                  │    ┌───────────────┐
  scripts 采集      │                  │◀───│ evolution/    │
                    │                  │    │ *.md          │
                    └───────┬──────────┘    │ (历史经验)     │
                            │               └───────────────┘
                            ▼
                    ┌──────────────────┐
                    │ 输出              │
                    │ ├─ 交易计划.md    │
                    │ └─ 策略更新       │
                    └──────────────────┘
```

---

## 6. LLM 分析框架设计

LLM 按以下顺序思考，每个步骤都必须有明确结论。

### 第一步：市场环境判断

**输入**：
- 大盘云图（31个行业涨跌）
- 板块资金净流入排名
- 涨跌停统计（涨停数/跌停数/连板高度）
- 大盘指数涨跌（沪指、深指、创业板、北交所、美股道琼斯）—— 一般可从新闻/舆情中获取
- 市场总成交额 —— 一般可从新闻/舆情中获取

**输出**：
- 市场强弱：强 / 中 / 弱
- 主线风格：题材驱动 / 趋势主导 / 混沌轮动
- 仓位建议：激进(8成) / 标准(5成) / 防守(2成以下)

### 第二步：题材线索识别

**输入**：
- 同花顺最强板块 + 连板天梯
- 金融界 A股头条 + 机会情报
- **淘股吧精华帖**（最重要的舆情来源，用于判断市场情绪、题材强度、龙头个股）

**输出**：
- 当前主线题材（如有）：名称、持续天数、核心标的、龙头股
- 新兴题材线索：名称、催化事件、参与价值评估
- 衰退题材：名称、衰退信号
- 市场情绪判断：根据淘股吧热帖的讨论热度和方向

### 第三步：个股筛选

**输入**：
- a-share-trend-scanner 的趋势股报告（人气榜前200 + 趋势评分）
- 第一步和第二步的结论

**筛选逻辑**：
- 趋势股：从 trend-scanner 报告中筛选 4星及以上的趋势股
- 题材股：在人气榜前200中，与第二步识别的主线/新兴题材相关的个股
- 筛选数量：5-10只候选

**每只输出**：
- 选股理由
- 所属类型（趋势/题材）
- 所属题材（如适用）
- 风险点

### 第四步：交易计划制定

**输入**：
- 第三步筛选的候选股
- 当前策略（strategy/active.yaml）
- 当前持仓情况（如用户提供）

**每只候选股输出**：
- 操作类型：趋势持有 / 题材短线
- 入场条件：什么情况下买入（参考策略模板）
- 目标仓位：金额
- 止盈条件（参考策略模板）
- 止损条件（参考策略模板）
- 持有周期预期（参考策略模板）

### 第五步：风险检查

- 持仓集中度：是否同一板块过多
- 与昨日计划的差异：换了哪些股、为什么
- 当前持仓中需要调整的标的
- 整体仓位是否符合市场环境判断

### 第六步：策略回顾与微调

**输入**：
- 当前策略（strategy/active.yaml）
- 近期实际交易表现（如用户提供）
- 历史经验文件（evolution/*.md）

**判断**：
- 当前策略是否需要调整？
- 如果需要，修改了什么？为什么？
- 更新 active.yaml 并在末尾追加修改记录

---

## 7. 可进化策略模板设计

### 7.1 默认策略（strategy/default.yaml）

作为基线，不可修改。LLM 可以参考但不能覆盖。

```yaml
trend_stock:
  description: "趋势股交易策略"
  holding_period: "按周持股，强趋势可持续1-2个月"
  entry: "回调至MA10附近时介入，或突破前高时追入"
  stop_loss: "跌破MA20且3日内未收回"
  take_profit: "偏离MA5超过15%时减仓，或趋势评分降至3星以下"
  position: "单只不超过总仓位20%"

theme_stock:
  description: "题材股交易策略"
  holding_period: "按日持股，一般不超过2周"
  entry: "题材爆发首日或次日低吸，需龙头未见顶"
  stop_loss: "题材板块当日跌幅>3%，或个股开板未回封"
  take_profit: "题材出现明显分歧日减仓，龙头见顶全部清仓"
  position: "题材主线时可到8成，单只不超过总仓位15%"

market_position:
  strong: "6-8成仓位"
  neutral: "3-5成仓位"
  weak: "1-2成仓位或空仓"
```

### 7.2 活动策略（strategy/active.yaml）

初始从 default.yaml 复制，LLM 可修改。每次修改需在末尾记录：

```yaml
# ... 策略内容（与 default 相同结构）...

evolution_log:
  - date: "2026-02-18"
    change: "趋势股止损改为'跌破MA10且量能放大2倍以上'"
    reason: "近期MA20止损太慢，导致利润回吐过多（2/15 XX股 -8%）"
  - date: "2026-02-20"
    change: "题材股持仓上限从15%提高到20%"
    reason: "主线强势时15%仓位限制导致错过主升浪收益"
```

### 7.3 进化机制

策略进化不是自动发生的，需要触发条件：

1. **被动进化**：用户提供实际交易结果后，LLM 对比计划 vs 实际，提出策略调整建议
2. **主动进化**：每次复盘第六步中，LLM 检查当前策略是否与市场环境匹配
3. **历史注入**：未来的"交易诊断 Skill"会生成 `evolution/feedback.md`，本 Skill 在分析前读取

---

## 8. 历史经验注入接口

### 8.1 目录结构

```
evolution/
├── feedback.md           # 最近一次交易诊断反馈
├── selection_rules.md    # 累积的选股规则修正
└── known_pitfalls.md     # 已知的交易陷阱
```

### 8.2 文件格式约定

**feedback.md**（由交易诊断 Skill 生成）：
```markdown
# 交易诊断反馈 2026-02-16

## 选股问题
- XX股选股依据是题材催化，但实际题材持续性不足，建议...

## 择时问题
- 趋势股入场偏晚，多在MA5附近追入而非MA10回调，建议...

## 执行问题
- 止损执行不坚决，XX股触发止损条件后仍持有3天，建议...
```

**selection_rules.md**（累积修正）：
```markdown
# 选股规则修正

1. 排除近30日换手率 < 1% 的个股（流动性不足）
2. 题材股需至少有2个涨停板确认板块效应
3. 避免选择已连续涨停3天以上的个股（追高风险）
```

**known_pitfalls.md**（已知陷阱）：
```markdown
# 已知交易陷阱

1. 春节/长假前最后两个交易日不宜新建仓
2. 题材股分歧转一致后的第二天往往是最高点
3. 趋势股在业绩预告窗口期波动加大，需降低仓位
```

### 8.3 读取时机

SKILL.md 中明确指示 LLM：
> 在进入分析阶段前，先检查 `evolution/` 目录下是否有文件。如有，先完整阅读，将其中的建议纳入后续分析判断中。

---

## 9. 输出格式设计

### 9.1 交易计划（主输出）

Markdown 格式，人可读，且为未来诊断 Skill 提供对比素材。

```markdown
# 交易计划 2026-02-18

## 一、市场环境
- 强弱：中偏强
- 风格：题材驱动（机器人主线延续第3天）
- 建议仓位：6成
- 关键指数：沪指 +0.5%，创业板 +1.2%，道琼斯 -0.3%
- 成交额：1.2万亿（较昨日放量15%）

## 二、题材跟踪
| 题材 | 状态 | 核心标的 | 龙头 | 备注 |
|------|------|---------|------|------|
| 机器人 | 主线延续 | xxx, yyy | zzz | 第3天，注意分化 |
| AI算力 | 新兴 | aaa | - | 催化：某政策发布 |
| 新能源 | 衰退 | - | - | 龙头已见顶 |

## 三、候选标的

### 1. 000001.SZ 某某股份 [趋势]
- **趋势评分**：⭐⭐⭐⭐⭐ 92.3分 🔴L5
- **选股理由**：MA10连续抬升20天，60日涨幅35%，板块资金持续流入
- **入场条件**：明日若回调至MA10（约X元）附近可介入
- **目标仓位**：5000元
- **止盈**：偏离MA5超过15%时减仓
- **止损**：跌破MA20且3日内未收回
- **持有周期**：1-2周
- **风险点**：近期量能有萎缩迹象

### 2. 300002.SZ 某某科技 [题材-机器人]
- ...

## 四、持仓调整建议
- XX股：建议减仓至5成，题材板块出现分歧
- YY股：继续持有，趋势完好

## 五、风险提示
- 板块集中度：机器人相关占比50%，偏高
- 明日关注：XX会议结果可能影响市场

## 六、策略变更记录
- 本次无策略调整 / 调整了XXX（原因：...）
```

### 9.2 存储路径

```
data/plans/{YYYY-MM-DD}/review_plan.md
```

---

## 10. 与现有系统的关系

### 10.1 与 a-share-trend-scanner 的关系

```
a-share-trend-scanner (已有)        a-share-review-planner (新建)
┌───────────────────────┐          ┌───────────────────────┐
│ 输入：人气榜前200      │          │ 输入：                 │
│ 处理：K线拉取+趋势评分  │ ──输出──▶│   趋势报告 (scanner)  │
│ 输出：趋势股排名报告    │          │   + 新闻/舆情/大盘     │
│                       │          │ 处理：LLM 综合分析     │
│ 定位：纯数据+算法      │          │ 输出：交易计划         │
│ 不含 LLM 判断         │          │                       │
└───────────────────────┘          │ 定位：LLM 推理决策     │
                                   └───────────────────────┘
```

### 10.2 与未来的交易诊断 Skill 的关系

```
a-share-review-planner              a-share-trade-doctor (未来)
┌───────────────────────┐          ┌───────────────────────┐
│ 输出：交易计划          │ ──对比──▶│ 输入：                 │
│ 读取：evolution/*.md   │ ◀─反馈──│   交易计划 + 实际成交   │
│                       │          │ 处理：逐笔归因分析      │
│                       │          │ 输出：                 │
│                       │          │   evolution/feedback   │
│                       │          │   策略调整建议          │
└───────────────────────┘          └───────────────────────┘
```

### 10.3 与 docs/openclaw/ 旧设计的关系

`docs/openclaw/` 下的运行时设计（agent.runtime.yaml、event-routing.yaml 等）面向的是一个**完整的自动化交易引擎**，包含实时事件循环、WebSocket 连接、broker 对接等。当前 Skill 聚焦于**复盘决策**这个子集，不依赖也不替代那套设计。未来如果要做自动执行，可以在那套设计的基础上迭代，但应确保：
- 实时部分由代码/服务实现，不由 LLM Skill 承担
- 风控规则由代码实现，不由 LLM 判断
- LLM Skill 只负责"出计划"，代码负责"按计划执行"

---

## 11. Scripts 技术设计

### 11.1 collect_sentiment.py（主入口）

```
用法：
python3 scripts/collect_sentiment.py \
  --date 2026-02-17 \
  --output-dir /tmp/review/2026-02-17 \
  --news-count 20 \
  --taoguba-count 20

功能：
1. 获取最近交易日期
2. 并发采集所有数据源
3. 输出结构化 JSON 文件到 output-dir

输出文件：
  {output-dir}/
  ├── trade_date.json           # {"trade_date": "20260217"}
  ├── taoguba_hot.json          # 淘股吧精华帖列表
  ├── news_headline.json        # A股头条
  ├── news_realtime.json        # 市况直击
  ├── news_opportunity.json     # 机会情报
  ├── news_daily.json           # 每日财经
  ├── market_cloud.json         # 大盘云图（行业→子行业结构）
  ├── capital_flow.json         # 资金流向（按板块聚合后的排名）
  └── collection_summary.json   # 采集摘要（各源状态和数量）
```

### 11.2 技术约束

- **纯标准库实现**：不依赖第三方包（urllib + json），与 trend-scanner 保持一致
- **禁止正则解析 HTML**：淘股吧爬虫使用 BeautifulSoup 或 Openclaw 内置 browser 工具
- **统一重试机制**：HTTP 请求失败自动重试3次，指数退避
- **并发采集**：使用 ThreadPoolExecutor 并发拉取多个数据源
- **容错设计**：单个数据源失败不影响其他源，collection_summary.json 记录各源状态

### 11.3 关于淘股吧的采集方式

淘股吧是 HTML 页面，有两种采集方式：

**方案A（推荐）**：使用 Openclaw 内置 browser 工具
- SKILL.md 中指导 LLM 用 browser 工具访问淘股吧
- 优点：不怕 JS 渲染、不怕反爬
- 缺点：依赖 Openclaw 环境

**方案B（备选）**：Python 脚本 + BeautifulSoup
- 与 smartrade-adk 中已有的 `tgb_jinghua.py` 类似
- 优点：独立运行，不依赖 Openclaw
- 缺点：需要安装 beautifulsoup4，HTML 结构变化时可能失效

**决策**：先实现方案B（复用已有代码），同时在 SKILL.md 中提供方案A作为备选指引。如果方案B失效，LLM 可自动切换到方案A。

---

## 12. 开发计划

### Phase 1：MVP（最小可用版本）

1. 实现 `collect_sentiment.py` 及各 fetcher
2. 编写 `SKILL.md`（核心分析流程）
3. 编写 `references/analysis-framework.md`（详细分析模板）
4. 创建 `strategy/default.yaml` 和 `strategy/active.yaml`
5. 创建 `evolution/` 目录及空文件
6. 端到端测试：采集数据 → LLM 分析 → 输出交易计划

### Phase 2：优化

1. 完善淘股吧采集（方案A/B双路径）
2. 优化分析框架，根据实际使用反馈调整
3. 增加与 a-share-trend-scanner 的更紧密集成

### Phase 3：进化闭环

1. 开发交易诊断 Skill（`a-share-trade-doctor`）
2. 实现 evolution/ 目录的自动更新
3. 建立"计划 → 执行 → 诊断 → 改进"的完整闭环

---

## 附录

### A. 已有代码资产清单

| 项目 | 路径 | 可复用内容 |
|------|------|-----------|
| smartrade | `github_cache/smartrade/crawlers/` | 东方财富人气榜、金融界龙虎榜/K线、同花顺涨跌停/板块/连板、日期工具 |
| smartrade-adk | `github_cache/smartrade-adk/backend/crawlers/` | 淘股吧精华帖（异步版）、同花顺热门板块（异步+报告）、金融界K线（异步版）、HTTP客户端基础设施 |
| a-share-trend-scanner | `43.138.150.96:/root/.openclaw/workspace/skills/` | 完整的趋势评分脚本（1467行），已部署运行 |

### B. API 接口速查表

| 接口 | 方法 | URL | 关键参数 |
|------|------|-----|---------|
| 人气榜 | GET | data.eastmoney.com/dataapi/xuangu/list | filter, ps, p |
| A股头条 | POST | gateway.jrj.com/jrj-news/news/queryNewsList | channelNum=010, infoCls=001062 |
| 市况直击 | POST | 同上 | infoCls=001140 |
| 机会情报 | POST | 同上 | infoCls=001161 |
| 每日财经 | POST | 同上（channelNum=103） | infoCls=001116 |
| 7x24要闻 | POST | gateway.jrj.com/jrj-news/news/queryNewsFlash | - |
| 重要新闻 | GET | stockjs.jrj.com.cn/share/news/yaowen/yw{date}.js | date |
| 交易日期 | POST | gateway.jrj.com/quot-feed/tradedate | - |
| 大盘云图 | POST | gateway.jrj.com/quot-dpyt/v1/market | mkt=1 |
| 资金流向 | POST | gateway.jrj.com/quot-dpyt/v1/hq | column=netin |
| 淘股吧 | GET | www.tgb.cn/jinghua/1-1 | HTML 页面 |
