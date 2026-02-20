# A股复盘 Skill 升级方案 v2

> 文档版本：v1.0
> 讨论来源：vibe coding discussion `20260220-042011-a-share-skill`
> 状态：已收敛，可开发

---

## 一、背景与现状

### 1.1 Skill 定位

`a-share-review-planner` 是一个每日复盘规划 Skill，运行于 OpenClaw Agent 框架。用户触发"复盘"后，Skill 自动采集多源市场数据、经 LLM 分析判断、生成含入场/止盈/止损/仓位的交易计划，并推送 Telegram PDF。

**核心原则**：LLM 做判断（分析/推理/决策），代码做执行（采集/计算/校验）。

### 1.2 现有工作流

```
触发
  → collect_sentiment.py（并发采集：新闻/淘股吧/板块资金/同花顺/金融界）
  → 阶段2：LLM 读取多文件整理关键信息
  → 阶段3：LLM 9步分析（市场环境/题材/选股/深度分析/计划/风控/策略/知识库/精华言论）
  → candidates.json（LLM 生成）
  → risk_check.py（硬性规则校验）
  → 阶段4：输出 report.md（纯 Markdown）
  → report_to_image.py → PDF
  → Telegram
```

### 1.3 已有数据源

| 数据源 | 内容 | 文件 |
|--------|------|------|
| 金融界新闻 | 头条/直击/情报/财经/7×24 | `news_*.json` |
| 板块资金 | 净流入前5+后5 | `market_sectors.json` |
| 淘股吧 | 精华/热讨/推荐，含正文 | `taoguba_*.json` |
| 同花顺 | K线+涨停评分（人气榜前200） | `ths_report.md`, `ths_snapshot.json` |
| 金融界 | 大盘云图/资金流向 | `market_overview.json` |
| jvQuant（可选） | 账户持仓 | `broker_account.json` |
| a-share-trend-scanner | 趋势评分体系（1467行，已部署） | `trend_scan.json` |

---

## 二、问题诊断

通过讨论，识别出四个核心瓶颈：

### 2.1 选股（最大瓶颈）

**现状**：选股信号 = 价格/量能（趋势评分）+ 社区舆情 + 新闻。
**缺口**：缺少机构资金方向信号（北向净流入、主力净流入）。
**影响**：在「热度」阶段选股，比机构资金滞后一个信号层，容易追高。

### 2.2 择时（中等瓶颈）

**现状**：LLM 靠新闻文本主观判断市场强/中/弱，无量化依据。
**影响**：同样的市场两次分析可能结论不同，仓位建议不稳定。

### 2.3 复盘（战略短板）

**现状**：`evolution/` 目录无历史积累；报告输出纯 Markdown，程序无法解析。
**影响**：每次从零出发，无法自动比对历史推荐的实际收益，策略进化缺乏数据支撑。

### 2.4 自进化（前提未满足）

**现状**：ProposalJudge 机制存在，但无历史决策记录和结果反馈作为燃料。
**根因**：复盘问题未解决，自进化无从启动。

---

## 三、升级需求

### 3.1 P0：可闭环最小集

以下三项是本次升级的核心，互为前置依赖：

1. **LLM 双层输出**：报告末尾新增结构化 JSON block，机器可直接解析（解决复盘数据源问题）
2. **资金面 Fetcher**：接入北向资金 + 主力净流入 Top20（解决选股信号缺口）
3. **决策日志闭环**：`decision_logger.py` 记录每次推荐，`diagnose.py` 回填实际涨跌（建立自进化数据基础）

### 3.2 P1：知识库持续完善

- `evolution/feedback.md` 由 `diagnose.py` 自动写入，形成可读性反馈报告
- 胜率/超额收益数据积累后，支持 ProposalJudge 的量化依据

### 3.3 不在本次范围内

- 龙虎榜 fetcher（P2）
- 接入 mcp-cn-a-stock 公开 MCP 服务（P2）
- ProposalJudge 的复杂提案博弈（前提未满足）

---

## 四、技术设计

### 4.1 升级后工作流

```
触发
  → [NEW] 生成 run_id
  → collect_sentiment.py（原有，并发采集）
  → [NEW] funding_fetcher.py（可选：北向资金 + 主力净流入）
  → 阶段2：LLM 读取多文件（新增读取 funding 数据）
  → 阶段3：LLM 9步分析（同原有）
  → [MODIFIED] candidates.json（格式升级为 schema_v1）
  → [NEW] validate_output.py（schema 校验）
  → risk_check.py（原有硬性规则校验）
  → [NEW] decision_logger.py（写入 decision_log.jsonl）
  → 阶段4：输出 report.md（新增末尾 JSON block）
  → report_to_image.py → PDF → Telegram（原有）

（独立进程，T+1/T+5）
  → diagnose.py → 回填 outcome → evolution/feedback.md
```

### 4.2 run_id 规范

**格式**：`{YYYYMMDD}-{strategy_version}-{HHMMSS}`

示例：`20260220-v1.0-143052`

**生成时机**：在调用 LLM 之前，由采集脚本或工作流入口生成。

**写入位置**：
1. 报告 Markdown 头部注释：`<!-- run_id: 20260220-v1.0-143052 -->`
2. JSON block 顶层字段 `run_id`
3. `decision_log.jsonl` 每条记录的键

**strategy_version 读取**：
- 主来源：`strategy/active.yaml` 中的 `strategy_version` 字段（或兼容 `version`）
- fallback：`v0`（同时在 `risk_flags` 中追加 `strategy_version_fallback: true`）

### 4.3 JSON Schema v1

LLM 分析完成后，`candidates.json` 升级为以下格式。所有核心字段**不得删除或重命名**（向后兼容约束），新增字段必须放入 `extra`。

```json
{
  "run_id": "20260220-v1.0-143052",
  "as_of_date": "2026-02-20",
  "market": {
    "regime": "strong",
    "sentiment_score": 72,
    "trend_signals": {
      "limit_up_count": 85,
      "limit_down_count": 12,
      "limit_up_down_ratio": 7.08,
      "volume_ratio": 1.35,
      "main_theme_days": 3
    }
  },
  "funding": {
    "northbound_net": 12.5,
    "main_force_top20": [
      {"code": "300750", "name": "宁德时代", "net_inflow": 8.2}
    ],
    "data_degraded": false
  },
  "themes": [
    {
      "name": "人形机器人",
      "stage": "accelerating",
      "leaders": ["688272", "300785"],
      "catalyst": "特斯拉Optimus量产消息"
    }
  ],
  "candidates": [
    {
      "code": "688272",
      "name": "联影医疗",
      "score": 4.2,
      "action": "buy",
      "thesis_short": "机器人零部件龙头，趋势评分4星",
      "risk_note": "题材分歧期慎追高"
    }
  ],
  "risk_flags": {
    "data_degraded": false,
    "output_schema_invalid": false,
    "strategy_version_fallback": false
  },
  "execution": {
    "total_capital": 100000,
    "market_mode": "strong",
    "account_mode": "normal",
    "position_advice": "standard"
  },
  "kpi": {
    "candidate_count": 5,
    "theme_count": 3,
    "funding_coverage": 1.0
  }
}
```

#### 核心字段约束

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `run_id` | string | 必填 | 格式见 4.2 |
| `as_of_date` | string | 必填 | YYYY-MM-DD |
| `market.regime` | enum | 必填 | `strong` / `neutral` / `weak` |
| `funding.data_degraded` | bool | 必填 | AKShare 失败时为 `true` |
| `candidates[].action` | enum | 必填 | `buy` / `hold` / `sell` / `watch` |
| `candidates[].thesis_short` | string | 必填 | ≤ 30 字，LLM prompt 强制约束 |
| `candidates[].risk_note` | string | 必填 | ≤ 30 字 |

### 4.4 LLM 输出格式变更

**变更内容**：`report.md` 末尾新增 JSON fenced block，`candidates.json` 同步写出。

**报告末尾格式**（阶段4新增保存命令）：

```markdown
<!-- run_id: {run_id} -->

[原有报告内容...]

```json
{完整 schema_v1 JSON 对象}
```
```

**prompt 约束（新增到阶段3末尾）**：
- 输出 JSON 时，`thesis_short` 和 `risk_note` 各不超过 30 字
- `action` 必须从 `buy/hold/sell/watch` 中选择，不得使用其他词
- JSON 必须是有效的单个对象，不得包含注释或省略号

### 4.5 校验失败处理

| 情形 | 处理方式 |
|------|----------|
| JSON 解析失败 | `run_failed=true` + `output_schema_invalid=true`，继续输出人类可读报告，**不写** decision_log |
| 核心字段缺失 | 同上 |
| `funding.data_degraded=true` | 报告"风险提示"章节显示"当日资金信号缺失，不建议提高仓位" |
| `strategy_version` 读取失败 | fallback `v0`，`risk_flags.strategy_version_fallback=true` |
| AKShare 不可用 | 降级到 trend+sentiment 旧评分，`funding.data_degraded=true`，主流程不阻断 |

---

## 五、新增模块设计

### 5.1 `scripts/validate_output.py`

**职责**：纯标准库校验 candidates.json 是否符合 schema_v1 核心字段约束。

**接口**：
```bash
# 正常使用（由工作流调用）
python3 validate_output.py --input /tmp/a-share-review/{DATE}/candidates.json

# 自测
python3 validate_output.py --test
```

**返回**：
- exit code 0：校验通过或可降级继续（通过 `--strict` 可改为失败时 exit 1）
- stdout：JSON 格式校验结果 `{"ok": true/false, "errors": [...], "warnings": [...]}`

**校验规则**（纯字段存在性检查，不引入 jsonschema 依赖）：
1. 顶层必填字段存在性
2. `market.regime` 值在枚举范围内
3. `candidates` 非空数组，每项包含必填字段
4. `candidates[].action` 值在枚举范围内

### 5.2 `scripts/fetchers/funding.py`

**职责**：采集北向资金净流入 + 主力净流入 Top20。

**依赖**：可选 `akshare>=1.15.0`；不可用时自动 fallback，返回 `{"data_degraded": true}`。

**接口**（被 `collect_sentiment.py` 调用）：

```python
def fetch_funding(date: str | None = None) -> dict:
    """采集资金面数据。

    Args:
        date: 交易日期 YYYYMMDD，None 表示最新。

    Returns:
        {
          "northbound_net": float,        # 北向净流入（亿元），正为流入
          "main_force_top20": [...],      # 主力净流入 Top20
          "data_degraded": bool           # True 表示数据获取失败
        }
    """
```

**collect_sentiment.py 集成**：在现有采集完成后追加 `funding.json`，不影响其他数据源采集。

### 5.3 `scripts/decision_logger.py`

**职责**：将本次运行的决策快照写入持久化日志，供 `diagnose.py` 后续回填 outcome。

**调用时机**：`validate_output.py` 校验通过后、`risk_check.py` 之后、PDF 生成之前。

**输入**：`candidates.json`（schema_v1 格式）+ `run_id`。

**输出**：追加写入 `.memory/decision_log.jsonl`（每行一个完整 JSON）。

**日志记录格式**：

```json
{
  "run_id": "20260220-v1.0-143052",
  "as_of_date": "2026-02-20",
  "market_regime": "strong",
  "candidates": [
    {"code": "688272", "name": "联影医疗", "score": 4.2, "action": "buy"}
  ],
  "risk_flags": {"data_degraded": false},
  "outcome": {
    "t1": null,
    "t5": null,
    "written_at": null
  }
}
```

**接口**：
```bash
python3 decision_logger.py \
  --input /tmp/a-share-review/{DATE}/candidates.json \
  --log-file {SKILL_DIR}/.memory/decision_log.jsonl

# 自测
python3 decision_logger.py --test
```

### 5.4 `scripts/diagnose.py`

**职责**：T+1/T+5 运行，回填历史推荐的实际涨跌结果，输出可读性反馈报告。

**触发方式**：手动调用或 cron（收盘后约 16:00），独立于主工作流，不影响日报产出。

**处理逻辑**：

1. 遍历 `decision_log.jsonl`，筛选 `outcome.t1=null` 且 `as_of_date ≤ 今天-1` 的记录
2. 批量调用现有 THS K线 fetcher 获取候选股涨跌幅
3. 获取沪深300当日涨跌幅作为超额收益基准
4. 计算指标：次日胜率、5日胜率、平均超额收益、最差案例
5. 回填 `outcome` 字段（读取全部行 → 修改目标行 → 整体重写）
6. 追加写入 `evolution/feedback.md`

**输出 `feedback.md` 格式**：

```markdown
## 诊断报告 - {起始日期} ~ {结束日期}

### 整体表现
- 统计周期：X 个交易日，共 Y 次推荐
- 次日胜率（action=buy）：Z%（沪深300同期：W%）
- 5日胜率：Z%
- 平均超额收益（T+1）：+X.X%

### 最差案例
| 日期 | 代码 | 名称 | action | 次日涨跌 | 市场当日 |
|...   |      |      |        |          |          |

### 信号质量
- 资金信号有效率：X%（data_degraded=false 的比例）
```

**接口**：
```bash
python3 diagnose.py [--dry-run] [--since 2026-02-01]
```

---

## 六、文件变更清单

### 新增文件

| 文件 | 负责方 |
|------|--------|
| `scripts/validate_output.py` | opencode |
| `schema_v1.json`（参考用） | opencode |
| `scripts/fetchers/funding.py` | opencode |
| `scripts/decision_logger.py` | claude-code |
| `scripts/diagnose.py` | claude-code |
| `tests/test_decision_logger.py` | claude-code |

### 修改文件

| 文件 | 变更内容 | 负责方 |
|------|----------|--------|
| `SKILL.md` | 阶段4新增 JSON block 输出要求；新增阶段4.5校验步骤；阶段1新增 run_id 生成 | opencode |
| `references/commands.md` | 新增 JSON 格式说明 + 校验命令 | opencode |
| `scripts/collect_sentiment.py` | 集成 funding fetcher；生成并传递 run_id | codex |
| `scripts/risk_check.py` | 输出后调用 decision_logger（validate 通过时） | codex |
| `strategy/active.yaml` | 新增 `strategy_version: "v1.0"` 字段 | claude-code |

---

## 七、验收标准

连续 **5 个交易日** 满足以下条件视为可上线：

| 指标 | 门槛 |
|------|------|
| JSON 解析成功率 | 100% |
| 资金因子覆盖率（`data_degraded=false` 比例） | ≥ 95% |
| 每日产出 T+1 可追踪 outcome 占位记录 | 100% |
| 主工作流不因 diagnose/logger 失败而中断 | 100% |

---

## 八、接口约定汇总

### candidates.json 与 report.md 关系

- `candidates.json` 为机器消费的单一真实来源（source of truth）
- `report.md` 末尾 JSON block 与 `candidates.json` 内容完全一致（冗余，方便人工核查）
- `decision_logger.py` 只读 `candidates.json`，不解析 `report.md`

### 模块间数据流

```
run_id（工作流入口生成）
  ↓
collect_sentiment.py + funding_fetcher.py
  ↓
[LLM 分析]
  ↓
candidates.json（schema_v1）← 写入 run_id
  ↓
validate_output.py
  ├─ 失败 → run_failed=true，跳过 decision_logger，继续出报告
  └─ 成功 ↓
         risk_check.py（原有）
           ↓
         decision_logger.py → .memory/decision_log.jsonl
           ↓
         report_to_image.py → PDF → Telegram

（独立进程）
.memory/decision_log.jsonl → diagnose.py → evolution/feedback.md
```
