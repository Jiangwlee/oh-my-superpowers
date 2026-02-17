"""轻量 HTTP 客户端 — 仅依赖 Python 标准库（urllib + json）。"""

import json
import time
import urllib.request
import urllib.error

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "Gecko/20100101 Firefox/147.0"
)


def http_json(
    url: str,
    method: str = "GET",
    payload: dict | None = None,
    headers: dict | None = None,
    timeout: float = 15.0,
    retries: int = 3,
    sleep_sec: float = 0.8,
) -> dict:
    """发送 HTTP 请求并返回解析后的 JSON dict。

    Parameters
    ----------
    url : str
        请求地址。
    method : str
        HTTP 方法，默认 ``"GET"``。
    payload : dict | None
        请求体（仅 POST/PUT/PATCH 等有效），会自动序列化为 JSON。
    headers : dict | None
        额外请求头，会与默认头合并（调用方优先）。
    timeout : float
        单次请求超时秒数，默认 15。
    retries : int
        最大重试次数（含首次），默认 3。
    sleep_sec : float
        首次重试前等待秒数，后续按指数退避翻倍。

    Returns
    -------
    dict
        解析后的 JSON 响应。

    Raises
    ------
    RuntimeError
        所有重试均失败后抛出，包含最后一次异常信息。
    """
    # --- 构建请求头 ---
    merged_headers: dict[str, str] = {"User-Agent": _DEFAULT_UA}
    if headers:
        merged_headers.update(headers)

    # POST 时自动补 Content-Type
    if method.upper() in ("POST", "PUT", "PATCH"):
        merged_headers.setdefault("Content-Type", "application/json")

    # --- 构建请求体 ---
    data: bytes | None = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    # --- 重试循环 ---
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
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(wait)
                wait *= 2  # 指数退避

    raise RuntimeError(
        f"http_json 请求失败（重试 {retries} 次）: {url} — {last_exc}"
    )
