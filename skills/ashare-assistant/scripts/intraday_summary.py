#!/usr/bin/env python3
"""日内行情摘要工具（30分钟聚合）。

用法:
    python -m scripts.intraday_summary --code 000338 --date 20260226
    python -m scripts.intraday_summary --code 000338  # 默认今天

输出: JSON 到 stdout
"""

import argparse
import json
import logging
import sys

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="获取个股全天日内行情摘要（30分钟聚合）")
    parser.add_argument("--code", required=True, help="6位股票代码，如 000338")
    parser.add_argument("--date", default=None, help="日期 YYYYMMDD 或 YYYY-MM-DD，默认今天")
    args = parser.parse_args()

    try:
        from ashare_data.fetchers.intraday_analysis import get_intraday_summary
        result = get_intraday_summary(args.code, args.date)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        logger.exception("intraday_summary 失败: %s", exc)
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
