#!/usr/bin/env python3
"""操作时刻行情现场还原工具。

用法:
    python scripts/trade_context.py --code 603163 --date 20260226 --time 093047 --price 128.73
    python scripts/trade_context.py --code 603163 --time 093047  # 默认今天，不传价格

参数:
    --code:   6位股票代码
    --date:   日期 YYYYMMDD 或 YYYY-MM-DD，默认今天
    --time:   操作时间 HHMMSS（来自 broker_account.json order_list.time 字段）
    --price:  成交价格（来自 deal_price 字段），默认0（自动取K线收盘价）
    --window: 前后各取多少分钟，默认30

输出: JSON 到 stdout
"""

import argparse
import json
import os
import sys

_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PKG_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(_SKILL_ROOT)), "packages", "ashare-data"
)
for _p in (_SKILL_ROOT, _PKG_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def main() -> None:
    parser = argparse.ArgumentParser(description="还原操作时刻前后30分钟行情现场")
    parser.add_argument("--code", required=True, help="6位股票代码")
    parser.add_argument("--date", default=None, help="日期 YYYYMMDD 或 YYYY-MM-DD，默认今天")
    parser.add_argument("--time", required=True, help="操作时间 HHMMSS，如 093047")
    parser.add_argument("--price", type=float, default=0.0, help="成交价格，默认0")
    parser.add_argument("--window", type=int, default=30, help="前后各取分钟数，默认30")
    args = parser.parse_args()

    from ashare_data.fetchers.intraday_analysis import get_trade_context

    result = get_trade_context(
        code=args.code,
        date=args.date,
        trade_time=args.time,
        trade_price=args.price,
        window_minutes=args.window,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
