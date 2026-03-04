"""测试 watchlist_monitor 的状态机信号逻辑。"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ashare_data.watchlist_monitor as monitor
from ashare_data.fetchers.market_sentiment import MarketSentiment
from ashare_data.watchlist_monitor import _KlineBar, _RealtimeQuote


_CN_TZ = timezone(timedelta(hours=8))


def _make_daily_bars(closes: list[float], volume: float = 1000.0) -> list[_KlineBar]:
    end_date = datetime.now(tz=_CN_TZ).date() - timedelta(days=1)
    bars: list[_KlineBar] = []
    for idx, close in enumerate(closes):
        day = end_date - timedelta(days=len(closes) - 1 - idx)
        bars.append(
            _KlineBar(
                date=day.strftime("%Y-%m-%d"),
                open=close,
                close=close,
                high=close,
                low=close,
                volume=volume,
            )
        )
    return bars


def _make_weekly_bars(closes: list[float]) -> list[_KlineBar]:
    bars: list[_KlineBar] = []
    for idx, close in enumerate(closes):
        bars.append(
            _KlineBar(
                date=f"2025-W{idx + 1:02d}",
                open=close,
                close=close,
                high=close,
                low=close,
                volume=5000.0,
            )
        )
    return bars


def _make_rt(
    *,
    current: float,
    open_price: float | None = None,
    high: float | None = None,
    low: float | None = None,
    volume_lot: float = 600.0,
    change_pct: float = 0.0,
) -> _RealtimeQuote:
    return _RealtimeQuote(
        code="000001",
        name="测试股",
        current=current,
        prev_close=current,
        open=open_price if open_price is not None else current,
        high=high if high is not None else current,
        low=low if low is not None else current,
        volume_lot=volume_lot,
        change_pct=change_pct,
    )


def _sentiment_green() -> MarketSentiment:
    return MarketSentiment(limit_up=80, limit_down=20, danger_level="green", market_open=True)


class TestSignalStateMachine(unittest.TestCase):
    """SETUP/ENTRY/HOLD 状态转换。"""

    def setUp(self) -> None:
        self.params = dict(monitor._DEFAULT_SIGNAL_PARAMS)
        self.daily_closes = [float(x) for x in range(70, 105)]
        self.weekly_closes = [float(x) for x in range(80, 110)]
        self.daily = _make_daily_bars(self.daily_closes)
        self.weekly = _make_weekly_bars(self.weekly_closes)

    def test_setup_state_created(self) -> None:
        ma5w = sum(self.weekly_closes[-5:]) / 5
        rt = _make_rt(current=ma5w * 1.01, volume_lot=500.0, high=ma5w * 1.015, low=ma5w * 0.995)
        signal, next_state = monitor._analyze_signal(
            "000001", "测试股", self.daily, self.weekly, rt, _sentiment_green(), self.params, None
        )
        self.assertIsNotNone(signal)
        self.assertEqual(signal.state, "SETUP")
        self.assertIsNotNone(next_state)
        self.assertGreater(next_state["pb_high"], next_state["pb_low"])

    def test_entry_only_when_breakout_confirmed(self) -> None:
        setup_state = {
            "pb_start_date": "2026-03-01",
            "pb_high": 99.0,
            "pb_low": 95.0,
            "updated_at": "2026-03-01 15:00:00",
        }
        rt = _make_rt(current=100.0, open_price=98.0, high=100.2, low=99.0, volume_lot=1400.0)
        signal, next_state = monitor._analyze_signal(
            "000001", "测试股", self.daily, self.weekly, rt, _sentiment_green(), self.params, setup_state
        )
        self.assertIsNotNone(signal)
        self.assertEqual(signal.state, "ENTRY")
        self.assertIsNone(next_state)
        self.assertGreater(signal.stop_price, 0.0)

    def test_hold_when_in_acceleration_zone(self) -> None:
        ma20w = sum(self.weekly_closes[-20:]) / 20
        rt = _make_rt(current=ma20w * 1.35, volume_lot=900.0)
        signal, next_state = monitor._analyze_signal(
            "000001", "测试股", self.daily, self.weekly, rt, _sentiment_green(), self.params, None
        )
        self.assertIsNotNone(signal)
        self.assertEqual(signal.state, "HOLD")
        self.assertEqual(signal.action_next_day, "no_new_position")
        self.assertIsNone(next_state)


class TestExitSignals(unittest.TestCase):
    """REDUCE/EXIT 出场逻辑。"""

    def setUp(self) -> None:
        self.params = dict(monitor._DEFAULT_SIGNAL_PARAMS)

    def test_exit_when_two_week_breakdown(self) -> None:
        weekly = _make_weekly_bars([80.0] * 25 + [78.0, 76.0, 74.0, 72.0, 70.0, 68.0])
        daily = _make_daily_bars([68.0] * 30)
        kline_map = {"000001": ("测试股", daily, weekly)}
        holdings = [{"code": "000001", "name": "测试股", "hold_vol": "100"}]
        exits = monitor._check_exit_signals(holdings, kline_map, self.params)
        self.assertTrue(exits)
        self.assertEqual(exits[0].state, "EXIT")

    def test_reduce_when_overextended(self) -> None:
        weekly = _make_weekly_bars([50.0 + i for i in range(30)])
        ma5w = sum([b.close for b in weekly][-5:]) / 5
        daily = _make_daily_bars([ma5w * 1.28] * 30)
        kline_map = {"000002": ("测试股B", daily, weekly)}
        holdings = [{"code": "000002", "name": "测试股B", "hold_vol": "100"}]
        exits = monitor._check_exit_signals(holdings, kline_map, self.params)
        states = [item.state for item in exits]
        self.assertIn("REDUCE", states)


class TestPullbackStateStore(unittest.TestCase):
    """状态文件读写。"""

    def test_load_and_save_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "pullback_state.json"
            original = monitor._PULLBACK_STATE_FILE
            monitor._PULLBACK_STATE_FILE = state_file
            try:
                payload = {"000001": {"pb_start_date": "2026-03-03", "pb_high": 100.0, "pb_low": 95.0}}
                monitor._save_pullback_state(payload)
                loaded = monitor._load_pullback_state()
                self.assertEqual(loaded["000001"]["pb_high"], 100.0)
                self.assertEqual(loaded["000001"]["pb_low"], 95.0)
                raw = json.loads(state_file.read_text(encoding="utf-8"))
                self.assertIn("000001", raw)
            finally:
                monitor._PULLBACK_STATE_FILE = original


class TestPostCloseBuyTargets(unittest.TestCase):
    """盘后买入信号读取。"""

    def test_load_post_close_buy_targets_filters_non_buy_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            signals_file = Path(tmpdir) / "post_close_decisions.json"
            payload = {
                "decisions": [
                    {"code": "000001", "name": "平安银行", "action": "open"},
                    {"code": "000002", "name": "万科A", "action": "hold"},
                    {"code": "000003", "name": "国农科技", "action": "buy_open_t1"},
                    {"code": "000001", "name": "平安银行", "action": "add"},
                ]
            }
            signals_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            original = monitor._POST_CLOSE_FILE
            monitor._POST_CLOSE_FILE = signals_file
            try:
                targets = monitor._load_post_close_buy_targets()
            finally:
                monitor._POST_CLOSE_FILE = original

            self.assertEqual([row["code"] for row in targets], ["000001", "000003"])


class TestHoldingsSnapshotLoad(unittest.TestCase):
    """持仓快照加载。"""

    def test_load_latest_holdings_snapshot_uses_latest_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            positions_dir = Path(tmpdir)
            (positions_dir / "2026-03-01.json").write_text(
                json.dumps(
                    {
                        "hold_list": [
                            {"code": "000001", "name": "平安银行", "hold_vol": "100"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (positions_dir / "2026-03-03.json").write_text(
                json.dumps(
                    {
                        "hold_list": [
                            {"code": "000002", "name": "万科A", "hold_vol": "200"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            original = monitor._POSITIONS_DIR
            monitor._POSITIONS_DIR = positions_dir
            try:
                date_str, rows = monitor._load_latest_holdings_snapshot()
            finally:
                monitor._POSITIONS_DIR = original
            self.assertEqual(date_str, "2026-03-03")
            self.assertEqual([r["code"] for r in rows], ["000002"])


if __name__ == "__main__":
    unittest.main()
