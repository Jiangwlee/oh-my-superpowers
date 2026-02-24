"""统一 HTTP 客户端（标准库实现）。"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "Gecko/20100101 Firefox/147.0"
)


def http_text(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | list[Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    retries: int = 3,
    sleep_sec: float = 0.8,
) -> str:
    """发送 HTTP 请求并返回文本。"""
    merged_headers: dict[str, str] = {"User-Agent": _DEFAULT_UA}
    if headers:
        merged_headers.update(headers)
    if method.upper() in ("POST", "PUT", "PATCH") and payload is not None:
        merged_headers.setdefault("Content-Type", "application/json")

    data: bytes | None = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    last_exc: Exception | None = None
    wait = sleep_sec
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers=merged_headers,
                method=method.upper(),
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(wait)
                wait *= 2
    raise RuntimeError(f"http_text 请求失败（重试 {retries} 次）: {url} — {last_exc}")


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

