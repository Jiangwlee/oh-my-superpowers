#!/usr/bin/env python3
"""采集东方财富股吧（帖子/资讯/公告）用于候选股 deep research。"""

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

from ashare_data.fetchers.eastmoney_guba import (  # noqa: E402
    fetch_latest_posts,
    fetch_post_detail,
    fetch_stock_info_list,
    fetch_stock_notice_list,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="采集东方财富股吧数据")
    parser.add_argument("--code", required=True, help="股票代码，如 002050")
    parser.add_argument("--output", required=True, help="输出 JSON 路径")
    parser.add_argument("--post-limit", type=int, default=36, help="最新帖子抓取条数")
    parser.add_argument("--detail-limit", type=int, default=10, help="抓取正文详情条数")
    parser.add_argument("--notice-days", type=int, default=3, help="公告近N天过滤")
    args = parser.parse_args()

    posts = fetch_latest_posts(args.code, limit=args.post_limit)
    infos = fetch_stock_info_list(args.code)
    notices = fetch_stock_notice_list(args.code, recent_days=args.notice_days)

    detail_posts = []
    for item in posts[: max(0, args.detail_limit)]:
        post_id = item.get("post_id")
        if not post_id:
            continue
        try:
            detail_posts.append(fetch_post_detail(args.code, str(post_id)))
        except Exception as exc:
            detail_posts.append(
                {
                    "post_id": str(post_id),
                    "error": str(exc),
                    "url": item.get("url"),
                }
            )

    payload = {
        "code": args.code,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latest_posts": posts,
        "latest_post_details": detail_posts,
        "stock_infos": infos,
        "stock_notices_recent": notices,
        "summary": {
            "latest_posts": len(posts),
            "latest_post_details": len(detail_posts),
            "stock_infos": len(infos),
            "stock_notices_recent": len(notices),
        },
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(json.dumps(payload["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
