"""统一 HTTP 客户端（标准库实现）。"""

from __future__ import annotations

import contextlib
import http.client
import json
import logging
import os
import time
import unittest.mock
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)
_DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/147.0"

# 不经过任何代理的专用 opener。
# urllib 默认 opener 会读取 http_proxy / https_proxy 等系统环境变量，
# 导致访问东财、淘股吧等国内接口时因调用方设置的代理出错。
# 使用空 ProxyHandler({}) 明确禁用代理，确保直连。
_NO_PROXY_OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
)

# 代理相关环境变量列表（大小写均可能出现）。
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


@contextlib.contextmanager
def no_proxy_env():
    """临时禁用代理，使 requests 等第三方库直连网络。

    同时清除进程代理环境变量并 patch ``requests.utils.getproxies`` 返回空字典，
    彻底阻断两条代理检测路径：

    1. ``os.environ`` 中的 http_proxy / https_proxy 等变量
    2. macOS 系统代理（通过 ``getproxies_macosx_sysconf()`` 检测），
       requests 在 env vars 为空时会 fallback 读取系统代理，
       patch 后同样返回 ``{}`` 使其直连。

    退出上下文后自动恢复原始环境变量和原始函数。

    用法::

        from ashare_data.core.http_client import no_proxy_env

        with no_proxy_env():
            resp = requests.get("https://example.com")
    """
    saved: dict[str, str] = {}
    for key in _PROXY_ENV_VARS:
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    try:
        import requests.utils as _requests_utils  # type: ignore[import]

        patch_target = _requests_utils
        attr_name = "getproxies"
    except ImportError:
        patch_target = None
        attr_name = ""

    if patch_target is not None:
        with unittest.mock.patch.object(patch_target, attr_name, return_value={}):
            try:
                yield
            finally:
                os.environ.update(saved)
    else:
        try:
            yield
        finally:
            os.environ.update(saved)


def http_text(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | list[Any] | str | bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 20.0,  # 增加超时时间
    retries: int = 5,  # 增加重试次数
    sleep_sec: float = 1.0,  # 增加初始延迟
) -> str:
    """发送 HTTP 请求并返回文本。"""
    method_upper = method.upper()
    merged_headers: dict[str, str] = {"User-Agent": _DEFAULT_UA}
    if headers:
        merged_headers.update(headers)
    if method_upper in ("POST", "PUT", "PATCH") and payload is not None:
        merged_headers.setdefault("Content-Type", "application/json")

    data: bytes | None = None
    if payload is not None and method_upper in ("GET", "HEAD"):
        raise ValueError(f"{method_upper} 请求不支持 payload，请使用 query string")
    if payload is not None:
        if isinstance(payload, bytes):
            data = payload
        elif isinstance(payload, str):
            data = payload.encode("utf-8")
        else:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    last_exc: Exception | None = None
    wait = sleep_sec
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers=merged_headers,
                method=method_upper,
            )
            with _NO_PROXY_OPENER.open(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except http.client.IncompleteRead as exc:
            last_exc = exc
            if attempt < retries:
                logger.warning(
                    "http_text incomplete read %s/%s %s, will retry",
                    attempt,
                    retries,
                    url,
                )
                time.sleep(wait)
                wait *= 2
            else:
                partial = exc.partial or b""
                logger.warning(
                    "http_text incomplete read after %s retries for %s, returning partial body",
                    retries,
                    url,
                )
                return partial.decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            last_exc = exc
            if attempt < retries:
                logger.warning(
                    "http_text retry %s/%s %s failed: %s",
                    attempt,
                    retries,
                    url,
                    exc,
                )
                time.sleep(wait)
                wait *= 2
    logger.error("http_text failed after %s retries: %s", retries, url)
    raise RuntimeError(f"http_text 请求失败（重试 {retries} 次）: {url} — {last_exc}")


def http_bytes(
    url: str,
    method: str = "GET",
    payload: bytes | str | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    retries: int = 3,
    sleep_sec: float = 0.8,
) -> bytes:
    """发送 HTTP 请求并返回原始字节（用于 gzip/二进制响应）。"""
    method_upper = method.upper()
    if payload is not None and method_upper in ("GET", "HEAD"):
        raise ValueError(f"{method_upper} 请求不支持 payload，请使用 query string")

    data: bytes | None = None
    if isinstance(payload, bytes):
        data = payload
    elif isinstance(payload, str):
        data = payload.encode("utf-8")

    merged_headers: dict[str, str] = {"User-Agent": _DEFAULT_UA}
    if headers:
        merged_headers.update(headers)

    last_exc: Exception | None = None
    wait = sleep_sec
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers=merged_headers,
                method=method_upper,
            )
            with _NO_PROXY_OPENER.open(req, timeout=timeout) as resp:
                return resp.read()
        except http.client.IncompleteRead as exc:
            last_exc = exc
            if attempt < retries:
                logger.warning(
                    "http_bytes incomplete read %s/%s %s, will retry",
                    attempt,
                    retries,
                    url,
                )
                time.sleep(wait)
                wait *= 2
            else:
                logger.warning(
                    "http_bytes incomplete read after %s retries for %s, returning partial body",
                    retries,
                    url,
                )
                return exc.partial or b""
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            last_exc = exc
            if attempt < retries:
                logger.warning(
                    "http_bytes retry %s/%s %s failed: %s",
                    attempt,
                    retries,
                    url,
                    exc,
                )
                time.sleep(wait)
                wait *= 2
    logger.error("http_bytes failed after %s retries: %s", retries, url)
    raise RuntimeError(f"http_bytes 请求失败（重试 {retries} 次）: {url} — {last_exc}")


def http_json(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | list[Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    retries: int = 3,
    sleep_sec: float = 0.8,
) -> dict[str, Any]:
    """发送 HTTP 请求并返回 JSON dict。"""
    body = http_text(
        url=url,
        method=method,
        payload=payload,
        headers=headers,
        timeout=timeout,
        retries=retries,
        sleep_sec=sleep_sec,
    )
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"http_json 响应解析失败: {url} — {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"http_json 响应不是 JSON object: {url}")
    return data
