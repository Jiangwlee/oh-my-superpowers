#!/usr/bin/env python3
"""CDP 调试入口。

用途：
  1. 验证 Chrome 9222 / CDP 连通性
  2. 在真实浏览器上下文里抓取受保护接口
  3. 为 403/反爬问题提供手工排障入口

示例：
    ashare-cdp-debug ths-indexflash
    ashare-cdp-debug fetch-json --page-url https://q.10jqka.com.cn/ --url /api.php?t=indexflash
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from ashare_data.cdp import CdpClient
from ashare_data.fetchers.ths_cdp import fetch_indexflash_via_cdp

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CDP 调试入口")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ths-indexflash", help="在浏览器上下文抓取同花顺 indexflash")

    fetch_json = subparsers.add_parser("fetch-json", help="在浏览器上下文发起任意 JSON 请求")
    fetch_json.add_argument("--page-url", required=True, help="先打开的页面 URL")
    fetch_json.add_argument("--url", required=True, help="页内 fetch 的目标 URL，可为相对路径")
    fetch_json.add_argument(
        "--headers",
        default="{}",
        help='附加请求头 JSON，例如 \'{"Accept":"*/*"}\'',
    )
    return parser


def _dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "ths-indexflash":
        return fetch_indexflash_via_cdp()

    if args.command == "fetch-json":
        headers = json.loads(args.headers)
        if not isinstance(headers, dict):
            raise ValueError("--headers 必须是 JSON object")
        client = CdpClient()
        session = client.open_page(args.page_url)
        try:
            session.wait_for_network_idle(1.5)
            return session.fetch_json(args.url, headers={str(k): str(v) for k, v in headers.items()})
        finally:
            session.close()

    raise ValueError(f"Unsupported command: {args.command}")


def main() -> None:
    """Run the CDP debug CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [ashare-cdp-debug] %(message)s",
        datefmt="%H:%M:%S",
    )

    result = _dispatch(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
