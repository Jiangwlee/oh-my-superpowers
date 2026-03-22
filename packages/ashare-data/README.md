# ashare-data

A股数据采集与预处理基础设施包。为 `ashare-assistant` skill 提供定时数据采集能力，独立于 LLM 工作流运行。

当前重构方向下，`ashare-data` 的长期定位是 **可复用基础库**：

- 保留 source fetchers、共享 HTTP/缓存/解析工具、趋势评分等通用能力
- 逐步减少平台级业务逻辑、数据库落库、HTTP API、工作台职责
- 新的数据平台后端位于 `apps/ashare-platform/backend`

## 安装

```bash
pip install -e packages/ashare-data
```

安装后注册以下 CLI 命令：

| 命令 | 说明 |
|------|------|
| `ashare-collect` | 每日收盘后数据采集（新闻/资金/板块/论坛） |
| `ashare-cdp-debug` | Chrome CDP 调试入口（用于受保护接口排障） |
| `ashare-diagnose` | 数据质量诊断 |
| `ashare-em-collect` | 东方财富股吧热帖采集 |
| `ashare-tgb-collect` | 淘股吧热帖采集 |
| `ashare-wl-monitor` | Watchlist 盘中信号扫描（默认循环模式） |
| `ashare-postclose-decide` | 盘后决策流水线（生成次日交易建议） |

## 快速使用

```bash
# 采集今日数据（raw/ → filtered/）
ashare-collect --verbose

# 指定日期
ashare-collect --date 2026-02-26

# 仅采集，跳过格式转换
ashare-collect --skip-filter

# 仅格式转换（原始数据已存在）
ashare-collect --skip-collect

# 盘中 watchlist 扫描（自动判断交易时间与节假日）
ashare-wl-monitor --verbose

# 强制运行（跳过时间和节假日检查，用于调试）
ashare-wl-monitor --force

# 仅执行一次扫描（适合 cron）
ashare-wl-monitor --once

# 连续扫描（默认每 20 秒，可自定义间隔）
ashare-wl-monitor --interval 60

# 盘后决策流水线
ashare-postclose-decide --verbose

# 用真实浏览器上下文抓同花顺 indexflash
ashare-cdp-debug ths-indexflash

# 通用页内 fetch 调试
ashare-cdp-debug fetch-json --page-url https://q.10jqka.com.cn/ --url '/api.php?t=indexflash'
```

### `ashare-collect` 参数（当前实现）

```bash
ashare-collect [--date YYYY-MM-DD] [--skip-collect] [--skip-filter] \
  [--news-count N] [--taoguba-count N] [--no-scan-trends] \
  [--popularity-max N] [--verbose]
```

- `--date`：指定采集日期（默认今日）
- `--skip-collect`：跳过采集阶段，仅执行过滤转换
- `--skip-filter`：跳过过滤转换，仅执行采集阶段
- `--news-count`：每类新闻采集条数
- `--taoguba-count`：淘股吧采集条数
- `--no-scan-trends`：关闭趋势扫描
- `--popularity-max`：人气榜扫描上限
- `--verbose`：输出详细日志

## 配置

数据根目录固定为 `~/.ashare-assistant`（不使用环境变量覆盖）。

数据目录结构：

```
~/.ashare-assistant/
├── data/
│   └── {DATE}/
│       ├── manifest.json # 批次清单（文件哈希/大小/记录数）
│       ├── raw/        # 原始 JSON（ashare-collect 输出）
│       ├── filtered/   # Markdown 格式（ashare-assistant 读取）
│       ├── analysis/   # ashare-assistant 生成的结构化 JSON 产物
│       └── report/     # ashare-assistant 子代理中间报告
├── signals/
│   └── watchlist_signals.json  # ashare-wl-monitor 盘中扫描结果（每次覆盖写）
├── cache/              # HTTP 响应缓存
├── broker_data/        # 券商持仓历史
│   ├── positions/
│   └── orders/
└── memory/
    └── decision_log.jsonl
```

治理说明（当前实现）：
- 核心输出均带 `schema_version` 字段（如 `collection_summary.json`、`run_id.json`、`post_close_decisions.json`、`watchlist_signals.json`、`outcome`）
- 每日批次会生成 `manifest.json`，记录 `raw/` 与 `filtered/` 文件的 `sha256`、大小和记录数
- `collection_summary.json` 的每个 `source` 包含最小 DQ 指标：`record_count` / `is_empty` / `freshness_sec` / `missing_key_rate`
- `ashare-collect` 会执行 retention 策略：按保留期清理历史 `data/`、过期信号文件和过旧 `decision_log.jsonl` 记录
- `ashare-collect` 返回 `degraded/degraded_reasons`，用于标记“可用但质量降级”的批次
- 关键决策产物包含血缘字段：`source_run_id` / `source_files`

## 数据源

| 模块 | 数据源 | 说明 |
|------|--------|------|
| `fetchers/news.py` | 金融界 | 头条/每日/机会/实时/快讯 |
| `fetchers/funding.py` | 金融界 | 北向资金、主力净流入 TOP |
| `fetchers/market_overview.py` | 金融界 | 板块涨跌、同花顺报告 |
| `fetchers/us_market.py` | 金融界 | 美股三大指数 |
| `fetchers/taoguba.py` | 淘股吧 | 热帖、推荐、热议 |
| `fetchers/eastmoney_guba.py` | 东方财富 | 股吧热帖 |
| `fetchers/trend_scanner.py` | JRJ/THS | 趋势评分、K线数据 |
| `fetchers/market_sentiment.py` | 同花顺 | 涨跌停计数、封板率、晋级统计、市场危险等级、是否开盘 |
| `fetchers/market_breadth.py` | 搜狐/同花顺 | 历史涨跌平家数，最新快照支持 THS CDP fallback |
| `fetchers/market_turnover.py` | 同花顺 | 市场总成交额（日级） |
| `fetchers/sohu_zdt.py` | 搜狐 | 历史涨停/跌停/涨跌平/成交额 HTML 表 |
| `fetchers/sse_stock_data.py` | 上交所 | 日概览、统计数据、活跃股榜 |
| `fetchers/ths_cdp.py` | 同花顺 | 受浏览器上下文保护接口的 CDP 采集适配层 |
| `fetchers/broker_account.py` | JVQuant | 账户持仓、委托记录 |
| `fetchers/trade_date.py` | 金融界 JRJ 接口 | 最近交易日获取（`tradedate`） |

## 包结构

```
ashare_data/
├── core/
│   ├── config.py          # 路径配置（固定 ~/.ashare-assistant）
│   ├── http_client.py     # HTTP 工具（重试、超时、无代理）
│   ├── watchlist.py       # Watchlist 读写
│   └── cache.py           # 磁盘缓存
├── fetchers/
│   ├── market_sentiment.py  # 同花顺涨跌停池 → MarketSentiment
│   ├── market_breadth.py    # 历史/最新涨跌平家数
│   ├── market_turnover.py   # 市场成交额
│   ├── sohu_zdt.py          # 搜狐历史涨跌分布表
│   ├── sse_stock_data.py    # 上交所公共统计接口
│   ├── ths_cdp.py           # 同花顺 CDP 适配层
│   ├── trend_scanner.py     # 趋势评分、历史 K 线
│   └── ...                  # 其他数据源
├── cdp/
│   ├── client.py            # Chrome DevTools Protocol 客户端
│   ├── session.py           # 页面会话与页内 fetch/eval
│   └── errors.py            # CDP 相关异常
├── collect.py               # 统一采集入口（ashare-collect CLI）
├── cdp_debug.py             # CDP 调试入口（ashare-cdp-debug）
├── watchlist_monitor.py     # Watchlist 盘中信号扫描（ashare-wl-monitor CLI）
└── filter_to_markdown.py    # JSON → Markdown 格式转换
```

说明：

- 上述结构反映的是当前状态，不是最终目标边界
- 平台级 task / pipeline / retained fact / API 将逐步迁往
  `apps/ashare-platform/backend`
- `ashare-data` 将收敛为“拿数据、洗数据、算分”的基础能力层

## 与 ashare-platform 的边界

当前职责边界：

- `ashare-data` 负责抓取、解析、清洗、评分、CDP 访问适配
- `ashare-platform` 负责 retained DB、日级 pipeline、HTTP API、容器内调度

典型链路：

- `market_sentiment.py` / `market_breadth.py` / `market_turnover.py`
  提供市场情绪原始能力
- `apps/ashare-platform/backend/app/pipelines/build_emotion_facts.py`
  将这些原始能力汇总为 retained `market_emotion_daily`

## Chrome CDP

`ashare-data` 现在内置通用 CDP 客户端，用于处理必须依赖真实浏览器上下文的数据源。

典型场景：

- 同花顺 `indexflash` 普通 HTTP 访问会遇到 `403`
- 在真实 Chrome 会话中可正常返回
- `market_breadth.py` 会在直接 HTTP 失败时切到 `ths_cdp.py`

调试命令：

```bash
ashare-cdp-debug ths-indexflash
ashare-cdp-debug fetch-json --page-url https://q.10jqka.com.cn/ --url '/api.php?t=indexflash'
```

默认依赖本机 Chrome DevTools endpoint：

```bash
http://127.0.0.1:9222
```

## 开发

```bash
# 运行测试
python -m unittest discover -s tests -p "test_*.py"

# 测试指定模块
python -m unittest tests.test_broker_account
```

## 部署（定时任务）

`ashare-data` 自身仍可独立以 cron 方式运行，但日级 retained facts、HTTP API 和容器内定时任务现在由 `apps/ashare-platform/backend` 承担。

```cron
# 每个工作日 15:30 采集收盘数据
30 15 * * 1-5 ashare-collect --date $(date +\%Y-\%m-\%d)

# 每个工作日盘中（9-15 点）每 10 分钟扫描 watchlist（单次模式）
# 脚本自动判断交易时段（9:30-15:00）和节假日（THS trade_status）
*/10 9-15 * * 1-5 ashare-wl-monitor --once
```

## 实操顺序建议

建议按交易时段执行，避免数据缺口：

1. 盘后先运行 `ashare-postclose-decide`，生成次日候选（输出 `post_close_decisions.json`）
2. 盘中运行 `ashare-wl-monitor --once`（或循环模式），基于盘后候选 + 实时行情生成盘中信号
3. 每日收盘后运行 `ashare-collect`，做全量数据采集与 Markdown 过滤
4. 个股深研按需运行 `ashare-em-collect` / `ashare-tgb-collect`（单股扩展数据，不是日常必跑）
5. 周期性运行 `ashare-diagnose`，回填 `decision_log.jsonl` 的 T+1/T+5 并输出反馈摘要

说明：
- `ashare-wl-monitor` 依赖 `ashare-postclose-decide` 产出的 `~/.ashare-assistant/signals/post_close_decisions.json`
- 其他 CLI 彼此无强依赖，可按场景独立运行

### `ashare-wl-monitor` 工作原理

1. **时间门控**：北京时间 9:30–15:00 外自动跳过
2. **节假日检测**：调用同花顺接口，若 `trade_status` 不属于交易中状态（如 `trading`/`morning_trade`/`afternoon_trade`）则跳过（避免节假日基于昨日收盘价产生虚假信号）
3. **市场危险等级**：跌停 ≥ 80 时写空信号文件并退出；30–79 标记 `yellow`，仓位目标采用更保守参数
4. **个股判定**：基于 `SETUP/ENTRY/HOLD` 状态机，结合周/日均线、回撤区间（PB）和量能触发信号
5. **输出**：覆盖写 `~/.ashare-assistant/signals/watchlist_signals.json`

信号文件格式：

```json
{
  "scanned_at": "2026-02-27 13:45:00",
  "market": {"limit_up": 75, "limit_down": 3, "danger_level": "green"},
  "market_sectors": {},
  "monitored": {"buy_targets": 12, "universe": 12},
  "holdings_source_date": "",
  "holdings_live": [],
  "signals": [
    {"code": "002378", "name": "章源钨业", "state": "SETUP",
     "reason": "回撤进入观察区，等待突破PB_HIGH确认",
     "price": 8.45, "change": -2.3, "ma5w": 8.52, "ma20w": 8.10,
     "ma20d": 8.31, "vr20d": 0.74, "dev20w": 0.0421, "dev5w": -0.0087,
     "pb_start_date": "2026-02-27", "pb_high": 8.61, "pb_low": 8.33,
     "entry_price": 0.0, "stop_price": 0.0, "position_target": 0.25,
     "action_next_day": "observe_setup", "score": 70}
  ],
  "exits": [],
  "pullback_state_count": 3
}
```
