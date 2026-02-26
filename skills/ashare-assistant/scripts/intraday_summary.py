#!/usr/bin/env python3
"""日内行情摘要工具（30分钟聚合）。

用法:
    python scripts/intraday_summary.py --code 000338 --date 20260226
    python scripts/intraday_summary.py --code 000338  # 默认今天

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
    parser = argparse.ArgumentParser(description="获取个股全天日内行情摘要（30分钟聚合）")
    parser.add_argument("--code", required=True, help="6位股票代码，如 000338")
    parser.add_argument("--date", default=None, help="日期 YYYYMMDD 或 YYYY-MM-DD，默认今天")
    args = parser.parse_args()

    from ashare_data.fetchers.intraday_analysis import get_intraday_summary

    result = get_intraday_summary(args.code, args.date)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
