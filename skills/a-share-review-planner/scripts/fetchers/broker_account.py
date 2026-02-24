"""jvQuant 券商账户采集器。

通过 jvQuant HTTP 柜台接口获取：账户资金、当日持仓、当日委托记录。
采集结果自动持久化到本地，支持历史回查。

费用注意事项：
  - 每次 login 调用都会产生计费（5毛/次）
  - 本模块通过本地 ticket 缓存复用登录凭证，在 expire 时间内不重新登录
  - 缓存路径：~/.openclaw/.jvquant_ticket_cache.json
  - 柜台地址通过 /query/server 自动获取并缓存

持久化存储：
  - 路径：~/.openclaw/broker_data/
  - 持仓快照：positions/YYYY-MM-DD.json （每日覆盖写入，保留最新）
  - 委托记录：orders/YYYY-MM-DD.json    （每日覆盖写入）

配置方式（任选其一，环境变量优先）：
  1. 环境变量（推荐）：
       JVQUANT_APP_TOKEN=your_jvquant_token
       EASTMONEY_ACCOUNT=your_account
       EASTMONEY_PASSWORD=your_password
     兼容旧变量名（优先级低于上述）：
       JVQUANT_TOKEN / JVQUANT_ACC / JVQUANT_PASS
  2. 配置文件 ~/.openclaw/jvquant.json：
       {"token": "...", "acc": "...", "pass": "..."}

用法：
    from scripts.fetchers.broker_account import fetch_broker_account
    data = fetch_broker_account()       # 采集当日数据（自动持久化）

    from scripts.fetchers.broker_account import load_history
    history = load_history(days=30)     # 查询最近30天历史
"""

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# ── 常量 ────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

_CN_TZ = timezone(timedelta(hours=8))

_CACHE_DIR = os.path.expanduser("~/.openclaw")
_TICKET_CACHE_PATH = os.path.join(_CACHE_DIR, ".jvquant_ticket_cache.json")
_COUNTER_CACHE_PATH = os.path.join(_CACHE_DIR, ".jvquant_counter_cache.json")
_CONFIG_PATH = os.path.join(_CACHE_DIR, "jvquant.json")

# 持久化存储目录
_DATA_DIR = os.path.join(_CACHE_DIR, "broker_data")
_POSITIONS_DIR = os.path.join(_DATA_DIR, "positions")
_ORDERS_DIR = os.path.join(_DATA_DIR, "orders")

# 柜台地址分配 API
_SERVER_QUERY_URL = "http://jvquant.com/query/server"

# ticket 提前失效窗口（秒），留 60 秒 buffer 避免边界过期
_EXPIRE_BUFFER_SEC = 60

# 柜台地址缓存有效期（秒），30 分钟
_COUNTER_CACHE_TTL = 1800

_DEFAULT_TIMEOUT = 15.0


# ── 配置加载 ─────────────────────────────────────────────────────


def _load_config() -> dict:
    """加载 jvQuant 配置。

    优先级：环境变量（新名 > 旧名） > 配置文件。
    柜台地址不再需要手动配置，由 /query/server 自动获取。
    """
    cfg: dict = {}

    # 从配置文件读取基础值
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass

    # 旧环境变量（向后兼容）
    if os.environ.get("JVQUANT_TOKEN"):
        cfg["token"] = os.environ["JVQUANT_TOKEN"]
    if os.environ.get("JVQUANT_ACC"):
        cfg["acc"] = os.environ["JVQUANT_ACC"]
    if os.environ.get("JVQUANT_PASS"):
        cfg["pass"] = os.environ["JVQUANT_PASS"]

    # 新环境变量（优先级最高，覆盖旧名）
    if os.environ.get("JVQUANT_APP_TOKEN"):
        cfg["token"] = os.environ["JVQUANT_APP_TOKEN"]
    if os.environ.get("EASTMONEY_ACCOUNT"):
        cfg["acc"] = os.environ["EASTMONEY_ACCOUNT"]
    if os.environ.get("EASTMONEY_PASSWORD"):
        cfg["pass"] = os.environ["EASTMONEY_PASSWORD"]

    return cfg


def _require_config() -> dict:
    """返回配置，缺少必要字段时抛出 RuntimeError。"""
    cfg = _load_config()
    missing = [k for k in ("token", "acc", "pass") if not cfg.get(k)]
    if missing:
        field_map = {
            "token": "JVQUANT_APP_TOKEN",
            "acc": "EASTMONEY_ACCOUNT",
            "pass": "EASTMONEY_PASSWORD",
        }
        hint = " / ".join(field_map[k] for k in missing)
        raise RuntimeError(
            f"jvQuant 配置缺少字段: {missing}。\n"
            f"请设置环境变量 {hint}，\n"
            f"或在 {_CONFIG_PATH} 中写入 JSON 配置。"
        )
    return cfg


# ── 柜台地址动态获取 ──────────────────────────────────────────────


def _load_counter_cache() -> str | None:
    """读取柜台地址缓存。过期或不存在返回 None。"""
    try:
        if os.path.exists(_COUNTER_CACHE_PATH):
            with open(_COUNTER_CACHE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if time.time() < data.get("expire_at", 0):
                return data["counter"]
    except Exception:
        pass
    return None


def _save_counter_cache(counter: str) -> None:
    """缓存柜台地址。"""
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(_COUNTER_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"counter": counter, "expire_at": time.time() + _COUNTER_CACHE_TTL}, f
        )


def _query_trade_server(token: str) -> str:
    """调用 /query/server 获取沪深交易柜台地址。

    此接口不计费，但返回的地址可能变化，因此做短期缓存。
    """
    cached = _load_counter_cache()
    if cached:
        logger.debug("复用柜台地址缓存: %s", cached)
        return cached

    params = urllib.parse.urlencode({"market": "ab", "type": "trade", "token": token})
    url = f"{_SERVER_QUERY_URL}?{params}"

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(f"查询柜台地址失败: {exc}") from exc

    if str(data.get("code")) != "0":
        raise RuntimeError(f"查询柜台地址返回错误: {data}")

    server = data["server"]
    if not server.startswith("http"):
        server = f"http://{server}"
    server = server.rstrip("/")

    _save_counter_cache(server)
    logger.debug("获取柜台地址: %s", server)
    return server


# ── Ticket 缓存 ──────────────────────────────────────────────────


def _load_ticket_cache() -> dict | None:
    """读取本地 ticket 缓存。如不存在或格式错误，返回 None。"""
    try:
        if os.path.exists(_TICKET_CACHE_PATH):
            with open(_TICKET_CACHE_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _save_ticket_cache(ticket: str, expire_at: float) -> None:
    """将 ticket 和过期时间戳写入缓存文件。"""
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(_TICKET_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"ticket": ticket, "expire_at": expire_at}, f)


def _get_valid_ticket(cfg: dict, counter: str) -> str:
    """获取有效 ticket。优先复用缓存，过期才重新登录。"""
    cache = _load_ticket_cache()
    now = time.time()

    if cache and cache.get("ticket") and cache.get("expire_at"):
        if now < cache["expire_at"] - _EXPIRE_BUFFER_SEC:
            return cache["ticket"]

    return _login(cfg, counter)


def _login(cfg: dict, counter: str) -> str:
    """调用 jvQuant login 接口，返回 ticket 并写入缓存。

    计费说明：此接口每次调用计费 5毛，请勿随意调用。
    模块已实现缓存机制，正常情况下每个 expire 周期只登录一次。
    """
    params = urllib.parse.urlencode(
        {
            "token": cfg["token"],
            "acc": cfg["acc"],
            "pass": cfg["pass"],
        }
    )
    url = f"{counter}/login?{params}"

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(f"jvQuant login 失败: {exc}") from exc

    if str(data.get("code")) != "0":
        raise RuntimeError(f"jvQuant login 返回错误: {data}")

    ticket: str = data["ticket"]
    expire_sec: int = int(data.get("expire", 3600))
    expire_at = time.time() + expire_sec

    _save_ticket_cache(ticket, expire_at)
    logger.debug("login 成功, ticket 有效期 %d 秒", expire_sec)
    return ticket


# ── 数据接口 ─────────────────────────────────────────────────────


def _http_get(url: str) -> dict:
    """发送 GET 请求并解析 JSON，失败抛出 RuntimeError。"""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(f"HTTP 请求失败: {url} — {exc}") from exc


def _fetch_positions(counter: str, token: str, ticket: str) -> dict:
    """获取账户资金和持仓列表（check_hold 接口）。"""
    params = urllib.parse.urlencode({"token": token, "ticket": ticket})
    url = f"{counter}/check_hold?{params}"
    data = _http_get(url)

    if str(data.get("code")) != "0":
        raise RuntimeError(f"check_hold 返回错误: {data}")
    return data


def _fetch_orders(counter: str, token: str, ticket: str) -> list:
    """获取当日委托记录（check_order 接口）。"""
    params = urllib.parse.urlencode({"token": token, "ticket": ticket})
    url = f"{counter}/check_order?{params}"
    data = _http_get(url)

    if str(data.get("code")) != "0":
        raise RuntimeError(f"check_order 返回错误: {data}")

    if isinstance(data, list):
        return data
    return data.get("list", data.get("order_list", data.get("data", [])))


# ── 持久化存储 ───────────────────────────────────────────────────


def _today_str() -> str:
    """返回当日日期字符串 YYYY-MM-DD（北京时间）。"""
    return datetime.now(_CN_TZ).strftime("%Y-%m-%d")


def _save_daily_data(directory: str, date_str: str, data: dict | list) -> None:
    """将数据写入 directory/YYYY-MM-DD.json。同日多次调用覆盖写入。"""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{date_str}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.debug("持久化写入: %s", path)


def _persist_account_data(account_data: dict) -> None:
    """将采集结果持久化到本地文件。

    - positions/YYYY-MM-DD.json: 资金 + 持仓快照
    - orders/YYYY-MM-DD.json:    当日委托记录
    """
    date_str = _today_str()

    # 持仓快照
    position_snapshot = {
        "date": date_str,
        "fetched_at": account_data["fetched_at"],
        "total": account_data["total"],
        "usable": account_data["usable"],
        "day_earn": account_data["day_earn"],
        "hold_earn": account_data["hold_earn"],
        "hold_list": account_data["hold_list"],
    }
    _save_daily_data(_POSITIONS_DIR, date_str, position_snapshot)

    # 委托记录（仅当有委托时写入）
    orders = account_data.get("order_list", [])
    if orders:
        order_snapshot = {
            "date": date_str,
            "fetched_at": account_data["fetched_at"],
            "order_list": orders,
        }
        _save_daily_data(_ORDERS_DIR, date_str, order_snapshot)
        logger.debug("持久化 %d 条委托记录", len(orders))
    else:
        logger.debug("当日无委托记录，跳过 orders 持久化")


def load_history(days: int = 30) -> dict:
    """查询最近 N 天的持仓快照和委托记录。

    Args:
        days: 回查天数，默认 30。

    Returns:
        {
            "positions": {
                "2026-02-24": {...},
                "2026-02-23": {...},
                ...
            },
            "orders": {
                "2026-02-24": {...},
                ...
            },
            "available_days": 5,       # 实际有数据的天数
            "date_range": ["2026-02-20", "2026-02-24"],
        }
    """
    today = datetime.now(_CN_TZ).date()
    positions: dict[str, dict] = {}
    orders: dict[str, dict] = {}

    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")

        pos_path = os.path.join(_POSITIONS_DIR, f"{date_str}.json")
        if os.path.exists(pos_path):
            try:
                with open(pos_path, encoding="utf-8") as f:
                    positions[date_str] = json.load(f)
            except Exception:
                logger.warning("读取持仓文件失败: %s", pos_path)

        order_path = os.path.join(_ORDERS_DIR, f"{date_str}.json")
        if os.path.exists(order_path):
            try:
                with open(order_path, encoding="utf-8") as f:
                    orders[date_str] = json.load(f)
            except Exception:
                logger.warning("读取委托文件失败: %s", order_path)

    all_dates = sorted(set(list(positions.keys()) + list(orders.keys())))

    return {
        "positions": positions,
        "orders": orders,
        "available_days": len(all_dates),
        "date_range": [all_dates[0], all_dates[-1]] if all_dates else [],
    }


# ── 主入口 ───────────────────────────────────────────────────────


def fetch_broker_account() -> dict:
    """获取账户完整信息（资金 + 持仓 + 当日委托），自动持久化到本地。

    Returns:
        包含以下字段的字典：
        - total        : 账户总资产
        - usable       : 可用资金
        - day_earn     : 当日盈亏
        - hold_earn    : 持仓盈亏
        - hold_list    : 持仓列表
        - order_list   : 当日委托列表
        - fetched_at   : 采集时间戳（ISO 格式）
        - ticket_reused: 是否复用了缓存 ticket

    Raises:
        RuntimeError: 配置缺失、网络失败或接口返回错误码时抛出。
    """
    cfg = _require_config()

    # 动态获取柜台地址
    counter = _query_trade_server(cfg["token"])

    # 检查缓存是否有效（用于记录是否产生了登录费用）
    cache = _load_ticket_cache()
    now = time.time()
    ticket_reused = (
        cache is not None
        and cache.get("ticket")
        and cache.get("expire_at")
        and now < cache["expire_at"] - _EXPIRE_BUFFER_SEC
    )

    ticket = _get_valid_ticket(cfg, counter)

    positions = _fetch_positions(counter, cfg["token"], ticket)
    orders = _fetch_orders(counter, cfg["token"], ticket)

    fetched_at = datetime.now(_CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    result = {
        "total": positions.get("total", ""),
        "usable": positions.get("usable", ""),
        "day_earn": positions.get("day_earn", ""),
        "hold_earn": positions.get("hold_earn", ""),
        "hold_list": positions.get("hold_list", []),
        "order_list": orders,
        "fetched_at": fetched_at,
        "ticket_reused": ticket_reused,
    }

    # 自动持久化
    try:
        _persist_account_data(result)
    except Exception:
        logger.exception("持久化账户数据失败")

    return result
