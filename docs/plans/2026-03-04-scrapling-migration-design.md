# Scrapling 迁移设计

## 目标

用 Scrapling 的 Fetcher（基于 curl_cffi）替换 ashare-data 中所有 urllib 标准库 HTTP 请求，
同时用 Scrapling 的 CSS/XPath 选择器替换 html.parser 手写解析器。

## 核心改动

### 1. 新增 `ashare_data/core/scraper.py` — 统一封装层

封装 Scrapling Fetcher，提供与当前 `http_client.py` 同级别的 API，包括：
- `fetch_page(url) -> Response` — 返回 Scrapling Response（可直接 .css/.xpath）
- `fetch_text(url) -> str` — 兼容旧代码，返回纯文本
- `fetch_json(url) -> dict` — JSON 请求
- `fetch_bytes(url) -> bytes` — 原始字节
- `no_proxy_env()` 上下文管理器保留

关键设计：
- 全局使用 `FetcherSession` 单例复用连接
- 默认 `impersonate='chrome'`，TLS 指纹模拟
- 默认 `stealthy_headers=True`，自动生成真实浏览器 headers
- 内置 retry 机制（curl_cffi 原生支持，IncompleteRead 问题自动消失）

### 2. 各 fetcher 模块改动

| 模块 | HTTP 层 | 解析层 | 改动量 |
|------|---------|--------|--------|
| taoguba.py | urllib → scraper | HTMLParser → css/xpath | 重写 |
| eastmoney_guba.py | urllib → scraper | HTMLParser → css/xpath | 重写 |
| news.py | urllib → scraper | HTMLParser → css | 中等 |
| funding.py | urllib → scraper | 无 HTML 解析 | 小 |
| market_overview.py | urllib → scraper | 无 HTML 解析 | 小 |
| market_sentiment.py | urllib → scraper | 无 HTML 解析 | 小 |
| trade_date.py | urllib → scraper | 无 HTML 解析 | 小 |
| trend_scanner.py | urllib → scraper | 无 HTML 解析 | 小 |
| us_market.py | urllib → scraper | 无 HTML 解析 | 小 |
| broker_account.py | urllib → scraper | 无 HTML 解析 | 小 |

### 3. 项目规范更新

- AGENTS.md: HTML 解析优先使用 Scrapling CSS/XPath 选择器
- pyproject.toml: 新增 `scrapling[fetchers]` 依赖

### 4. http_client.py 处理

保留文件，内部实现切换为 scrapling Fetcher 代理。
所有现有调用方无需改动 import 路径。
