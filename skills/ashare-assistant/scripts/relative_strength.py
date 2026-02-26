#!/usr/bin/env python3
"""个股 vs 大盘相对强弱工具。

用法:
    python scripts/relative_strength.py --code 000338 --date 20260226
    python scripts/relative_strength.py --code 000338  # 默认今天
    python scripts/relative_strength.py --code 000338 --benchmark 399001  # 深证成指

输出: JSON 到 stdout，含5个时间节点（10:00/11:00/13:30/14:30/15:00）的对比
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
    parser = argparse.ArgumentParser(description="计算个股 vs 大盘相对强弱（全天5个节点）")
    parser.add_argument("--code", required=True, help="6位股票代码")
    parser.add_argument("--date", default=None, help="日期 YYYYMMDD 或 YYYY-MM-DD，默认今天")
    parser.add_argument("--benchmark", default="000001", help="基准指数代码，默认 000001（上证综指）")
    args = parser.parse_args()

    from ashare_data.fetchers.intraday_analysis import get_relative_strength

    result = get_relative_strength(args.code, args.date, args.benchmark)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
