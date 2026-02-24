"""统一 HTTP 客户端（标准库实现）。"""

from __future__ import annotations

import http.client
import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "Gecko/20100101 Firefox/147.0"
)


def http_text(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | list[Any] | str | bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    retries: int = 3,
    sleep_sec: float = 0.8,
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
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except http.client.IncompleteRead as exc:
            partial = exc.partial or b""
            logger.warning("http_text incomplete read for %s, returning partial body", url)
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
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except http.client.IncompleteRead as exc:
            logger.warning("http_bytes incomplete read for %s, returning partial body", url)
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
