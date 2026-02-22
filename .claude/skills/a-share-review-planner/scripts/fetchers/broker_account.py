"""jvQuant 券商账户采集器。

通过 jvQuant HTTP 柜台接口获取：账户资金、当日持仓、当日委托记录。

费用注意事项：
  - 每次 login 调用都会产生计费（1分钟周期聚合）
  - 本模块通过本地 ticket 缓存复用登录凭证，在 expire 时间内不重新登录
  - 缓存路径：~/.openclaw/.jvquant_ticket_cache.json

配置方式（任选其一，环境变量优先）：
  1. 环境变量：
       JVQUANT_COUNTER=http://xxx.xxx.xxx.xxx:xxxx
       JVQUANT_TOKEN=your_jvquant_token
       JVQUANT_ACC=your_account
       JVQUANT_PASS=your_password
  2. 配置文件 ~/.openclaw/jvquant.json：
       {"counter": "http://...", "token": "...", "acc": "...", "pass": "..."}

用法：
    from scripts.fetchers.broker_account import fetch_broker_account
    data = fetch_broker_account()
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

# ── 常量 ────────────────────────────────────────────────────────

_CACHE_PATH = os.path.expanduser("~/.openclaw/.jvquant_ticket_cache.json")
_CONFIG_PATH = os.path.expanduser("~/.openclaw/jvquant.json")

# 缓存提前失效窗口（秒）：distance from actual expire
# 避免在 ticket 即将到期时仍使用，留 60 秒 buffer
_EXPIRE_BUFFER_SEC = 60

_DEFAULT_TIMEOUT = 15.0


# ── 配置加载 ─────────────────────────────────────────────────────


def _load_config() -> dict:
    """加载 jvQuant 配置。环境变量优先，其次读取 ~/.openclaw/jvquant.json。"""
    cfg: dict = {}

    # 从配置文件读取基础值
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass

    # 环境变量覆盖（优先级更高）
    if os.environ.get("JVQUANT_COUNTER"):
        cfg["counter"] = os.environ["JVQUANT_COUNTER"].rstrip("/")
    if os.environ.get("JVQUANT_TOKEN"):
        cfg["token"] = os.environ["JVQUANT_TOKEN"]
    if os.environ.get("JVQUANT_ACC"):
        cfg["acc"] = os.environ["JVQUANT_ACC"]
    if os.environ.get("JVQUANT_PASS"):
        cfg["pass"] = os.environ["JVQUANT_PASS"]

    return cfg


def _require_config() -> dict:
    """返回配置，缺少必要字段时抛出 RuntimeError。"""
    cfg = _load_config()
    missing = [k for k in ("counter", "token", "acc", "pass") if not cfg.get(k)]
    if missing:
        raise RuntimeError(
            f"jvQuant 配置缺少字段: {missing}。\n"
            f"请设置环境变量 JVQUANT_COUNTER / JVQUANT_TOKEN / JVQUANT_ACC / JVQUANT_PASS，\n"
            f"或在 {_CONFIG_PATH} 中写入 JSON 配置。"
        )
    return cfg


# ── Ticket 缓存 ──────────────────────────────────────────────────


def _load_ticket_cache() -> Optional[dict]:
    """读取本地 ticket 缓存。如不存在或格式错误，返回 None。"""
    try:
        if os.path.exists(_CACHE_PATH):
            with open(_CACHE_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _save_ticket_cache(ticket: str, expire_at: float) -> None:
    """将 ticket 和过期时间戳写入缓存文件。"""
    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
    with open(_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"ticket": ticket, "expire_at": expire_at}, f)


def _get_valid_ticket(cfg: dict) -> str:
    """获取有效 ticket。优先复用缓存，过期才重新登录。

    复用缓存可避免重复计费。ticket 由 login 接口返回，有 expire（秒）有效期。
    """
    cache = _load_ticket_cache()
    now = time.time()

    if cache and cache.get("ticket") and cache.get("expire_at"):
        # 缓存仍在有效期内（留 60 秒 buffer）
        if now < cache["expire_at"] - _EXPIRE_BUFFER_SEC:
            return cache["ticket"]

    # 缓存失效，重新登录
    return _login(cfg)


def _login(cfg: dict) -> str:
    """调用 jvQuant login 接口，返回 ticket 并写入缓存。

    计费说明：此接口每次调用均会计费，请勿随意调用。
    模块已实现缓存机制，正常情况下每个 expire 周期只登录一次。
    """
    params = urllib.parse.urlencode({
        "token": cfg["token"],
        "acc": cfg["acc"],
        "pass": cfg["pass"],
    })
    url = f"{cfg['counter']}/login?{params}"

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"jvQuant login 失败: {exc}") from exc

    if str(data.get("code")) != "0":
        raise RuntimeError(f"jvQuant login 返回错误: {data}")

    ticket: str = data["ticket"]
    expire_sec: int = int(data.get("expire", 3600))
    expire_at = time.time() + expire_sec

    _save_ticket_cache(ticket, expire_at)
    return ticket


# ── 数据接口 ─────────────────────────────────────────────────────


def _http_get(url: str) -> dict:
    """发送 GET 请求并解析 JSON，失败抛出 RuntimeError。"""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"HTTP 请求失败: {url} — {exc}") from exc


def _fetch_positions(cfg: dict, ticket: str) -> dict:
    """获取账户资金和持仓列表（check_hold 接口）。"""
    params = urllib.parse.urlencode({"token": cfg["token"], "ticket": ticket})
    url = f"{cfg['counter']}/check_hold?{params}"
    data = _http_get(url)

    if str(data.get("code")) != "0":
        raise RuntimeError(f"check_hold 返回错误: {data}")
    return data


def _fetch_orders(cfg: dict, ticket: str) -> list:
    """获取当日委托记录（check_order 接口）。"""
    params = urllib.parse.urlencode({"token": cfg["token"], "ticket": ticket})
    url = f"{cfg['counter']}/check_order?{params}"
    data = _http_get(url)

    if str(data.get("code")) != "0":
        raise RuntimeError(f"check_order 返回错误: {data}")

    # 接口返回格式可能是列表或包含列表的 dict
    if isinstance(data, list):
        return data
    return data.get("order_list", data.get("data", []))


# ── 主入口 ───────────────────────────────────────────────────────


def fetch_broker_account() -> dict:
    """获取账户完整信息（资金 + 持仓 + 当日委托）。

    Returns
    -------
    dict
        包含以下字段：
        - total       : 账户总资产（字符串，如 "501527.77"）
        - usable      : 可用资金
        - day_earn    : 当日盈亏
        - hold_earn   : 持仓盈亏
        - hold_list   : 持仓列表（含 code/name/hold_vol/usable_vol/day_earn/hold_earn）
        - order_list  : 当日委托列表
        - fetched_at  : 采集时间戳（ISO 格式）
        - ticket_reused : bool，是否复用了缓存 ticket（true 表示没有新增登录计费）

    Raises
    ------
    RuntimeError
        配置缺失、网络失败或接口返回错误码时抛出。
    """
    cfg = _require_config()

    # 检查缓存是否有效（用于记录是否产生了登录费用）
    cache = _load_ticket_cache()
    now = time.time()
    ticket_reused = (
        cache is not None
        and cache.get("ticket")
        and cache.get("expire_at")
        and now < cache["expire_at"] - _EXPIRE_BUFFER_SEC
    )

    ticket = _get_valid_ticket(cfg)

    positions = _fetch_positions(cfg, ticket)
    orders = _fetch_orders(cfg, ticket)

    from datetime import datetime, timezone, timedelta
    fetched_at = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    return {
        "total": positions.get("total", ""),
        "usable": positions.get("usable", ""),
        "day_earn": positions.get("day_earn", ""),
        "hold_earn": positions.get("hold_earn", ""),
        "hold_list": positions.get("hold_list", []),
        "order_list": orders,
        "fetched_at": fetched_at,
        "ticket_reused": ticket_reused,
    }
