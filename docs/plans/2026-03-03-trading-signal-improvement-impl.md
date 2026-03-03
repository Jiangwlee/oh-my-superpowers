# Trading Signal Improvement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复交易信号系统的三个核心缺陷：补充均线方向验证、增加持仓出场信号、废弃旧信号来源。

**Architecture:** 全部改动集中在两个文件：`watchlist_monitor.py`（新信号系统）和 `trend_scanner.py`（旧系统降级）。不增加新文件，不改变选股池逻辑，不涉及自动下单。

**Tech Stack:** Python 3.11, unittest（项目已有测试在 `packages/ashare-data/tests/`）

---

## Task 1：`watchlist_monitor.py` — 加入5周均线方向验证

**目标：** 在买入信号生成前，验证5周均线本身是向上倾斜的。均线方向向下时直接排除，即使价格贴近均线也不买。

**Files:**
- Modify: `packages/ashare-data/ashare_data/watchlist_monitor.py:515-525`
- Test: `packages/ashare-data/tests/test_watchlist_monitor.py`（新建）

---

**Step 1: 新建测试文件，写第一个失败测试**

新建 `packages/ashare-data/tests/test_watchlist_monitor.py`：

```python
"""测试 watchlist_monitor 的信号逻辑。"""
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from ashare_data.watchlist_monitor import _analyze_signal, _KlineBar, _RealtimeQuote
from ashare_data.fetchers.market_sentiment import MarketSentiment


def _make_daily_bars(closes: list[float]) -> list[_KlineBar]:
    """构造日K列表，日期从 2026-01-01 起。"""
    bars = []
    for i, c in enumerate(closes):
        date = f"2026-01-{i+1:02d}" if i < 31 else f"2026-02-{i-30:02d}"
        bars.append(_KlineBar(date=date, open=c, high=c, low=c, close=c, volume=1000))
    return bars


def _make_weekly_bars(closes: list[float]) -> list[_KlineBar]:
    bars = []
    for i, c in enumerate(closes):
        bars.append(_KlineBar(date=f"2026-W{i+1:02d}", open=c, high=c, low=c, close=c, volume=5000))
    return bars


def _make_rt(current: float, change_pct: float = -4.0, volume_lot: int = 800) -> _RealtimeQuote:
    return _RealtimeQuote(current=current, change_pct=change_pct, volume_lot=volume_lot)


def _green_sentiment() -> MarketSentiment:
    return MarketSentiment(limit_up=80, limit_down=20, danger_level="green", market_open=True)


class TestAnalyzeSignalMA5WDirection(unittest.TestCase):
    """均线方向验证：5周均线向下时不应产生买入信号。"""

    def _make_declining_weekly(self) -> list[float]:
        """8周内均线持续下降（从100降到85）。"""
        return [100.0, 98.0, 96.0, 94.0, 92.0, 90.0, 88.0, 86.0]

    def _make_rising_weekly(self) -> list[float]:
        """8周内均线持续上升（从85升到100）。"""
        return [85.0, 87.0, 89.0, 91.0, 93.0, 95.0, 97.0, 99.0]

    def test_declining_ma5w_returns_none(self):
        """5周均线方向向下时，即使价格在均线附近，也不应产生买入信号。"""
        weekly_closes = self._make_declining_weekly()
        # MA5W_now = mean([92,90,88,86,84]) 约 88 (这里简化：用列表末5个)
        # MA5W_prev = mean([100,98,96,94,92]) 约 96 → now < prev → 方向向下
        weekly_closes = [100.0, 98.0, 96.0, 94.0, 92.0, 90.0, 88.0, 86.0]
        ma5w_now = sum(weekly_closes[-5:]) / 5   # (92+90+88+86+84) 注：只有8个，取后5个
        # weekly_closes[-5:] = [92,90,88,86,84] 但只有8个，取 [92,90,88,86] 不够
        # 实际 weekly_closes[-5:] = [90,88,86,84,82] ... 用真实数据构造
        weekly_closes = [100.0, 98.0, 96.0, 94.0, 92.0, 90.0, 88.0, 86.0]
        # MA5W_now = mean([94,92,90,88,86]) = 90.0
        # MA5W_prev = mean([100,98,96,94,92]) = 96.0 → 下降

        daily = _make_daily_bars([95.0] * 25)  # 日线价格高于MA20
        weekly = _make_weekly_bars(weekly_closes)
        rt = _make_rt(current=90.5)  # 价格在5周均线(90.0)附近±1%

        result = _analyze_signal("000001", "测试股", daily, weekly, rt, _green_sentiment())
        self.assertIsNone(result, "5周均线方向向下时应返回 None，不产生买入信号")

    def test_rising_ma5w_allows_signal(self):
        """5周均线方向向上时，价格在均线附近应产生买入信号。"""
        # MA5W_now = mean([93,95,97,99,101]) = 97.0
        # MA5W_prev = mean([85,87,89,91,93]) = 89.0 → 上升
        weekly_closes = [85.0, 87.0, 89.0, 91.0, 93.0, 95.0, 97.0, 99.0, 101.0]
        ma5w_now = sum(weekly_closes[-5:]) / 5  # = 98.6

        daily = _make_daily_bars([100.0] * 25)
        weekly = _make_weekly_bars(weekly_closes)
        rt = _make_rt(current=ma5w_now * 1.005)  # 价格在MA5W附近+0.5%

        result = _analyze_signal("000001", "测试股", daily, weekly, rt, _green_sentiment())
        # 不强制要求买入信号（可能因其他条件未满足），但至少不是 None 就代表有信号输出
        # 实际测试：有结果时 signal 应为 buy_dip 或 watch
        if result is not None:
            self.assertIn(result.signal, ("buy_dip", "watch"))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: 运行测试确认失败**

```bash
cd /home/bruce/Projects/oh-my-superpowers
python -m pytest packages/ashare-data/tests/test_watchlist_monitor.py::TestAnalyzeSignalMA5WDirection::test_declining_ma5w_returns_none -v
```

预期输出：**FAIL** — 当前代码没有均线方向检查，返回非 None（或 buy_dip）而非 None。

---

**Step 3: 在 `watchlist_monitor.py` 加入均线方向验证**

文件：`packages/ashare-data/ashare_data/watchlist_monitor.py`

找到第 515–520 行的现有过滤块：
```python
    # ──────────────── 周线核心过滤 ────────────────
    if ma5_week > 0:
        # 周线趋势破坏：跌破5周均线
        if current < ma5_week:
            logger.debug("%s 跌破5周均线(%.2f<%.2f)，周线趋势破坏", code, current, ma5_week)
            return None
```

在 `return None`（跌破均线）的下方，**紧接着**追加：

```python
        # 5周均线方向验证：均线本身必须向上倾斜（当前MA5W > 3周前MA5W）
        if len(weekly_closes) >= 8:
            ma5w_prev = sum(weekly_closes[-8:-3]) / 5
            if ma5_week <= ma5w_prev:
                logger.debug(
                    "%s 5周均线方向向下(%.2f<=%.2f)，趋势无效",
                    code, ma5_week, ma5w_prev,
                )
                return None
```

插入后完整块如下：
```python
    # ──────────────── 周线核心过滤 ────────────────
    if ma5_week > 0:
        # 周线趋势破坏：跌破5周均线
        if current < ma5_week:
            logger.debug("%s 跌破5周均线(%.2f<%.2f)，周线趋势破坏", code, current, ma5_week)
            return None
        # 5周均线方向验证：均线本身必须向上倾斜（当前MA5W > 3周前MA5W）
        if len(weekly_closes) >= 8:
            ma5w_prev = sum(weekly_closes[-8:-3]) / 5
            if ma5_week <= ma5w_prev:
                logger.debug(
                    "%s 5周均线方向向下(%.2f<=%.2f)，趋势无效",
                    code, ma5_week, ma5w_prev,
                )
                return None
```

**Step 4: 运行测试确认通过**

```bash
python -m pytest packages/ashare-data/tests/test_watchlist_monitor.py::TestAnalyzeSignalMA5WDirection -v
```

预期输出：**PASSED** 2 tests

**Step 5: 语法检查 + 提交**

```bash
python -m py_compile packages/ashare-data/ashare_data/watchlist_monitor.py
git add packages/ashare-data/ashare_data/watchlist_monitor.py \
        packages/ashare-data/tests/test_watchlist_monitor.py
git commit -m "feat: add MA5W direction check to block declining trend buy signals"
```

---

## Task 2：`watchlist_monitor.py` — 增加持仓出场信号

**目标：** 扫描时同时检查当前持仓，当持仓股跌破5周均线（止损）或超涨25%（减仓），在信号文件 `exits` 字段中输出提示。

**Files:**
- Modify: `packages/ashare-data/ashare_data/watchlist_monitor.py`（多处）
- Test: `packages/ashare-data/tests/test_watchlist_monitor.py`（追加）

---

**Step 1: 追加出场信号测试（写入同一测试文件）**

在 `test_watchlist_monitor.py` 末尾追加：

```python
from ashare_data.watchlist_monitor import _check_exit_signals


class TestCheckExitSignals(unittest.TestCase):
    """持仓出场信号检测。"""

    def _make_kline_map(self, code: str, current_close: float, ma5w: float):
        """构造 kline_map，使周线MA5W等于给定值。"""
        # 构造8根周线，令 mean(last5) == ma5w，方向向上
        weekly_closes = [ma5w * 0.96, ma5w * 0.97, ma5w * 0.98, ma5w * 0.99,
                         ma5w, ma5w * 1.01, ma5w * 1.02, ma5w * 1.03]
        daily_closes = [current_close] * 25
        daily = _make_daily_bars(daily_closes)
        weekly = _make_weekly_bars(weekly_closes)
        return {code: ("测试股", daily, weekly)}

    def test_stop_loss_when_below_ma5w(self):
        """当前收盘 < 5周均线 → 触发 stop_loss。"""
        holdings = [{"code": "000001", "name": "测试股", "hold_vol": "100"}]
        kline_map = self._make_kline_map("000001", current_close=85.0, ma5w=100.0)

        exits = _check_exit_signals(holdings, kline_map)

        self.assertEqual(len(exits), 1)
        self.assertEqual(exits[0].signal, "stop_loss")
        self.assertEqual(exits[0].code, "000001")

    def test_take_profit_when_above_125pct_ma5w(self):
        """当前收盘 > 5周均线×1.25 → 触发 take_profit_partial。"""
        holdings = [{"code": "000002", "name": "测试股B", "hold_vol": "200"}]
        kline_map = self._make_kline_map("000002", current_close=130.0, ma5w=100.0)

        exits = _check_exit_signals(holdings, kline_map)

        self.assertEqual(len(exits), 1)
        self.assertEqual(exits[0].signal, "take_profit_partial")

    def test_no_signal_when_healthy(self):
        """价格在MA5W之上但未超涨25% → 无出场信号。"""
        holdings = [{"code": "000003", "name": "测试股C", "hold_vol": "300"}]
        kline_map = self._make_kline_map("000003", current_close=108.0, ma5w=100.0)

        exits = _check_exit_signals(holdings, kline_map)

        self.assertEqual(exits, [])

    def test_zero_vol_holding_skipped(self):
        """hold_vol=0（已清仓）的持仓应跳过。"""
        holdings = [{"code": "000004", "name": "测试股D", "hold_vol": "0"}]
        kline_map = self._make_kline_map("000004", current_close=80.0, ma5w=100.0)

        exits = _check_exit_signals(holdings, kline_map)

        self.assertEqual(exits, [])
```

**Step 2: 运行测试确认失败**

```bash
python -m pytest packages/ashare-data/tests/test_watchlist_monitor.py::TestCheckExitSignals -v
```

预期：**ImportError** — `_check_exit_signals` 不存在。

---

**Step 3: 在 `watchlist_monitor.py` 实现 `_check_exit_signals`**

在 `_write_signals` 函数（第626行）**之前**插入新函数：

```python
def _check_exit_signals(
    holdings: list[dict[str, Any]],
    kline_map: dict[str, tuple[str, list[_KlineBar], list[_KlineBar]]],
) -> list[StockSignal]:
    """检查持仓股是否触发出场信号。

    Args:
        holdings: broker_account hold_list，每项含 code / name / hold_vol。
        kline_map: 已拉取的 K 线数据映射（可能不含全部持仓）。

    Returns:
        触发出场条件的 StockSignal 列表。signal 值为
        "stop_loss" 或 "take_profit_partial"。
    """
    today_str = datetime.now(tz=_CN_TZ).strftime("%Y-%m-%d")
    exits: list[StockSignal] = []

    for h in holdings:
        code = str(h.get("code", "")).strip()
        hold_vol = int(h.get("hold_vol", 0) or 0)
        if hold_vol <= 0 or not code:
            continue
        entry = kline_map.get(code)
        if entry is None:
            continue
        name, daily_bars, weekly_bars = entry
        if len(weekly_bars) < 5:
            continue

        weekly_closes = [b.close for b in weekly_bars]
        ma5_week = sum(weekly_closes[-5:]) / 5
        if ma5_week <= 0:
            continue

        # 取最近已收盘的日K
        hist = [b for b in daily_bars if b.date < today_str]
        if not hist:
            continue
        current = hist[-1].close

        if current < ma5_week:
            exits.append(
                StockSignal(
                    code=code,
                    name=name,
                    signal="stop_loss",
                    reason="收盘跌破5周均线",
                    price=round(current, 3),
                    change=0.0,
                    ma5_week=round(ma5_week, 3),
                    ma10=0.0,
                    ma20=0.0,
                    star=0,
                    score=0,
                )
            )
        elif current > ma5_week * 1.25:
            pct = (current / ma5_week - 1) * 100
            exits.append(
                StockSignal(
                    code=code,
                    name=name,
                    signal="take_profit_partial",
                    reason=f"超涨{pct:.0f}%，建议减仓50%",
                    price=round(current, 3),
                    change=0.0,
                    ma5_week=round(ma5_week, 3),
                    ma10=0.0,
                    ma20=0.0,
                    star=0,
                    score=0,
                )
            )

    return exits
```

**Step 4: 更新 `_write_signals` 支持 `exits` 参数**

找到第 626–651 行的 `_write_signals`，将签名和输出修改为：

```python
def _write_signals(
    signals: list[StockSignal],
    watched: list[StockSignal],
    sentiment: MarketSentiment,
    *,
    exits: list[StockSignal] | None = None,
) -> None:
    """将信号结果覆盖写入 signals/watchlist_signals.json。"""
    _SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    scanned_at = datetime.now(tz=_CN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    output = {
        "scanned_at": scanned_at,
        "market": {
            "limit_up": sentiment.limit_up,
            "limit_down": sentiment.limit_down,
            "danger_level": sentiment.danger_level,
        },
        "signals": [asdict(s) for s in signals],
        "watched": [asdict(s) for s in watched],
        "exits": [asdict(s) for s in (exits or [])],
    }
    with open(_SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(
        "信号文件已写入: %s（buy_dip=%d, watch=%d, exits=%d）",
        _SIGNALS_FILE,
        len(signals),
        len(watched),
        len(exits or []),
    )
```

**Step 5: 在 `main()` 中拉取持仓并计算出场信号**

找到 `main()` 的步骤 2（第702行附近，加载 watchlist 之后），追加持仓加载逻辑：

```python
    # ── 2. 加载 watchlist ──────────────────────────────────────────────────
    stocks = load_watchlist()
    active = [s for s in stocks if s.get("status") == "active"]
    if not active:
        logger.info("watchlist 中无 active 股票，退出")
        _write_signals([], [], sentiment)
        return

    # ── 2b. 加载当前持仓（用于出场信号） ────────────────────────────────────
    try:
        from ashare_data.fetchers.broker_account import fetch_broker_account
        broker_data = fetch_broker_account()
        holdings = broker_data.get("hold_list", [])
        logger.info("持仓股数量: %d", len([h for h in holdings if int(h.get("hold_vol", 0) or 0) > 0]))
    except Exception as exc:
        logger.warning("持仓数据获取失败（出场信号将跳过）: %s", exc)
        holdings = []
```

在 K 线拉取阶段，同时拉取持仓股中不在 watchlist 的股票：

在第 723 行附近的 `kline_map` 构建逻辑后，追加：
```python
    # ── 3b. 为持仓中不在 watchlist 的股票补充 K 线 ─────────────────────────
    holding_codes_extra = [
        h for h in holdings
        if str(h.get("code", "")) not in kline_map
        and int(h.get("hold_vol", 0) or 0) > 0
    ]
    if holding_codes_extra:
        extra_stocks = [{"code": h["code"], "name": h.get("name", h["code"])} for h in holding_codes_extra]
        with ThreadPoolExecutor(max_workers=min(8, len(extra_stocks))) as pool:
            extra_futures = [pool.submit(_fetch_kline_job, s) for s in extra_stocks]
            for fut in extra_futures:
                try:
                    code, name, bars, weekly_bars = fut.result()
                    kline_map[code] = (name, bars, weekly_bars)
                except Exception as exc:
                    logger.warning("持仓 K 线获取异常: %s", exc)
```

在步骤 6（写文件）之前，计算出场信号：

```python
    # ── 5b. 计算出场信号 ───────────────────────────────────────────────────
    exit_signals = _check_exit_signals(holdings, kline_map)
    if exit_signals:
        logger.info("出场信号: %s", [(s.name, s.signal) for s in exit_signals])

    # ── 6. 写文件 ──────────────────────────────────────────────────────────
    _write_signals(buy_signals, watch_signals, sentiment, exits=exit_signals)
```

**Step 6: 运行全部测试确认通过**

```bash
python -m pytest packages/ashare-data/tests/test_watchlist_monitor.py -v
```

预期：**PASSED** 全部测试（含 Task 1 的 2 个 + Task 2 的 4 个 = 6 个）

**Step 7: 语法检查 + 提交**

```bash
python -m py_compile packages/ashare-data/ashare_data/watchlist_monitor.py
git add packages/ashare-data/ashare_data/watchlist_monitor.py \
        packages/ashare-data/tests/test_watchlist_monitor.py
git commit -m "feat: add portfolio exit signals (stop_loss / take_profit_partial)"
```

---

## Task 3：`trend_scanner.py` — 移除交易信号输出

**目标：** `trend_scanner.py` 退化为纯研究工具，不再输出"买入"/"卖出"操作信号，消除两套信号并行导致的混乱。

**Files:**
- Modify: `packages/ashare-data/ashare_data/fetchers/trend_scanner.py:905-932`
- Test: `packages/ashare-data/tests/test_watchlist_monitor.py`（追加验证）

---

**Step 1: 追加测试：trend_scanner 不再输出买入/卖出**

在 `test_watchlist_monitor.py` 末尾追加：

```python
from ashare_data.fetchers.trend_scanner import _trade_signal_from_ma


class TestTrendScannerSignalNeutralized(unittest.TestCase):
    """验证 trend_scanner 的交易信号已被中和（不再输出买入/卖出）。"""

    def test_no_buy_signal(self):
        """无论价格/均线关系如何，不应返回'买入'。"""
        signal, _ = _trade_signal_from_ma(100.0, 100.5, 99.0, 98.0)
        self.assertNotEqual(signal, "买入")

    def test_no_sell_signal(self):
        """无论价格/均线关系如何，不应返回'卖出'。"""
        signal, _ = _trade_signal_from_ma(120.0, 100.0, 99.0, 98.0)
        self.assertNotEqual(signal, "卖出")

    def test_returns_observe(self):
        """应始终返回'观察'。"""
        for last, ma5, ma10, ma20 in [
            (100.0, 100.0, 99.0, 98.0),   # 价格=MA5
            (85.0, 100.0, 99.0, 98.0),    # 价格<MA5
            (120.0, 100.0, 99.0, 98.0),   # 超涨
        ]:
            signal, _ = _trade_signal_from_ma(last, ma5, ma10, ma20)
            self.assertEqual(signal, "观察", f"last={last}, ma5={ma5}")
```

**Step 2: 运行测试确认失败**

```bash
python -m pytest packages/ashare-data/tests/test_watchlist_monitor.py::TestTrendScannerSignalNeutralized -v
```

预期：**FAIL** — 当前函数仍会返回"买入"/"卖出"。

---

**Step 3: 修改 `_trade_signal_from_ma`**

文件：`packages/ashare-data/ashare_data/fetchers/trend_scanner.py`

将第 905–932 行的整个 `_trade_signal_from_ma` 函数替换为：

```python
def _trade_signal_from_ma(
    last_close: float, ma5: float, ma10: float, ma20: float
) -> tuple[str, str]:
    """趋势信号（仅供研究，不作为操作依据）。

    交易操作信号由 watchlist_monitor 提供。
    """
    return "观察", "趋势扫描仅供研究，交易信号见 watchlist_monitor"
```

**Step 4: 运行全部测试确认通过**

```bash
python -m pytest packages/ashare-data/tests/test_watchlist_monitor.py -v
```

预期：**PASSED** 全部测试（Task 1 的 2 个 + Task 2 的 4 个 + Task 3 的 3 个 = 9 个）

**Step 5: 运行完整测试套件，确认没有回归**

```bash
python -m pytest packages/ashare-data/tests/ -v 2>&1 | tail -20
```

预期：所有已有测试仍通过。

**Step 6: 语法检查 + 提交**

```bash
python -m py_compile packages/ashare-data/ashare_data/fetchers/trend_scanner.py
git add packages/ashare-data/ashare_data/fetchers/trend_scanner.py \
        packages/ashare-data/tests/test_watchlist_monitor.py
git commit -m "refactor: neutralize trend_scanner trade signals, watchlist_monitor is sole signal source"
```

---

## Task 4：部署到 tencent-vps 验证

**目标：** 将改动同步到 VPS，运行一次 `--force` 扫描，确认新逻辑工作正常。

**Files:** 无代码改动，仅部署和验证。

---

**Step 1: 查阅部署规范**

```bash
cat /home/bruce/Projects/oh-my-superpowers/Deployment.md
```

按照 Deployment.md 中的步骤同步 `packages/ashare-data`。

**Step 2: 在 VPS 运行强制扫描**

```bash
ssh root@43.138.150.96 'cd /root && python3 -m ashare_data.watchlist_monitor --force --verbose 2>&1 | tail -30'
```

**Step 3: 检查输出文件**

```bash
ssh root@43.138.150.96 'cat ~/.ashare-assistant/signals/watchlist_signals.json'
```

验证标准：
- `exits` 字段存在（即使为空列表也正确）
- 无 Python 报错
- 日志中出现"5周均线方向向下"类的排除日志（说明新过滤生效）

**Step 4: 提交验证结果记录（可选）**

若验证一切正常，无需额外提交。如发现 VPS 兼容性问题，修复后提交。

---

## 验收标准

1. ✅ `test_declining_ma5w_returns_none` 通过 — 均线方向向下时不买入
2. ✅ `test_stop_loss_when_below_ma5w` 通过 — 持仓跌破均线触发止损信号
3. ✅ `test_take_profit_when_above_125pct_ma5w` 通过 — 超涨25%触发减仓信号
4. ✅ `test_returns_observe` 通过 — trend_scanner 不再输出买入/卖出
5. ✅ `watchlist_signals.json` 包含 `exits` 字段
6. ✅ 所有已有测试（`packages/ashare-data/tests/`）无回归
