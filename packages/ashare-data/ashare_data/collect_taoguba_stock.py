#!/usr/bin/env python3
"""采集淘股吧个股扩展数据（题材标签 + 个股讨论 + 综合推荐）。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_ROOT = os.path.dirname(_SCRIPTS_DIR)
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from ashare_data.fetchers.taoguba import (  # noqa: E402
    fetch_taoguba_quotes_posts,
    fetch_taoguba_stock_tags,
    fetch_taoguba_zh_recommend,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="采集淘股吧个股扩展数据")
    parser.add_argument("--full-code", required=True, help="完整代码，如 sz002050")
    parser.add_argument("--output", required=True, help="输出 JSON 路径")
    parser.add_argument("--quotes-count", type=int, default=20, help="个股讨论贴条数")
    parser.add_argument("--zh-page", type=int, default=1, help="综合推荐页码")
    parser.add_argument("--zh-count", type=int, default=20, help="综合推荐条数")
    args = parser.parse_args()

    tags = fetch_taoguba_stock_tags(args.full_code)
    quotes_posts = fetch_taoguba_quotes_posts(args.full_code, count=args.quotes_count)
    zh_recommend = fetch_taoguba_zh_recommend(page_no=args.zh_page, count=args.zh_count)

    payload = {
        "full_code": args.full_code,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stock_tags": tags,
        "quotes_posts": quotes_posts,
        "zh_recommend": zh_recommend,
        "summary": {
            "stock_tags": len(tags),
            "quotes_posts": len(quotes_posts),
            "zh_recommend": len(zh_recommend),
        },
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(json.dumps(payload["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
