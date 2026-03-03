"""测试 watchlist_monitor 的信号逻辑。"""
import unittest
from ashare_data.watchlist_monitor import _analyze_signal, _check_exit_signals, _KlineBar, _RealtimeQuote
from ashare_data.fetchers.market_sentiment import MarketSentiment
from ashare_data.fetchers.trend_scanner import _trade_signal_from_ma


def _make_daily_bars(closes: list[float]) -> list[_KlineBar]:
    """构造日K列表，日期从 2026-01-01 起。"""
    bars = []
    for i, c in enumerate(closes):
        if i < 28:
            date = f"2026-01-{i+1:02d}"
        else:
            date = f"2026-02-{i-27:02d}"
        bars.append(_KlineBar(date=date, open=c, high=c, low=c, close=c, volume=1000))
    return bars


def _make_weekly_bars(closes: list[float]) -> list[_KlineBar]:
    bars = []
    for i, c in enumerate(closes):
        bars.append(_KlineBar(date=f"2026-W{i+1:02d}", open=c, high=c, low=c, close=c, volume=5000))
    return bars


def _make_rt(current: float, change_pct: float = -4.0, volume_lot: int = 800) -> _RealtimeQuote:
    return _RealtimeQuote(
        code="000001",
        name="测试股",
        current=current,
        prev_close=current * 1.04,
        open=current,
        high=current,
        low=current,
        volume_lot=volume_lot,
        change_pct=change_pct,
    )


def _green_sentiment() -> MarketSentiment:
    return MarketSentiment(limit_up=80, limit_down=20, danger_level="green", market_open=True)


class TestAnalyzeSignalMA5WDirection(unittest.TestCase):
    """均线方向验证：5周均线向下时不应产生买入信号。"""

    def test_declining_ma5w_returns_none(self):
        """5周均线方向向下时，即使价格在均线附近，也不应产生任何信号。

        weekly_closes = [100, 98, 96, 94, 92, 90, 88, 86]
        # weekly_closes = [100, 98, 96, 94, 92, 90, 88, 86]
        # MA5W_now  = mean([-5:]) = mean([94,92,90,88,86]) = 90.0
        # MA5W_prev = mean([-8:-3]) = mean([100,98,96,94,92]) = 96.0
        # 90.0 <= 96.0 → 方向向下 → 应返回 None
        """
        weekly_closes = [100.0, 98.0, 96.0, 94.0, 92.0, 90.0, 88.0, 86.0]

        # 日线价格设为89，使 MA20=89，而 current=90.5 > MA20，不被日线过滤
        daily = _make_daily_bars([89.0] * 25)
        weekly = _make_weekly_bars(weekly_closes)
        rt = _make_rt(current=90.5, change_pct=-4.0, volume_lot=500)  # volume_lot=500 < avg_vol=1000*0.7=700

        result = _analyze_signal("000001", "测试股", daily, weekly, rt, _green_sentiment())
        self.assertIsNone(result, "5周均线方向向下时应返回 None，不产生买入信号")

    def test_rising_ma5w_allows_signal(self):
        """5周均线方向向上时，价格在均线附近，代码不应因方向检查被拦截。

        weekly_closes = [85, 87, 89, 91, 93, 95, 97, 99, 101]
        MA5W_now  = mean([93,95,97,99,101]) = 97.0
        MA5W_prev = mean([85,87,89,91,93]) = 89.0
        方向：97.0 > 89.0 → 向上 → 不因方向被拦截
        """
        weekly_closes = [85.0, 87.0, 89.0, 91.0, 93.0, 95.0, 97.0, 99.0, 101.0]
        ma5w_now = sum(weekly_closes[-5:]) / 5  # = (93+95+97+99+101)/5 = 97.0

        # MA20=96.0 < current=97.97，不被日线 MA20 过滤
        daily = _make_daily_bars([96.0] * 25)
        weekly = _make_weekly_bars(weekly_closes)
        # 价格在MA5W附近 +1%，触发买入区间
        rt = _make_rt(current=round(ma5w_now * 1.01, 2))

        result = _analyze_signal("000001", "测试股", daily, weekly, rt, _green_sentiment())
        # 5周均线向上，不应被方向检查拦截，必须产生合法信号
        self.assertIsNotNone(result, "5周均线方向向上时不应被方向检查拦截")
        self.assertIn(result.signal, ("buy_dip", "watch"))


class TestCheckExitSignals(unittest.TestCase):
    """持仓出场信号检测。"""

    def _make_kline_map(self, code: str, current_close: float, ma5w: float) -> dict:
        """构造 kline_map，令 mean(weekly[-5:]) ≈ ma5w，且均线方向向上。

        Args:
            code: 股票代码。
            current_close: 最近收盘价（写入日K最后一根的 close）。
            ma5w: 目标5周均线值，构造8根周K令 mean(last5)=ma5w。
        """
        # 8根周K，后5根均值=ma5w，且整体向上（前3根小于后5根）
        weekly_closes = [
            ma5w * 0.96, ma5w * 0.97, ma5w * 0.98,  # 前3根（较小）
            ma5w * 0.99, ma5w, ma5w * 1.0, ma5w * 1.0, ma5w * 1.0,  # 后5根，均值=ma5w
        ]
        # 注意：mean([0.99,1,1,1,1]*ma5w) = ma5w * 1.0 = ma5w ✓
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
            (100.0, 100.0, 99.0, 98.0),
            (85.0, 100.0, 99.0, 98.0),
            (120.0, 100.0, 99.0, 98.0),
        ]:
            signal, _ = _trade_signal_from_ma(last, ma5, ma10, ma20)
            self.assertEqual(signal, "观察", f"last={last}, ma5={ma5}")


if __name__ == "__main__":
    unittest.main()
