"""统一 HTTP 爬虫封装（基于 Scrapling）。

说明
----
- 使用 Scrapling Fetcher（curl_cffi 后端），提供 TLS 指纹模拟和自动反爬能力
- 返回 Response 对象，可直接调用 .css()/.xpath()/.re() 提取结构化数据
- 内部使用 FetcherSession 复用连接，避免 IncompleteRead 问题
- 默认 impersonate='chrome'，自动生成真实浏览器 headers

示例
----
    from ashare_data.core.scraper import fetch_page, fetch_text, fetch_json

    # 直接获取页面并解析
    resp = fetch_page('https://example.com')
    titles = resp.css('.title::text').getall()

    # 纯文本模式（兼容旧代码）
    html = fetch_text('https://example.com')

    # JSON API
    data = fetch_json('https://api.example.com/data')
"""

from __future__ import annotations

import json
import logging
import os
import time
import unittest.mock
from typing import Any

from scrapling.fetchers import Fetcher, FetcherSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 全局 Session 单例
# ---------------------------------------------------------------------------

_SESSION: FetcherSession | None = None


def _get_session() -> FetcherSession:
    """获取或创建全局 FetcherSession 单例。"""
    global _SESSION
    if _SESSION is None:
        _SESSION = FetcherSession(
            impersonate="chrome",
            timeout=15,
            retries=3,
            retry_delay=0.8,
            follow_redirects=True,
            max_redirects=30,
            verify=True,
            stealthy_headers=True,
        )
    return _SESSION


def no_proxy_env():
    """临时禁用代理，使请求直连网络。

    同时清除进程代理环境变量并 patch ``requests.utils.getproxies`` 返回空字典，
    彻底阻断两条代理检测路径。

    用法::

        with no_proxy_env():
            resp = requests.get("https://example.com")
    """
    _PROXY_ENV_VARS = (
        "http_proxy",
        "https_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "all_proxy",
        "ALL_PROXY",
        "no_proxy",
        "NO_PROXY",
    )

    saved: dict[str, str] = {}
    for key in _PROXY_ENV_VARS:
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    try:
        try:
            import requests.utils as _requests_utils

            patch_target = _requests_utils
            attr_name = "getproxies"
        except ImportError:
            patch_target = None
            attr_name = ""

        if patch_target is not None:
            with unittest.mock.patch.object(patch_target, attr_name, return_value={}):
                yield
        else:
            yield
    finally:
        os.environ.update(saved)


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

def fetch_page(url: str, **kwargs: Any) -> Any:
    """获取页面 HTML，返回 Scrapling Response 对象（可直接 .css/.xpath）。

    Args:
        url: 目标 URL。
        **kwargs: 传递给 Fetcher.get() 的参数，如 headers/cookies 等。

    Returns:
        Response 对象，继承自 Selector，支持链式调用 .css()/.xpath()/.re() 等。

    Example
    -------
        >>> resp = fetch_page("https://www.tgb.cn/jinghua/1-1")
        >>> titles = resp.css(".title::text").getall()
    """
    from scrapling.fetchers import Fetcher

    merged_headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    if kwargs.get("headers"):
        merged_headers.update(kwargs["headers"])
        del kwargs["headers"]

    kwargs["headers"] = merged_headers

    try:
        # 使用 Fetcher 直接获取并返回 Response
        return Fetcher.get(url, impersonate="chrome", **kwargs)
    except Exception as e:
        logger.exception("fetch_page 请求失败：%s — %s", url, e)
        raise


def parse_html(html_text: str, url: str = "") -> Any:
    """将 HTML 文本解析为 Scrapling Response 对象（无需网络请求）。

    Args:
        html_text: HTML 字符串。
        url: 可选的基准 URL（用于相对路径解析）。

    Returns:
        Response 对象，可直接调用 .css()/.xpath()/.re() 等。
    """
    from scrapling.parser import Selector

    # 直接使用 Selector 解析 HTML，无需网络请求
    return Selector(content=html_text, url=url)


def fetch_text(url: str, **kwargs: Any) -> str:
    """获取页面 HTML 文本（兼容旧 http_client.http_text）。

    Args:
        url: 目标 URL。
        **kwargs: 其他参数。

    Returns:
        页面 HTML 字符串。
    """
    resp = fetch_page(url, **kwargs)
    return resp.text


def fetch_json(url: str, **kwargs: Any) -> dict[str, Any]:
    """获取 JSON 响应，返回 dict。

    Args:
        url: 目标 URL。
        **kwargs: 其他参数。

    Returns:
        JSON 解析后的 dict。
    """
    resp = fetch_page(url, **kwargs)
    try:
        return resp.json()
    except Exception as e:
        raise RuntimeError(f"JSON 解析失败：{url} — {e}") from e


def fetch_bytes(url: str, **kwargs: Any) -> bytes:
    """获取原始字节响应。

    Args:
        url: 目标 URL。
        **kwargs: 其他参数。

    Returns:
        原始字节内容。
    """
    resp = fetch_page(url, **kwargs)
    return resp.body


def fetch_post_json(url: str, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """发送 POST JSON 请求，返回响应 dict。优先使用 urllib（curl_cffi 有重定向问题）。"""
    import urllib.request

    merged_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    if kwargs.get("headers"):
        merged_headers.update(kwargs["headers"])
        del kwargs["headers"]

    # 直接使用 urllib 避免 curl_cffi 的重定向问题
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=merged_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=kwargs.get("timeout", 15)) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.exception("fetch_post_json 请求失败：%s — %s", url, e)
        raise


__all__ = [
    "fetch_page",
    "fetch_text",
    "fetch_json",
    "fetch_bytes",
    "fetch_post_json",
    "no_proxy_env",
]
