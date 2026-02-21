# 美股行情集成 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 a-share-review-planner 中集成美股主要指数和核心科技股行情，输出独立的"美股影响评估"章节，为 A 股选股和仓位决策提供新维度。

**Architecture:** 新增 `us_market.py` fetcher 使用 yfinance 抓取美股数据，输出 `us_market.json`；在 `collect_sentiment.py` 中作为并发任务之一执行；在 `analysis-framework.md` 第一步之前插入第0步分析模板，`stage2-read.md` 新增读取项。

**Tech Stack:** Python 3.10+, yfinance（新增第三方依赖）, 标准库

---

## Task 1: 新增 yfinance 依赖

**Files:**
- Modify: `skills/a-share-review-planner/requirements.txt`
- Modify: `skills/a-share-review-planner/setup.sh`

**Step 1: 更新 requirements.txt**

将 `skills/a-share-review-planner/requirements.txt` 的第一行注释从"零第三方包"改为说明新增了 yfinance，并在文件末尾加入：

```
# 第三方包（minimal）
yfinance>=0.2.50
```

完整替换后的文件：

```
# a-share-review-planner Python 依赖
#
# 第三方包：yfinance（美股行情采集）
# 安装：pip install yfinance
#
# 运行时要求：
#   Python  >= 3.10   （使用 str | None 联合类型语法）
#   Node.js >= 22.0   （screenshot.js 需要内置 WebSocket + fetch）
#   Chrome / Chromium （PDF 及 PNG 生成）
#
# 可选工具：
#   pandoc            （Markdown→HTML 精确渲染，缺失时自动降级）
#
# 支持平台（setup.sh 自动识别）：
#   macOS
#   Ubuntu / Debian          — apt-get
#   RHEL / CentOS / Rocky
#     / AlmaLinux / Fedora   — dnf / yum（自动启用 EPEL）
#
# 完整安装步骤见 setup.sh

yfinance>=0.2.50
```

**Step 2: 更新 setup.sh — 在各平台末尾添加 pip install**

在 setup.sh 中定位到 `# ── 共用：创建目录 + 验证安装 ──` 注释之前（第 171 行之前），在 `if [ "$DISTRO" = "unknown" ]` 块的下方，添加一个共用的 pip install 步骤：

在第 169 行（`fi` 的下方，`# ── 共用：创建目录`上方）插入：

```bash
# ── 共用：安装 Python 第三方包 ────────────────────────────────────────────────
echo "安装 Python 依赖（yfinance）..."
python3 -m pip install --quiet yfinance 2>/dev/null || \
    pip3 install --quiet yfinance 2>/dev/null || \
    echo "  ⚠️  yfinance 安装失败，美股行情采集将被跳过"

```

**Step 3: 验证 yfinance 可用**

```bash
pip install yfinance
python3 -c "import yfinance; print('yfinance', yfinance.__version__)"
```

期望输出：`yfinance 0.2.x`

**Step 4: Commit**

```bash
git add skills/a-share-review-planner/requirements.txt skills/a-share-review-planner/setup.sh
git commit -m "feat(a-share-review-planner): add yfinance dependency for US market data"
```

---

## Task 2: 实现 us_market.py fetcher（TDD）

**Files:**
- Create: `skills/a-share-review-planner/tests/test_us_market.py`
- Create: `skills/a-share-review-planner/scripts/fetchers/us_market.py`

**Step 1: 写失败测试**

创建 `skills/a-share-review-planner/tests/test_us_market.py`：

```python
"""美股行情抓取模块单元测试。"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── sys.path 设置，使包导入生效 ──
_SKILL_ROOT = Path(__file__).parent.parent
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))


class UsMarketFetcherTest(unittest.TestCase):
    """测试 fetch_us_market() 的输出结构和降级行为。"""

    def _make_mock_ticker(self, prev_close: float, current_price: float) -> MagicMock:
        """构造一个模拟的 yfinance Ticker 对象。"""
        ticker = MagicMock()
        ticker.fast_info = MagicMock()
        ticker.fast_info.previous_close = prev_close
        ticker.fast_info.last_price = current_price
        ticker.fast_info.market_state = "CLOSED"
        return ticker

    @patch("scripts.fetchers.us_market.yf")
    def test_output_schema(self, mock_yf):
        """输出 JSON 必须包含 fetched_at / market_status / indices / tech_stocks。"""
        from scripts.fetchers.us_market import fetch_us_market

        mock_yf.Ticker.side_effect = lambda sym: self._make_mock_ticker(100.0, 102.0)

        result = fetch_us_market()

        self.assertIn("fetched_at", result)
        self.assertIn("market_status", result)
        self.assertIn("indices", result)
        self.assertIn("tech_stocks", result)

    @patch("scripts.fetchers.us_market.yf")
    def test_indices_content(self, mock_yf):
        """indices 必须包含纳斯达克、道琼斯、标普500、VIX，且有 change_pct。"""
        from scripts.fetchers.us_market import fetch_us_market

        mock_yf.Ticker.side_effect = lambda sym: self._make_mock_ticker(100.0, 103.0)

        result = fetch_us_market()
        tickers = {item["ticker"] for item in result["indices"]}
        self.assertIn("^IXIC", tickers)
        self.assertIn("^DJI", tickers)
        self.assertIn("^GSPC", tickers)
        self.assertIn("^VIX", tickers)

        for item in result["indices"]:
            self.assertIn("change_pct", item)
            self.assertIn("name_cn", item)

    @patch("scripts.fetchers.us_market.yf")
    def test_tech_stocks_content(self, mock_yf):
        """tech_stocks 必须包含 NVDA/AAPL/TSLA/MSFT/GOOG/META，且有 a_share_sectors。"""
        from scripts.fetchers.us_market import fetch_us_market

        mock_yf.Ticker.side_effect = lambda sym: self._make_mock_ticker(200.0, 196.0)

        result = fetch_us_market()
        tickers = {item["ticker"] for item in result["tech_stocks"]}
        for sym in ("NVDA", "AAPL", "TSLA", "MSFT", "GOOG", "META"):
            self.assertIn(sym, tickers)

        for item in result["tech_stocks"]:
            self.assertIsInstance(item["a_share_sectors"], list)
            self.assertGreater(len(item["a_share_sectors"]), 0)

    @patch("scripts.fetchers.us_market.yf")
    def test_change_pct_calculation(self, mock_yf):
        """涨跌幅计算：(current - prev) / prev * 100，保留2位小数。"""
        from scripts.fetchers.us_market import fetch_us_market

        mock_yf.Ticker.side_effect = lambda sym: self._make_mock_ticker(100.0, 102.0)

        result = fetch_us_market()
        # 所有标的都用 100->102，change_pct 应为 2.0
        for item in result["indices"] + result["tech_stocks"]:
            self.assertAlmostEqual(item["change_pct"], 2.0, places=1)

    @patch("scripts.fetchers.us_market.yf")
    def test_graceful_degradation_on_error(self, mock_yf):
        """单个 ticker 抓取失败时，不影响其他标的，change_pct 设为 None。"""
        from scripts.fetchers.us_market import fetch_us_market

        def side_effect(sym):
            if sym == "NVDA":
                raise RuntimeError("network error")
            return self._make_mock_ticker(100.0, 101.0)

        mock_yf.Ticker.side_effect = side_effect

        result = fetch_us_market()
        nvda_items = [i for i in result["tech_stocks"] if i["ticker"] == "NVDA"]
        self.assertEqual(len(nvda_items), 1)
        self.assertIsNone(nvda_items[0]["change_pct"])

        # 其他标的正常
        other = [i for i in result["tech_stocks"] if i["ticker"] != "NVDA"]
        for item in other:
            self.assertIsNotNone(item["change_pct"])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: 运行测试，确认失败**

```bash
cd /Users/mindora/Workspace/projects/OpenclawSkills
python -m unittest skills/a-share-review-planner/tests/test_us_market.py -v
```

期望输出：`ImportError` 或 `ModuleNotFoundError`（us_market 模块不存在）

**Step 3: 实现 us_market.py**

创建 `skills/a-share-review-planner/scripts/fetchers/us_market.py`：

```python
"""美股主要指数与核心科技股行情抓取模块。

使用 yfinance 获取收盘价和涨跌幅，并附带硬编码的 A 股关联板块映射。
若 yfinance 未安装，函数返回空结构并记录警告，不抛出异常。
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── 尝试导入 yfinance ────────────────────────────────────────────────────────

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    yf = None  # type: ignore[assignment]
    _YF_AVAILABLE = False
    logger.warning("yfinance 未安装，美股行情采集将被跳过。安装：pip install yfinance")


# ── 硬编码配置 ────────────────────────────────────────────────────────────────

_INDICES = [
    {"ticker": "^IXIC", "name_cn": "纳斯达克"},
    {"ticker": "^DJI",  "name_cn": "道琼斯"},
    {"ticker": "^GSPC", "name_cn": "标普500"},
    {"ticker": "^VIX",  "name_cn": "VIX恐慌指数"},
]

_TECH_STOCKS = [
    {"ticker": "NVDA", "name_cn": "英伟达"},
    {"ticker": "AAPL", "name_cn": "苹果"},
    {"ticker": "TSLA", "name_cn": "特斯拉"},
    {"ticker": "MSFT", "name_cn": "微软"},
    {"ticker": "GOOG", "name_cn": "谷歌"},
    {"ticker": "META", "name_cn": "Meta"},
]

# 美股个股 → A 股关联概念板块映射
_SECTOR_MAP: dict[str, list[str]] = {
    "NVDA": ["半导体/芯片", "AI算力", "光模块", "液冷散热"],
    "AAPL": ["消费电子", "果链（立讯精密/歌尔股份）", "AI手机"],
    "TSLA": ["新能源汽车", "锂电池", "充电桩", "汽车智能化"],
    "MSFT": ["云计算", "AI应用软件", "企业SaaS"],
    "GOOG": ["AI应用", "算力产业链", "光模块/液冷"],
    "META": ["VR/AR/元宇宙", "AI应用", "液冷散热"],
}


# ── 内部工具函数 ──────────────────────────────────────────────────────────────


def _get_quote(ticker_sym: str) -> dict:
    """获取单个标的的行情数据。

    Args:
        ticker_sym: Yahoo Finance Ticker 符号，如 "^IXIC" 或 "NVDA"。

    Returns:
        包含 prev_close / close / change_pct / market_status 的 dict。
        任何字段获取失败时对应值为 None。
    """
    try:
        t = yf.Ticker(ticker_sym)
        fi = t.fast_info
        prev_close: float | None = fi.previous_close
        close: float | None = fi.last_price
        market_status: str | None = getattr(fi, "market_state", None)

        if prev_close and close and prev_close != 0:
            change_pct = round((close - prev_close) / prev_close * 100, 2)
        else:
            change_pct = None

        return {
            "prev_close": round(prev_close, 2) if prev_close else None,
            "close": round(close, 2) if close else None,
            "change_pct": change_pct,
            "market_status": market_status,
        }
    except Exception as exc:
        logger.warning("获取 %s 行情失败: %s", ticker_sym, exc)
        return {"prev_close": None, "close": None, "change_pct": None, "market_status": None}


# ── 公开接口 ──────────────────────────────────────────────────────────────────


def fetch_us_market() -> dict:
    """获取美股主要指数和核心科技股行情。

    Returns:
        {
            "fetched_at": "2026-02-21 21:30:00",
            "market_status": "closed|open|pre-market|after-hours",
            "indices": [...],
            "tech_stocks": [...],
        }
        若 yfinance 未安装，返回带 "error" 字段的空结构。
    """
    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not _YF_AVAILABLE:
        return {
            "fetched_at": fetched_at,
            "market_status": "unavailable",
            "error": "yfinance not installed",
            "indices": [],
            "tech_stocks": [],
        }

    indices: list[dict] = []
    market_status = "unknown"

    for cfg in _INDICES:
        quote = _get_quote(cfg["ticker"])
        if market_status == "unknown" and quote.get("market_status"):
            market_status = quote["market_status"].lower()
        indices.append({
            "ticker": cfg["ticker"],
            "name_cn": cfg["name_cn"],
            "change_pct": quote["change_pct"],
            "close": quote["close"],
            "prev_close": quote["prev_close"],
        })

    tech_stocks: list[dict] = []
    for cfg in _TECH_STOCKS:
        quote = _get_quote(cfg["ticker"])
        tech_stocks.append({
            "ticker": cfg["ticker"],
            "name_cn": cfg["name_cn"],
            "change_pct": quote["change_pct"],
            "close": quote["close"],
            "prev_close": quote["prev_close"],
            "a_share_sectors": _SECTOR_MAP.get(cfg["ticker"], []),
        })

    return {
        "fetched_at": fetched_at,
        "market_status": market_status,
        "indices": indices,
        "tech_stocks": tech_stocks,
    }
```

**Step 4: 运行测试，确认通过**

```bash
python -m unittest skills/a-share-review-planner/tests/test_us_market.py -v
```

期望输出：5 个测试全部 `ok`

**Step 5: 语法检查**

```bash
python -m py_compile skills/a-share-review-planner/scripts/fetchers/us_market.py
python -m py_compile skills/a-share-review-planner/tests/test_us_market.py
```

期望：无输出（无语法错误）

**Step 6: Commit**

```bash
git add skills/a-share-review-planner/scripts/fetchers/us_market.py \
        skills/a-share-review-planner/tests/test_us_market.py
git commit -m "feat(a-share-review-planner): add us_market fetcher with A-share sector mapping"
```

---

## Task 3: 集成到 collect_sentiment.py

**Files:**
- Modify: `skills/a-share-review-planner/scripts/collect_sentiment.py`

**Step 1: 在 import 区域末尾（第 45 行之后）新增导入**

在 `from scripts.fetchers.broker_account import fetch_broker_account` 之后追加：

```python
from scripts.fetchers.us_market import fetch_us_market            # noqa: E402
```

**Step 2: 在 `_make_tasks()` 函数的 return 列表中追加 us_market 任务**

在 `_make_tasks()` 函数（第 131-145 行）的 return 列表末尾，`taoguba_recommend` 任务之后，追加：

```python
        {"name": "us_market", "filename": "us_market.json", "fn": fetch_us_market},
```

**Step 3: 在 `name_to_file` 字典（第 315-320 行）追加 us_market 映射**

在 `name_to_file["broker_account"] = "broker_account.json"` 之后追加：

```python
    name_to_file["us_market"] = "us_market.json"
```

注意：这一行实际上不需要，因为 us_market 已经在 `_make_tasks()` 中定义了 filename，`name_to_file` 字典是通过 `{t["name"]: t["filename"] for t in tasks}` 从 tasks 列表自动构建的（第 315 行）。**不需要手动追加**。

**Step 4: 验证采集脚本可正常导入（不需要实际运行网络采集）**

```bash
python -m py_compile skills/a-share-review-planner/scripts/collect_sentiment.py
python3 -c "
import sys; sys.path.insert(0, 'skills/a-share-review-planner')
from scripts.collect_sentiment import _make_tasks
tasks = _make_tasks(5, 5)
names = [t['name'] for t in tasks]
assert 'us_market' in names, f'us_market not in tasks: {names}'
print('✓ us_market task registered:', [t for t in tasks if t['name'] == 'us_market'])
"
```

期望输出：`✓ us_market task registered: [{'name': 'us_market', 'filename': 'us_market.json', ...}]`

**Step 5: Commit**

```bash
git add skills/a-share-review-planner/scripts/collect_sentiment.py
git commit -m "feat(a-share-review-planner): register us_market as collection task in collect_sentiment"
```

---

## Task 4: 更新 stage2-read.md

**Files:**
- Modify: `skills/a-share-review-planner/references/stage2-read.md`

**Step 1: 在文件第19行之后，`broker_account.json` 行之前，插入 us_market.json 条目**

在表格中 `| 11 |` 行之前插入：

```
| 10.5 | `/tmp/a-share-review/{DATE}/us_market.json` | 美股行情（若文件不存在则跳过，不影响分析流程） |
```

修改后的表格应为：

```markdown
| # | 文件 | 用途 |
|---|------|------|
| 0 | `/tmp/a-share-review/{DATE}/run_id.json` | **本次运行标识** |
| 1 | `/tmp/a-share-review/{DATE}/news_headline.json` | A股头条（指数、成交额） |
...（中间行不变）...
| 10 | `/tmp/a-share-review/{DATE}/trend_report.md` | 趋势股报告（人类可读） |
| 10.5 | `/tmp/a-share-review/{DATE}/us_market.json` | 美股行情（若文件不存在则跳过，不影响分析流程） |
| 11 | `/tmp/a-share-review/{DATE}/broker_account.json` | 账户资金+持仓（如存在） |
...（后续行不变）...
```

**Step 2: Commit**

```bash
git add skills/a-share-review-planner/references/stage2-read.md
git commit -m "docs(a-share-review-planner): add us_market.json to stage2 read list"
```

---

## Task 5: 更新 analysis-framework.md — 新增第0步

**Files:**
- Modify: `skills/a-share-review-planner/references/analysis-framework.md`

**Step 1: 在文件目录部分（第9-18行）最前面插入第0步条目**

在目录 `- [第一步：市场环境判断]` 之前插入：

```markdown
- [第0步：美股前夜扫描](#第0步美股前夜扫描) — 指数涨跌、核心科技股、A股板块联动预判
```

**Step 2: 在 `## 第一步：市场环境判断` 之前插入完整的第0步章节**

插入位置：第22行（`## 第一步：市场环境判断` 标题之前），插入以下完整内容：

````markdown
## 第0步：美股前夜扫描

> **触发条件**：`us_market.json` 存在时执行。若文件不存在（yfinance 失败），跳过本步骤，在报告中注明"美股数据不可用"。

### 必须读取的数据

1. `us_market.json` — 美股指数与科技股行情

### 必须回答的问题

1. **美股三大指数整体表现如何？**
   - 纳斯达克、道琼斯、标普500 各自涨跌幅
   - VIX 恐慌指数水平（< 20 正常 / 20–30 警戒 / > 30 恐慌）
   - 整体基调：正面 / 中性 / 负面

2. **核心科技股如何表现？**
   - 英伟达、苹果、特斯拉、微软、谷歌、Meta 各自涨跌幅
   - 是否有个股异常波动（≥ ±3%）

3. **对 A 股主要板块的预期影响是什么？**
   - 基于 `a_share_sectors` 映射，逐一说明各科技股对 A 股相关板块的预期影响
   - 影响判断阈值：≥+2% 强利好 / +0.5%~+2% 弱利好 / -0.5%~+0.5% 中性 / -2%~-0.5% 弱利空（承压）/ ≤-2% 强利空（重挫）

### 输出格式

```
美股影响评估：
- 指数基调：纳斯达克 X% / 道琼斯 X% / 标普500 X% → 整体：正面/中性/负面
- VIX恐慌指数：XX（<20正常 / 20-30警戒 / >30恐慌）
- 核心科技股联动：
  - 英伟达 X% → A股影响：半导体/AI算力板块 [利好/中性/承压]
  - 特斯拉 X% → A股影响：新能源汽车/锂电池板块 [利好/中性/承压]
  - 苹果 X% → A股影响：消费电子/果链板块 [利好/中性/承压]
  - 微软 X% → A股影响：云计算/AI应用板块 [利好/中性/承压]
  - 谷歌 X% → A股影响：AI应用/算力产业链板块 [利好/中性/承压]
  - Meta X% → A股影响：VR/AR/元宇宙板块 [利好/中性/承压]
- 综合预判：（1-2句，说明美股对A股今日开盘的整体拖累或提振预期，及最值得关注的板块）
```

---

````

**Step 3: 更新第一步"必须回答的问题"第1条**

在第一步中找到如下原文：

```
   - 美股（道琼斯/纳斯达克）前一日表现
   - 来源：从新闻和舆情中提取
```

替换为：

```
   - 美股前夜整体表现（直接引用第0步"美股影响评估"中的指数基调结论，无需重复提取）
```

**Step 4: Commit**

```bash
git add skills/a-share-review-planner/references/analysis-framework.md
git commit -m "feat(a-share-review-planner): add step-0 US market pre-scan to analysis framework"
```

---

## Task 6: 全量测试验证

**Step 1: 运行所有测试**

```bash
python -m unittest discover -s skills -p "test_*.py" -v
```

期望：所有测试通过，无 ERROR / FAIL

**Step 2: 运行语法检查**

```bash
python -m py_compile skills/a-share-review-planner/scripts/fetchers/us_market.py
python -m py_compile skills/a-share-review-planner/scripts/collect_sentiment.py
```

期望：无输出

**Step 3: 冒烟测试（可选，需网络）**

```bash
python3 -c "
import sys; sys.path.insert(0, 'skills/a-share-review-planner')
from scripts.fetchers.us_market import fetch_us_market
import json
result = fetch_us_market()
print(json.dumps(result, ensure_ascii=False, indent=2)[:500])
"
```

期望：输出包含 indices 和 tech_stocks 的 JSON 片段

**Step 4: Final commit（如有残留修改）**

```bash
git add -u
git commit -m "test(a-share-review-planner): verify US market integration, all tests passing"
```
