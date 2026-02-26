#!/usr/bin/env python3
"""开盘背景分析工具（反事实基线：如果在开盘前看，你会如何判断？）。

用法:
    python scripts/opening_context.py --code 000338 --date 20260226
    python scripts/opening_context.py --code 000338  # 默认今天

输出: JSON 到 stdout，含跳空幅度、MA5/MA10/MA20、前5日趋势、开盘30分钟表现
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
    parser = argparse.ArgumentParser(description="获取个股开盘背景（跳空/MA/前日趋势）")
    parser.add_argument("--code", required=True, help="6位股票代码")
    parser.add_argument("--date", default=None, help="日期 YYYYMMDD 或 YYYY-MM-DD，默认今天")
    args = parser.parse_args()

    from ashare_data.fetchers.intraday_analysis import get_opening_context

    result = get_opening_context(args.code, args.date)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
