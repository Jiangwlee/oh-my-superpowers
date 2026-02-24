"""trade_review 核心逻辑单元测试。"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

import scripts.trade_review as tr


def _base_order(
    *,
    code: str = "000001",
    name: str = "平安银行",
    direction: str = "buy",
    status: str = "已成",
    price: float = 10.0,
    amount: int = 100,
) -> dict:
    return {
        "code": code,
        "name": name,
        "direction": direction,
        "status": status,
        "price": price,
        "amount": amount,
    }


class UnplannedTradeTest(unittest.TestCase):
    def test_unplanned_buy_detected(self) -> None:
        orders = [_base_order(code="002345", name="潮宏基", direction="buy")]
        candidates = [{"code": "000001", "name": "平安银行", "action": "buy", "score": 90}]

        flaws = tr._check_unplanned_trades(orders, candidates)

        self.assertEqual(len(flaws), 1)
        self.assertEqual(flaws[0]["category"], "unplanned_trade")
        self.assertIn("计划外买入", flaws[0]["message"])

    def test_watch_stock_bought_detected(self) -> None:
        orders = [_base_order(code="000001", direction="buy")]
        candidates = [{"code": "000001", "name": "平安银行", "action": "watch", "score": 70}]

        flaws = tr._check_unplanned_trades(orders, candidates)

        self.assertEqual(len(flaws), 1)
        self.assertIn("观察股误买", flaws[0]["message"])


class MissedExecutionTest(unittest.TestCase):
    def test_missed_high_score_buy_is_warning(self) -> None:
        orders: list[dict] = []
        positions = {"hold_list": []}
        candidates = [
            {"code": "300750", "name": "宁德时代", "action": "buy", "score": 85},
        ]

        flaws = tr._check_missed_execution(orders, candidates, positions)

        self.assertEqual(len(flaws), 1)
        self.assertEqual(flaws[0]["severity"], "warning")
        self.assertIn("未执行", flaws[0]["message"])

    def test_already_held_not_flagged(self) -> None:
        orders: list[dict] = []
        positions = {"hold_list": [{"code": "300750", "name": "宁德时代"}]}
        candidates = [{"code": "300750", "name": "宁德时代", "action": "buy", "score": 90}]

        flaws = tr._check_missed_execution(orders, candidates, positions)

        self.assertEqual(flaws, [])


class TimingAnalysisTest(unittest.TestCase):
    def test_calc_vwap_jrj_amount_scaled(self) -> None:
        bars = [
            {"amount": 1_161_700_000.0, "volume": 10000, "avg": 0.0},
            {"amount": 2_323_400_000.0, "volume": 20000, "avg": 0.0},
        ]

        vwap = tr._calc_vwap(bars)

        self.assertAlmostEqual(vwap, 11.617, places=3)

    @mock.patch("scripts.trade_review.fetch_jrj_minute_kline")
    def test_chasing_high_buy_detected(self, mock_minute: mock.Mock) -> None:
        mock_minute.return_value = [
            {"time": 1, "low": 10.0, "high": 10.2, "amount": 10000.0, "volume": 1000},
            {"time": 2, "low": 10.2, "high": 12.0, "amount": 24000.0, "volume": 2000},
        ]
        orders = [_base_order(price=11.7, direction="buy", status="已成")]

        flaws, scores = tr._analyze_timing(orders)

        self.assertTrue(any("追高" in x["message"] for x in flaws))
        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0]["direction"], "buy")

    @mock.patch("scripts.trade_review.fetch_jrj_minute_kline")
    def test_panic_sell_detected(self, mock_minute: mock.Mock) -> None:
        mock_minute.return_value = [
            {"time": 1, "low": 9.0, "high": 10.0, "amount": 9000.0, "volume": 1000},
            {"time": 2, "low": 9.0, "high": 12.0, "amount": 24000.0, "volume": 2000},
        ]
        orders = [_base_order(price=9.2, direction="sell", status="已成")]

        flaws, scores = tr._analyze_timing(orders)

        self.assertTrue(any("恐慌卖出" in x["message"] for x in flaws))
        self.assertEqual(scores[0]["direction"], "sell")

    @mock.patch("scripts.trade_review.fetch_jrj_minute_kline")
    def test_same_code_orders_fetch_minute_kline_once(self, mock_minute: mock.Mock) -> None:
        mock_minute.return_value = [
            {"time": 1, "low": 10.0, "high": 11.0, "amount": 10000.0, "volume": 1000}
        ]
        orders = [
            _base_order(code="000001", direction="buy", price=10.2, status="已成"),
            _base_order(code="000001", direction="sell", price=10.8, status="已成"),
        ]

        tr._analyze_timing(orders)

        self.assertEqual(mock_minute.call_count, 1)


class PositionCheckTest(unittest.TestCase):
    def test_single_stock_over_limit(self) -> None:
        positions = {
            "total": 100000.0,
            "usable": 10000.0,
            "hold_earn": 0.0,
            "hold_list": [
                {"code": "000001", "name": "平安银行", "market_value": 35000.0},
                {"code": "000002", "name": "万科A", "market_value": 55000.0},
            ],
        }
        strategy = {
            "market_position": {"neutral": "3-5成仓位"},
            "trend_stock": {"position": "单只不超过总仓位20%"},
        }

        flaws, check = tr._check_position_compliance(positions, strategy, "neutral")

        self.assertFalse(check["compliant"])
        self.assertTrue(any("单股仓位超限" in x["message"] for x in flaws))

    def test_weak_market_heavy_position_no_duplicate_flaw(self) -> None:
        positions = {
            "total": 100000.0,
            "usable": 10000.0,
            "hold_earn": 0.0,
            "hold_list": [{"code": "000001", "name": "平安银行", "market_value": 90000.0}],
        }
        strategy = {
            "market_position": {"weak": "1-2成仓位"},
            "trend_stock": {"position": "单只不超过总仓位20%"},
        }

        flaws, _ = tr._check_position_compliance(positions, strategy, "weak")

        msgs = [x["message"] for x in flaws if x["category"] == "position_flaw"]
        self.assertEqual(msgs.count("弱市重仓"), 1)
        self.assertFalse(any("weak 市仓位过高" == m for m in msgs))

    def test_defensive_mode_constraint(self) -> None:
        positions = {
            "total": 100000.0,
            "usable": 40000.0,
            "hold_earn": -15000.0,  # -15% -> defensive
            "hold_list": [{"code": "000001", "name": "平安银行", "market_value": 60000.0}],
        }
        strategy = {
            "market_position": {"neutral": "3-5成仓位"},
            "trend_stock": {"position": "单只不超过总仓位20%"},
        }

        flaws, check = tr._check_position_compliance(positions, strategy, "neutral")

        self.assertEqual(check["account_mode"], "defensive")
        self.assertTrue(any("防御模式仓位过高" in x["message"] for x in flaws))


class DisciplineTest(unittest.TestCase):
    def test_flip_trading_detected_within_3_days(self) -> None:
        history = {
            "orders": {
                "2026-02-24": {"order_list": [_base_order(code="000001", direction="buy")]},
                "2026-02-23": {"order_list": []},
                "2026-02-22": {"order_list": [_base_order(code="000001", direction="sell")]},
                "2026-02-21": {"order_list": [_base_order(code="000002", direction="sell")]},
            }
        }

        flaws = tr._check_discipline([], "normal", history)

        self.assertTrue(any(f.get("code") == "000001" and "频繁翻转交易" in f["message"] for f in flaws))

    def test_flip_trading_not_detected_outside_3_days(self) -> None:
        history = {
            "orders": {
                "2026-02-24": {"order_list": [_base_order(code="000001", direction="buy")]},
                "2026-02-23": {"order_list": []},
                "2026-02-22": {"order_list": []},
                "2026-02-21": {"order_list": [_base_order(code="000001", direction="sell")]},
            }
        }

        flaws = tr._check_discipline([], "normal", history)

        self.assertFalse(any(f.get("code") == "000001" and "频繁翻转交易" in f["message"] for f in flaws))

    def test_defensive_mode_new_buy(self) -> None:
        flaws = tr._check_discipline([_base_order(direction="buy")], "defensive", {"orders": {}})
        self.assertTrue(any("防御模式下加仓" in f["message"] for f in flaws))


class HoldingManagementTest(unittest.TestCase):
    @mock.patch("scripts.trade_review.fetch_jrj_daily_kline")
    def test_ma20_stop_loss_missed(self, mock_daily: mock.Mock) -> None:
        mock_daily.return_value = [{"close": 10.0} for _ in range(30)]
        hold_list = [{"code": "000001", "name": "平安银行", "current_price": 9.0}]
        history = {
            "positions": {
                "2026-02-23": {"hold_list": [{"code": "000001", "price": 9.1}]},
                "2026-02-22": {"hold_list": [{"code": "000001", "price": 9.2}]},
            }
        }

        flaws = tr._check_holding_management(hold_list, history)

        self.assertTrue(any("未执行MA20止损" in f["message"] for f in flaws))

    @mock.patch("scripts.trade_review.fetch_jrj_daily_kline")
    def test_ma5_deviation_take_profit(self, mock_daily: mock.Mock) -> None:
        mock_daily.return_value = [{"close": 10.0} for _ in range(30)]
        hold_list = [{"code": "000001", "name": "平安银行", "current_price": 12.2}]

        flaws = tr._check_holding_management(hold_list, {"positions": {}})

        self.assertTrue(any("偏离MA5超20%" in f["message"] for f in flaws))


class RunTradeReviewTest(unittest.TestCase):
    def test_run_trade_review_outputs_summary(self) -> None:
        broker_data = {
            "total": 100000.0,
            "usable": 50000.0,
            "day_earn": 1200.0,
            "hold_earn": 2000.0,
            "hold_list": [{"code": "000001", "name": "平安银行", "market_value": 50000.0}],
            "order_list": [_base_order(price=10.8, direction="buy", status="已成")],
            "fetched_at": "2026-02-24T15:00:00+08:00",
        }
        decision = {
            "as_of_date": "2026-02-24",
            "run_id": "20260224-review-150000",
            "market_regime": "neutral",
            "candidates": [{"code": "000001", "name": "平安银行", "score": 88, "action": "buy"}],
        }
        strategy = {
            "strategy_version": "v1.0",
            "market_position": {"neutral": "3-5成仓位"},
            "trend_stock": {"position": "单只不超过总仓位20%"},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "trade_review.json"
            with (
                mock.patch("scripts.trade_review._load_latest_decision", return_value=decision),
                mock.patch("scripts.trade_review._load_strategy", return_value=strategy),
                mock.patch("scripts.trade_review._analyze_timing", return_value=([], [])),
                mock.patch("scripts.trade_review._check_holding_management", return_value=[]),
                mock.patch("scripts.trade_review._check_discipline", return_value=[]),
                mock.patch("scripts.trade_review.load_history", return_value={"positions": {}, "orders": {}}),
            ):
                result = tr.run_trade_review(
                    broker_data=broker_data,
                    decision_log_path="ignored.jsonl",
                    strategy_path="ignored.yaml",
                    output_path=str(out_path),
                )

            self.assertTrue(out_path.exists())
            on_disk = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(on_disk["review_date"], "2026-02-24")
            self.assertIn("execution_summary", result)
            self.assertIn("flaw_counts", result)

    def test_no_orders_day(self) -> None:
        broker_data = {
            "total": 100000.0,
            "usable": 70000.0,
            "day_earn": 0.0,
            "hold_earn": 0.0,
            "hold_list": [],
            "order_list": [],
            "fetched_at": "2026-02-24T15:00:00+08:00",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "trade_review.json"
            with (
                mock.patch("scripts.trade_review._load_latest_decision", return_value=None),
                mock.patch("scripts.trade_review._load_strategy", return_value={"strategy_version": "v1.0"}),
                mock.patch("scripts.trade_review.load_history", return_value={"positions": {}, "orders": {}}),
            ):
                result = tr.run_trade_review(broker_data=broker_data, output_path=str(out_path))

        self.assertEqual(result["execution_summary"]["total_orders"], 0)
        self.assertEqual(result["timing_scores"], [])

    def test_no_decision_log(self) -> None:
        broker_data = {
            "total": 100000.0,
            "usable": 80000.0,
            "day_earn": 0.0,
            "hold_earn": 0.0,
            "hold_list": [],
            "order_list": [_base_order(direction="buy", status="已成")],
            "fetched_at": "2026-02-24T15:00:00+08:00",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "trade_review.json"
            with (
                mock.patch("scripts.trade_review._load_latest_decision", return_value=None),
                mock.patch("scripts.trade_review._load_strategy", return_value={"strategy_version": "v1.0"}),
                mock.patch("scripts.trade_review._analyze_timing", return_value=([], [])),
                mock.patch("scripts.trade_review._check_holding_management", return_value=[]),
                mock.patch("scripts.trade_review._check_discipline", return_value=[]),
                mock.patch("scripts.trade_review.load_history", return_value={"positions": {}, "orders": {}}),
            ):
                result = tr.run_trade_review(broker_data=broker_data, output_path=str(out_path))

        self.assertFalse(result["metadata"]["data_completeness"]["decision_log"])
        self.assertTrue(any("无交易计划日的买入" in f["message"] for f in result["flaws"]))


if __name__ == "__main__":
    unittest.main()
