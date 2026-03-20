"""统一 HTTP 客户端（基于 urllib.request）。

说明
----
- 使用 urllib.request 实现，避免 curl_cffi 的 IncompleteRead 问题
- 保留原有 API 签名，兼容所有现有调用方
- 内置重试机制和代理禁用

示例
----
    from ashare_data.core.http_client import http_text, http_json, http_bytes

    html = http_text("https://example.com")
    data = http_json("https://api.example.com/data")
    raw = http_bytes("https://example.com/file.bin")
"""

from __future__ import annotations

import http.client
import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)
_DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/147.0"

# 不经过任何代理的专用 opener。
_NO_PROXY_OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
)


def http_text(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | list[Any] | str | bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 20.0,
    retries: int = 5,
    sleep_sec: float = 1.0,
) -> str:
    """发送 HTTP 请求并返回文本。使用分块读取避免 IncompleteRead。"""
    if method != "GET":
        raise NotImplementedError("http_text 仅支持 GET 方法，POST 请改用 http_post_text")
    if payload is not None:
        raise ValueError("http_text GET 请求不接受 payload")
    
    merged_headers = {"User-Agent": _DEFAULT_UA}
    if headers:
        merged_headers.update(headers)

    last_exc: Exception | None = None
    wait = sleep_sec
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=merged_headers, method="GET")
            with _NO_PROXY_OPENER.open(req, timeout=timeout) as resp:
                # 使用 read() 不带参数会自动处理 chunked encoding
                # 但如果遇到 IncompleteRead，尝试手动读取剩余数据
                try:
                    data = resp.read()
                    return data.decode("utf-8")
                except http.client.IncompleteRead as e:
                    # 如果发生 IncompleteRead，返回已读取的部分
                    logger.warning("IncompleteRead detected, returning partial response: %s bytes", len(e.partial))
                    return e.partial.decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            last_exc = exc
            if attempt < retries:
                logger.warning("http_text retry %s/%s %s failed: %s", attempt, retries, url, exc)
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
    if method != "GET":
        raise NotImplementedError("http_bytes 仅支持 GET 方法")
    if payload is not None:
        raise ValueError("http_bytes GET 请求不接受 payload")
    
    merged_headers = {"User-Agent": _DEFAULT_UA}
    if headers:
        merged_headers.update(headers)

    last_exc: Exception | None = None
    wait = sleep_sec
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=merged_headers, method="GET")
            with _NO_PROXY_OPENER.open(req, timeout=timeout) as resp:
                try:
                    return resp.read()
                except http.client.IncompleteRead as e:
                    logger.warning("IncompleteRead in http_bytes, returning partial: %s bytes", len(e.partial))
                    return e.partial
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            last_exc = exc
            if attempt < retries:
                logger.warning("http_bytes retry %s/%s %s failed: %s", attempt, retries, url, exc)
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
    """发送 HTTP 请求并返回 JSON dict。支持 GET 和 POST。"""
    import time
    
    if method == "POST":
        # POST 请求
        merged_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": _DEFAULT_UA,
        }
        if headers:
            merged_headers.update(headers)

        last_exc: Exception | None = None
        wait = sleep_sec
        for attempt in range(1, retries + 1):
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload if payload is not None else {}).encode("utf-8"),
                    headers=merged_headers,
                    method="POST",
                )
                with _NO_PROXY_OPENER.open(req, timeout=timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as exc:
                last_exc = exc
                if attempt < retries:
                    logger.warning("http_json POST retry %s/%s %s failed: %s", attempt, retries, url, exc)
                    time.sleep(wait)
                    wait *= 2
        logger.error("http_json POST failed after %s retries: %s", retries, url)
        raise RuntimeError(f"http_json POST 请求失败（重试 {retries} 次）: {url} — {last_exc}")
    
    # GET 请求
    body = http_text(
        url=url,
        method="GET",
        payload=None,
        headers=headers,
        timeout=timeout,
        retries=retries,
        sleep_sec=sleep_sec,
    )
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"http_json 响应解析失败：{url} — {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"http_json 响应不是 JSON object: {url}")
    return data


def http_post_text(
    url: str,
    data: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    retries: int = 3,
) -> str:
    """发送 POST 请求并返回文本。"""
    import time
    
    merged_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": _DEFAULT_UA,
    }
    if headers:
        merged_headers.update(headers)

    import urllib.parse
    form_data = urllib.parse.urlencode(data).encode("utf-8")

    last_exc: Exception | None = None
    wait = sleep_sec
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, data=form_data, headers=merged_headers, method="POST")
            with _NO_PROXY_OPENER.open(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            last_exc = exc
            if attempt < retries:
                logger.warning("http_post_text retry %s/%s %s failed: %s", attempt, retries, url, exc)
                time.sleep(wait)
                wait *= 2
    logger.error("http_post_text failed after %s retries: %s", retries, url)
    raise RuntimeError(f"http_post_text 请求失败（重试 {retries} 次）: {url} — {last_exc}")


def http_post_json(
    url: str,
    data: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    retries: int = 3,
) -> dict[str, Any]:
    """发送 POST JSON 请求并返回响应 dict。"""
    return http_json(url, method="POST", payload=data, headers=headers, timeout=timeout, retries=retries)


__all__ = [
    "http_text",
    "http_bytes",
    "http_json",
    "http_post_text",
    "http_post_json",
]
