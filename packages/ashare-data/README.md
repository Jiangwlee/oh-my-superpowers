# ashare-data

A股数据采集与预处理基础设施包。为 `ashare-assistant` skill 提供定时数据采集能力，独立于 LLM 工作流运行。

## 安装

```bash
pip install -e packages/ashare-data
```

安装后注册 CLI 命令 `ashare-collect`。

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
```

## 配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `ASHARE_ASSISTANT_HOME` | 数据根目录 | `~/.ashare-assistant` |

数据目录结构：

```
$ASHARE_ASSISTANT_HOME/
├── data/
│   └── {DATE}/
│       ├── raw/        # 原始 JSON（ashare-collect 输出）
│       └── filtered/   # Markdown 格式（ashare-assistant 读取）
├── cache/              # HTTP 响应缓存
├── broker_data/        # 券商持仓历史
│   ├── positions/
│   └── orders/
└── memory/
    └── decision_log.jsonl
```

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
| `fetchers/broker_account.py` | JVQuant | 账户持仓、委托记录 |
| `fetchers/trade_date.py` | 内置日历 | 交易日判断 |

## 包结构

```
ashare_data/
├── core/
│   ├── config.py          # 路径配置（读 ASHARE_ASSISTANT_HOME）
│   ├── http_client.py     # HTTP 工具（重试、超时）
│   └── cache.py           # 磁盘缓存
├── fetchers/              # 各数据源采集模块
├── collect.py             # 统一采集入口（ashare-collect CLI）
└── filter_to_markdown.py  # JSON → Markdown 格式转换
```

## 开发

```bash
# 运行测试
python -m unittest discover -s skills/ashare-assistant/tests -p "test_*.py"

# 测试指定模块
python -m unittest skills.ashare-assistant.tests.test_broker_account
```

## 部署（定时任务）

```cron
# 每个交易日 15:30 采集
30 15 * * 1-5 ASHARE_ASSISTANT_HOME=/data/ashare ashare-collect --date $(date +\%Y-\%m-\%d)
```
