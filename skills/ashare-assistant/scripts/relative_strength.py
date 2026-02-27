#!/usr/bin/env python3
"""个股 vs 大盘相对强弱工具。

用法:
    python -m scripts.relative_strength --code 000338 --date 20260226
    python -m scripts.relative_strength --code 000338  # 默认今天
    python -m scripts.relative_strength --code 000338 --benchmark 399001  # 深证成指

输出: JSON 到 stdout，含5个时间节点（10:00/11:00/13:30/14:30/15:00）的对比
"""

import argparse
import json
import logging
import sys

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="计算个股 vs 大盘相对强弱（全天5个节点）")
    parser.add_argument("--code", required=True, help="6位股票代码")
    parser.add_argument("--date", default=None, help="日期 YYYYMMDD 或 YYYY-MM-DD，默认今天")
    parser.add_argument("--benchmark", default="000001", help="基准指数代码，默认 000001（上证综指）")
    args = parser.parse_args()

    try:
        from ashare_data.fetchers.intraday_analysis import get_relative_strength
        result = get_relative_strength(args.code, args.date, args.benchmark)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        logger.exception("relative_strength 失败: %s", exc)
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
