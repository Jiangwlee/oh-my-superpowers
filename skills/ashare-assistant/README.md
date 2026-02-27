# A-Share Assistant

Purpose: A股日常交易工作流 Skill，驱动 LLM 完成复盘、选股、交易计划三阶段分析。
Audience: 使用 Openclaw 平台的交易者，以及维护本 Skill 的开发者。
Input:   `~/.ashare-assistant/data/{DATE}/filtered/` 预处理数据 + `strategy/active.yaml` 策略配置。
Output:  `market_review.md`（复盘）、`analysis/candidates.json`（候选股）、`trading_plan.md`（交易计划）。
Sections: 定位 | 架构 | 目录结构 | 快速上手 | 策略配置 | 数据流 | 部署

---

## 定位

ashare-assistant 是一个 **LLM 工作流 Skill**，负责每日盘后的三段式分析：

| 阶段 | 产出 | 驱动方式 |
|------|------|---------|
| 复盘 | `market_review.md` | LLM 按 `references/market-review.md` 规范生成 |
| 选股 | `analysis/candidates.json` | LLM 按 `references/stock-pick.md` 规范筛选 |
| 交易计划 | `trading_plan.md` | LLM 按 `references/trading-plan.md` 规范制定 |

**核心原则**：LLM 做判断，代码做执行。数据采集、风险校验、决策日志均由确定性脚本完成，LLM 只负责分析推理。

---

## 架构

```
ashare-data 包（数据基础设施）
  └─ ashare-collect / ashare-em-collect / ashare-tgb-collect（CLI）
       └─ ~/.ashare-assistant/data/{DATE}/
            ├── raw/           原始 JSON
            ├── filtered/      过滤后 Markdown（LLM 输入）
            ├── report/        情绪预处理报告
            └── analysis/      LLM 输出产物

ashare-assistant Skill（LLM 工作流）
  ├── SKILL.md                 Skill 入口（Openclaw 读取）
  ├── references/              LLM prompt 规范模板
  ├── strategy/active.yaml     可进化策略配置
  ├── scripts/                 确定性执行脚本
  └── evolution/               策略演进记录
```

---

## 目录结构

```
skills/ashare-assistant/
├── SKILL.md                   Openclaw Skill 定义与执行流程
├── README.md                  本文件
├── DEPLOYMENT.md              部署操作手册
├── requirements.txt           Python 依赖
├── setup.sh                   一键环境初始化
├── references/
│   ├── market-review.md       复盘 prompt 规范
│   ├── stock-pick.md          选股 prompt 规范
│   └── trading-plan.md        交易计划 prompt 规范
├── strategy/
│   ├── active.yaml            当前生效策略（LLM 可迭代修改）
│   └── default.yaml           默认策略备份
├── scripts/
│   ├── trade_review.py        交易复盘（确定性）
│   ├── holding_insight.py     持仓洞察
│   ├── risk_check.py          风险约束校验
│   ├── decision_logger.py     决策日志写入
│   ├── validate_output.py     输出格式校验
│   ├── trade_context.py       交易上下文构建
│   ├── relative_strength.py   相对强度计算
│   ├── opening_context.py     开盘前上下文
│   ├── intraday_summary.py    盘中小结
│   └── send_telegram_file.py  Telegram 推送
└── evolution/
    ├── feedback.md            历史复盘反馈
    ├── known_pitfalls.md      已知问题记录
    └── selection_rules.md     选股规则沉淀
```

---

## 快速上手

### 触发方式

在 Openclaw 对话框输入以下关键词均可触发：

> 复盘 / 选股 / 交易计划 / 明天买什么 / review

### 手动执行（调试）

```bash
cd <skill_install_dir>      # 必须在 Skill 安装目录下运行
DATE=$(date +%Y-%m-%d)
DATA_DIR="$HOME/.ashare-assistant/data/${DATE}"

# 1. 确保数据就绪（cron 已采集则跳过）
ashare-collect --date "${DATE}" --verbose

# 2. 风险检查（在 LLM 生成 candidates.json 后）
python3 -m scripts.risk_check --input "${DATA_DIR}/analysis/candidates.json"

# 3. 决策日志
python3 -m scripts.decision_logger --input "${DATA_DIR}/analysis/candidates.json"
```

> **注意**：scripts 使用相对导入，必须以 `-m scripts.<module>` 方式调用，
> 直接运行 `python3 scripts/foo.py` 会报 `ModuleNotFoundError`。

---

## 策略配置

`strategy/active.yaml` 定义交易策略，LLM 在每次复盘后可根据实际表现迭代调整，
修改时需在 `evolution_log` 中记录变更原因。

| 配置项 | 说明 |
|--------|------|
| `trend_stock` | 趋势股策略（按周/月持股，回调入场）|
| `theme_stock` | 题材股策略（按日持股，不超过 2 周）|
| `market_position` | 大盘强弱对应仓位建议 |
| `account_mode` | 账户健康度模式（growth / normal / defensive / critical）|
| `risk_limits` | 单股/板块/候选数量硬约束 |

账户模式优先级高于大盘仓位建议：回撤超过 30% 时进入 `critical` 模式，强制清仓观望。

---

## 数据流

```
每 30 分钟（cron）
  ashare-collect
    ├── 新闻/资金/行情 → raw/
    ├── 趋势扫描（200 只人气榜）→ ths_report.md
    ├── 个股深研（watchlist + 星级≥4）→ analysis/deep_research/
    └── 情绪预处理（opencode）→ report/news_sentiment.md

盘后（Skill 触发）
  LLM 读取 filtered/ + report/ → 生成三份产出
  scripts 校验 + 日志
```

数据目录默认路径：`~/.ashare-assistant/data/{DATE}/`

---

## 部署

详见 [DEPLOYMENT.md](DEPLOYMENT.md)，关键点：

- 数据采集依赖 `ashare-data` 包（需单独安装）
- VPS 上 `opencode` 需创建软链接至 `/usr/local/bin/`，否则 cron 任务找不到命令
- 新增 CLI entry point 后必须重新部署 `ashare-data` 包并 `pip install -e`
