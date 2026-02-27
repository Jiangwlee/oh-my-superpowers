"""broker_account 持久化层单元测试。

测试 _persist_account_data / load_history / _save_daily_data 的逻辑，
不涉及网络调用，不产生 JVQuant 费用。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(_SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(_SKILL_ROOT))

import ashare_data.fetchers.broker_account as ba


def _make_account_data(
    hold_count: int = 2,
    order_count: int = 3,
    total: str = "168746.73",
) -> dict:
    """构造模拟的 fetch_broker_account 返回值。"""
    return {
        "total": total,
        "usable": "50000.00",
        "day_earn": "-1234.56",
        "hold_earn": "2345.67",
        "hold_list": [
            {"code": f"00000{i}", "name": f"测试股票{i}", "qty": 100 * (i + 1)}
            for i in range(hold_count)
        ],
        "order_list": [
            {
                "code": f"00000{i}",
                "name": f"测试股票{i}",
                "direction": "buy" if i % 2 == 0 else "sell",
                "price": f"{10.0 + i:.2f}",
                "qty": 100,
            }
            for i in range(order_count)
        ],
        "fetched_at": "2026-02-24T15:30:00+08:00",
        "ticket_reused": True,
    }


class PersistenceTest(unittest.TestCase):
    """测试持久化写入和读取。"""

    def test_persist_creates_files(self) -> None:
        """_persist_account_data 应创建 positions 和 orders 的 JSON 文件。"""
        data = _make_account_data()

        with tempfile.TemporaryDirectory() as tmp:
            pos_dir = str(Path(tmp) / "positions")
            ord_dir = str(Path(tmp) / "orders")

            with (
                mock.patch.object(ba, "_POSITIONS_DIR", pos_dir),
                mock.patch.object(ba, "_ORDERS_DIR", ord_dir),
                mock.patch.object(ba, "_today_str", return_value="2026-02-24"),
            ):
                ba._persist_account_data(data)

            # 验证文件存在
            pos_file = Path(pos_dir) / "2026-02-24.json"
            ord_file = Path(ord_dir) / "2026-02-24.json"
            self.assertTrue(pos_file.exists(), "持仓文件应存在")
            self.assertTrue(ord_file.exists(), "委托文件应存在")

            # 验证持仓内容
            pos = json.loads(pos_file.read_text(encoding="utf-8"))
            self.assertEqual(pos["date"], "2026-02-24")
            self.assertEqual(pos["total"], "168746.73")
            self.assertEqual(len(pos["hold_list"]), 2)

            # 验证委托内容
            orders = json.loads(ord_file.read_text(encoding="utf-8"))
            self.assertEqual(orders["date"], "2026-02-24")
            self.assertEqual(len(orders["order_list"]), 3)

    def test_persist_no_orders_skips_order_file(self) -> None:
        """无委托记录时不应创建 orders 文件。"""
        data = _make_account_data(order_count=0)

        with tempfile.TemporaryDirectory() as tmp:
            pos_dir = str(Path(tmp) / "positions")
            ord_dir = str(Path(tmp) / "orders")

            with (
                mock.patch.object(ba, "_POSITIONS_DIR", pos_dir),
                mock.patch.object(ba, "_ORDERS_DIR", ord_dir),
                mock.patch.object(ba, "_today_str", return_value="2026-02-24"),
            ):
                ba._persist_account_data(data)

            pos_file = Path(pos_dir) / "2026-02-24.json"
            ord_file = Path(ord_dir) / "2026-02-24.json"
            self.assertTrue(pos_file.exists(), "持仓文件应存在")
            self.assertFalse(ord_file.exists(), "无委托时不应创建 orders 文件")

    def test_idempotent_overwrite(self) -> None:
        """同一天重复调用应覆盖写入，内容为最新值。"""
        with tempfile.TemporaryDirectory() as tmp:
            pos_dir = str(Path(tmp) / "positions")
            ord_dir = str(Path(tmp) / "orders")

            with (
                mock.patch.object(ba, "_POSITIONS_DIR", pos_dir),
                mock.patch.object(ba, "_ORDERS_DIR", ord_dir),
                mock.patch.object(ba, "_today_str", return_value="2026-02-24"),
            ):
                # 第一次写入
                data1 = _make_account_data(total="100000.00")
                ba._persist_account_data(data1)

                # 第二次写入不同数据
                data2 = _make_account_data(total="200000.00")
                ba._persist_account_data(data2)

            # 读取结果应是第二次的值
            pos = json.loads(
                (Path(pos_dir) / "2026-02-24.json").read_text(encoding="utf-8")
            )
            self.assertEqual(pos["total"], "200000.00")


class LoadHistoryTest(unittest.TestCase):
    """测试 load_history 读取。"""

    def test_load_empty(self) -> None:
        """无数据时应返回空结果。"""
        with tempfile.TemporaryDirectory() as tmp:
            pos_dir = str(Path(tmp) / "positions")
            ord_dir = str(Path(tmp) / "orders")

            with (
                mock.patch.object(ba, "_POSITIONS_DIR", pos_dir),
                mock.patch.object(ba, "_ORDERS_DIR", ord_dir),
            ):
                result = ba.load_history(days=7)

            self.assertEqual(result["positions"], {})
            self.assertEqual(result["orders"], {})
            self.assertEqual(result["available_days"], 0)
            self.assertEqual(result["date_range"], [])

    def test_load_after_persist(self) -> None:
        """持久化后 load_history 应正确读回数据。"""
        with tempfile.TemporaryDirectory() as tmp:
            pos_dir = str(Path(tmp) / "positions")
            ord_dir = str(Path(tmp) / "orders")

            with (
                mock.patch.object(ba, "_POSITIONS_DIR", pos_dir),
                mock.patch.object(ba, "_ORDERS_DIR", ord_dir),
                mock.patch.object(ba, "_today_str", return_value="2026-02-24"),
            ):
                data = _make_account_data()
                ba._persist_account_data(data)

            # load_history 需要 _today_str 来计算日期范围
            # 但它使用 datetime.now，我们 mock _POSITIONS_DIR/_ORDERS_DIR 即可
            with (
                mock.patch.object(ba, "_POSITIONS_DIR", pos_dir),
                mock.patch.object(ba, "_ORDERS_DIR", ord_dir),
                mock.patch(
                    "ashare_data.fetchers.broker_account.datetime",
                    wraps=ba.datetime,
                ) as mock_dt,
            ):
                # mock datetime.now 返回 2026-02-24
                from datetime import datetime, timezone, timedelta

                cn_tz = timezone(timedelta(hours=8))
                fake_now = datetime(2026, 2, 24, 16, 0, 0, tzinfo=cn_tz)
                mock_dt.now.return_value = fake_now

                result = ba.load_history(days=7)

            self.assertEqual(result["available_days"], 1)
            self.assertIn("2026-02-24", result["positions"])
            self.assertIn("2026-02-24", result["orders"])
            self.assertEqual(result["date_range"], ["2026-02-24", "2026-02-24"])

            # 验证读回的数据内容正确
            pos = result["positions"]["2026-02-24"]
            self.assertEqual(pos["total"], "168746.73")
            self.assertEqual(len(pos["hold_list"]), 2)

    def test_load_multiple_days(self) -> None:
        """多天数据应正确读取和排序。"""
        with tempfile.TemporaryDirectory() as tmp:
            pos_dir = str(Path(tmp) / "positions")
            ord_dir = str(Path(tmp) / "orders")

            dates = ["2026-02-20", "2026-02-21", "2026-02-24"]

            with (
                mock.patch.object(ba, "_POSITIONS_DIR", pos_dir),
                mock.patch.object(ba, "_ORDERS_DIR", ord_dir),
            ):
                for d in dates:
                    with mock.patch.object(ba, "_today_str", return_value=d):
                        data = _make_account_data(total=f"10000{dates.index(d)}.00")
                        ba._persist_account_data(data)

            with (
                mock.patch.object(ba, "_POSITIONS_DIR", pos_dir),
                mock.patch.object(ba, "_ORDERS_DIR", ord_dir),
                mock.patch(
                    "ashare_data.fetchers.broker_account.datetime",
                    wraps=ba.datetime,
                ) as mock_dt,
            ):
                from datetime import datetime, timezone, timedelta

                cn_tz = timezone(timedelta(hours=8))
                fake_now = datetime(2026, 2, 24, 16, 0, 0, tzinfo=cn_tz)
                mock_dt.now.return_value = fake_now

                result = ba.load_history(days=7)

            self.assertEqual(result["available_days"], 3)
            self.assertEqual(result["date_range"], ["2026-02-20", "2026-02-24"])
            self.assertEqual(result["positions"]["2026-02-20"]["total"], "100000.00")
            self.assertEqual(result["positions"]["2026-02-24"]["total"], "100002.00")


class PostMarketCacheTest(unittest.TestCase):
    """测试盘后缓存短路逻辑。"""

    def _write_positions(self, pos_dir: str, date_str: str, fetched_at: str) -> None:
        Path(pos_dir).mkdir(parents=True, exist_ok=True)
        data = {
            "date": date_str,
            "fetched_at": fetched_at,
            "total": "163912.25",
            "usable": "26666.25",
            "day_earn": "-3052.73",
            "hold_earn": "1037.34",
            "hold_list": [{"code": "002202", "name": "金风科技", "hold_vol": "1600"}],
        }
        (Path(pos_dir) / f"{date_str}.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )

    def _write_orders(self, ord_dir: str, date_str: str, count: int) -> None:
        Path(ord_dir).mkdir(parents=True, exist_ok=True)
        data = {
            "date": date_str,
            "fetched_at": f"{date_str}T22:10:16+08:00",
            "order_list": [
                {"code": "002202", "name": "金风科技", "type": "证券买入", "deal_volume": str(100 * (i + 1))}
                for i in range(count)
            ],
        }
        (Path(ord_dir) / f"{date_str}.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )

    def test_post_market_cache_hit_returns_cached_data(self) -> None:
        """盘后且持仓缓存存在时，应直接返回缓存，不调用 API。"""
        from datetime import datetime, timezone, timedelta

        cn_tz = timezone(timedelta(hours=8))
        fake_now = datetime(2026, 2, 25, 23, 19, 0, tzinfo=cn_tz)

        with tempfile.TemporaryDirectory() as tmp:
            pos_dir = str(Path(tmp) / "positions")
            ord_dir = str(Path(tmp) / "orders")
            self._write_positions(pos_dir, "2026-02-25", "2026-02-25T22:10:00+08:00")
            self._write_orders(ord_dir, "2026-02-25", 13)

            with (
                mock.patch.object(ba, "_POSITIONS_DIR", pos_dir),
                mock.patch.object(ba, "_ORDERS_DIR", ord_dir),
                mock.patch(
                    "ashare_data.fetchers.broker_account.datetime",
                    wraps=ba.datetime,
                ) as mock_dt,
            ):
                mock_dt.now.return_value = fake_now
                result = ba._load_post_market_cache("2026-02-25")

        self.assertIsNotNone(result)
        self.assertEqual(result["total"], "163912.25")
        self.assertEqual(len(result["order_list"]), 13)
        self.assertTrue(result["ticket_reused"])

    def test_post_market_cache_miss_when_no_positions_file(self) -> None:
        """持仓缓存不存在时，应返回 None（触发 API 调用路径）。"""
        with tempfile.TemporaryDirectory() as tmp:
            pos_dir = str(Path(tmp) / "positions")
            ord_dir = str(Path(tmp) / "orders")

            with (
                mock.patch.object(ba, "_POSITIONS_DIR", pos_dir),
                mock.patch.object(ba, "_ORDERS_DIR", ord_dir),
            ):
                result = ba._load_post_market_cache("2026-02-25")

        self.assertIsNone(result)

    def test_post_market_cache_returns_empty_orders_when_no_orders_file(self) -> None:
        """持仓缓存存在但 orders 文件不存在时，order_list 应为空列表。"""
        with tempfile.TemporaryDirectory() as tmp:
            pos_dir = str(Path(tmp) / "positions")
            ord_dir = str(Path(tmp) / "orders")
            self._write_positions(pos_dir, "2026-02-25", "2026-02-25T22:10:00+08:00")
            # 不写 orders 文件

            with (
                mock.patch.object(ba, "_POSITIONS_DIR", pos_dir),
                mock.patch.object(ba, "_ORDERS_DIR", ord_dir),
            ):
                result = ba._load_post_market_cache("2026-02-25")

        self.assertIsNotNone(result)
        self.assertEqual(result["order_list"], [])


class CostTrackingTest(unittest.TestCase):
    """测试每日费用追踪和预算控制。"""

    def test_record_cost_creates_file(self) -> None:
        """_record_cost 应创建费用文件并记录调用。"""
        with tempfile.TemporaryDirectory() as tmp:
            costs_dir = str(Path(tmp) / "costs")
            with (
                mock.patch.object(ba, "_COSTS_DIR", costs_dir),
                mock.patch.object(ba, "_today_str", return_value="2026-02-24"),
                mock.patch(
                    "ashare_data.fetchers.broker_account.datetime",
                    wraps=ba.datetime,
                ) as mock_dt,
            ):
                from datetime import datetime, timezone, timedelta

                cn_tz = timezone(timedelta(hours=8))
                mock_dt.now.return_value = datetime(
                    2026, 2, 24, 10, 30, 0, tzinfo=cn_tz
                )

                total = ba._record_cost("login", 0.5)

            self.assertEqual(total, 0.5)

            cost_file = Path(costs_dir) / "2026-02-24.json"
            self.assertTrue(cost_file.exists())

            record = json.loads(cost_file.read_text(encoding="utf-8"))
            self.assertEqual(record["total_cost"], 0.5)
            self.assertEqual(len(record["calls"]), 1)
            self.assertEqual(record["calls"][0]["api"], "login")
            self.assertEqual(record["calls"][0]["cost"], 0.5)

    def test_record_cost_accumulates(self) -> None:
        """多次调用 _record_cost 应累加费用。"""
        with tempfile.TemporaryDirectory() as tmp:
            costs_dir = str(Path(tmp) / "costs")
            with (
                mock.patch.object(ba, "_COSTS_DIR", costs_dir),
                mock.patch.object(ba, "_today_str", return_value="2026-02-24"),
                mock.patch(
                    "ashare_data.fetchers.broker_account.datetime",
                    wraps=ba.datetime,
                ) as mock_dt,
            ):
                from datetime import datetime, timezone, timedelta

                cn_tz = timezone(timedelta(hours=8))
                mock_dt.now.return_value = datetime(
                    2026, 2, 24, 10, 30, 0, tzinfo=cn_tz
                )

                ba._record_cost("login", 0.5)
                ba._record_cost("login", 0.5)
                total = ba._record_cost("login", 0.5)

            self.assertEqual(total, 1.5)

    def test_check_daily_budget_passes_under_limit(self) -> None:
        """费用未超限时 _check_daily_budget 不应抛异常。"""
        with tempfile.TemporaryDirectory() as tmp:
            costs_dir = str(Path(tmp) / "costs")
            with (
                mock.patch.object(ba, "_COSTS_DIR", costs_dir),
                mock.patch.object(ba, "_today_str", return_value="2026-02-24"),
            ):
                # 无费用记录时应通过
                ba._check_daily_budget()

    def test_check_daily_budget_blocks_over_limit(self) -> None:
        """费用超限时 _check_daily_budget 应抛出 RuntimeError。"""
        with tempfile.TemporaryDirectory() as tmp:
            costs_dir = str(Path(tmp) / "costs")

            # 写入一个已超限的费用记录
            import os

            os.makedirs(costs_dir, exist_ok=True)
            cost_file = Path(costs_dir) / "2026-02-24.json"
            cost_file.write_text(
                json.dumps({"date": "2026-02-24", "total_cost": 5.5, "calls": []}),
                encoding="utf-8",
            )

            with (
                mock.patch.object(ba, "_COSTS_DIR", costs_dir),
                mock.patch.object(ba, "_today_str", return_value="2026-02-24"),
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    ba._check_daily_budget()
                self.assertIn("5.50", str(ctx.exception))
                self.assertIn("预算", str(ctx.exception))

    def test_get_daily_cost_summary(self) -> None:
        """get_daily_cost_summary 应返回正确的摘要。"""
        with tempfile.TemporaryDirectory() as tmp:
            costs_dir = str(Path(tmp) / "costs")

            import os

            os.makedirs(costs_dir, exist_ok=True)
            cost_file = Path(costs_dir) / "2026-02-24.json"
            cost_file.write_text(
                json.dumps(
                    {
                        "date": "2026-02-24",
                        "total_cost": 2.0,
                        "calls": [
                            {"api": "login", "cost": 0.5, "time": "10:00:00"},
                            {"api": "login", "cost": 0.5, "time": "12:30:00"},
                            {"api": "login", "cost": 0.5, "time": "14:00:00"},
                            {"api": "login", "cost": 0.5, "time": "15:00:00"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.object(ba, "_COSTS_DIR", costs_dir),
                mock.patch.object(ba, "_today_str", return_value="2026-02-24"),
            ):
                summary = ba.get_daily_cost_summary()

            self.assertEqual(summary["total_cost"], 2.0)
            self.assertEqual(summary["call_count"], 4)
            self.assertEqual(summary["budget"], 5.0)
            self.assertEqual(summary["remaining"], 3.0)

    def test_login_records_cost(self) -> None:
        """_login 成功后应自动记录费用。"""
        with tempfile.TemporaryDirectory() as tmp:
            costs_dir = str(Path(tmp) / "costs")
            ticket_cache_path = str(Path(tmp) / ".jvquant_ticket_cache.json")

            fake_response = json.dumps(
                {"code": "0", "ticket": "test_ticket", "expire": "9000"}
            ).encode()

            with (
                mock.patch.object(ba, "_COSTS_DIR", costs_dir),
                mock.patch.object(ba, "_today_str", return_value="2026-02-24"),
                mock.patch.object(ba, "_CACHE_DIR", tmp),
                mock.patch.object(ba, "_TICKET_CACHE_PATH", ticket_cache_path),
                mock.patch(
                    "ashare_data.fetchers.broker_account.datetime",
                    wraps=ba.datetime,
                ) as mock_dt,
                mock.patch.object(ba._NO_PROXY_OPENER, "open") as mock_open,
            ):
                from datetime import datetime, timezone, timedelta

                cn_tz = timezone(timedelta(hours=8))
                mock_dt.now.return_value = datetime(
                    2026, 2, 24, 10, 30, 0, tzinfo=cn_tz
                )

                mock_resp = mock.MagicMock()
                mock_resp.read.return_value = fake_response
                mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
                mock_resp.__exit__ = mock.MagicMock(return_value=False)
                mock_open.return_value = mock_resp

                cfg = {"token": "t", "acc": "a", "pass": "p"}
                ticket = ba._login(cfg, "http://fake:1234")

            self.assertEqual(ticket, "test_ticket")

            cost_file = Path(costs_dir) / "2026-02-24.json"
            self.assertTrue(cost_file.exists())
            record = json.loads(cost_file.read_text(encoding="utf-8"))
            self.assertEqual(record["total_cost"], 0.5)

    def test_login_blocked_when_over_budget(self) -> None:
        """费用超限时 _login 应拒绝调用。"""
        with tempfile.TemporaryDirectory() as tmp:
            costs_dir = str(Path(tmp) / "costs")

            import os

            os.makedirs(costs_dir, exist_ok=True)
            cost_file = Path(costs_dir) / "2026-02-24.json"
            cost_file.write_text(
                json.dumps({"date": "2026-02-24", "total_cost": 5.0, "calls": []}),
                encoding="utf-8",
            )

            with (
                mock.patch.object(ba, "_COSTS_DIR", costs_dir),
                mock.patch.object(ba, "_today_str", return_value="2026-02-24"),
            ):
                cfg = {"token": "t", "acc": "a", "pass": "p"}
                with self.assertRaises(RuntimeError) as ctx:
                    ba._login(cfg, "http://fake:1234")
                self.assertIn("预算", str(ctx.exception))


class TicketBufferTest(unittest.TestCase):
    """测试 ticket 过期 buffer（5 分钟）。"""

    def test_ticket_valid_well_before_expiry(self) -> None:
        """ticket 距过期还有 10 分钟时应复用。"""
        import time

        cache = {"ticket": "cached_ticket", "expire_at": time.time() + 600}

        with mock.patch.object(ba, "_load_ticket_cache", return_value=cache):
            ticket = ba._get_valid_ticket(
                {"token": "t", "acc": "a", "pass": "p"}, "http://fake"
            )
        self.assertEqual(ticket, "cached_ticket")

    def test_ticket_within_buffer_triggers_relogin(self) -> None:
        """ticket 距过期不足 5 分钟时应重新登录。"""
        import time

        # 距过期只剩 3 分钟（小于 5 分钟 buffer）
        cache = {"ticket": "old_ticket", "expire_at": time.time() + 180}

        fake_response = json.dumps(
            {"code": "0", "ticket": "new_ticket", "expire": "9000"}
        ).encode()

        with tempfile.TemporaryDirectory() as tmp:
            costs_dir = str(Path(tmp) / "costs")
            ticket_cache_path = str(Path(tmp) / ".jvquant_ticket_cache.json")
            with (
                mock.patch.object(ba, "_load_ticket_cache", return_value=cache),
                mock.patch.object(ba, "_COSTS_DIR", costs_dir),
                mock.patch.object(ba, "_today_str", return_value="2026-02-24"),
                mock.patch.object(ba, "_CACHE_DIR", tmp),
                mock.patch.object(ba, "_TICKET_CACHE_PATH", ticket_cache_path),
                mock.patch(
                    "ashare_data.fetchers.broker_account.datetime",
                    wraps=ba.datetime,
                ) as mock_dt,
                mock.patch.object(ba._NO_PROXY_OPENER, "open") as mock_open,
            ):
                from datetime import datetime, timezone, timedelta

                cn_tz = timezone(timedelta(hours=8))
                mock_dt.now.return_value = datetime(
                    2026, 2, 24, 10, 30, 0, tzinfo=cn_tz
                )

                mock_resp = mock.MagicMock()
                mock_resp.read.return_value = fake_response
                mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
                mock_resp.__exit__ = mock.MagicMock(return_value=False)
                mock_open.return_value = mock_resp

                ticket = ba._get_valid_ticket(
                    {"token": "t", "acc": "a", "pass": "p"}, "http://fake"
                )

            self.assertEqual(ticket, "new_ticket")


if __name__ == "__main__":
    unittest.main()
