"""测试 watchlist_monitor 的信号逻辑。"""
import unittest
from ashare_data.watchlist_monitor import _analyze_signal, _KlineBar, _RealtimeQuote
from ashare_data.fetchers.market_sentiment import MarketSentiment


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


if __name__ == "__main__":
    unittest.main()
