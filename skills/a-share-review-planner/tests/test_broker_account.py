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

import scripts.fetchers.broker_account as ba


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
                    "scripts.fetchers.broker_account.datetime",
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
                    "scripts.fetchers.broker_account.datetime",
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


if __name__ == "__main__":
    unittest.main()
