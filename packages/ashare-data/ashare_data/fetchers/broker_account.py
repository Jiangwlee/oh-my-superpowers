"""jvQuant 券商账户采集器。

通过 jvQuant HTTP 柜台接口获取：账户资金、当日持仓、当日委托记录。
采集结果自动持久化到本地，支持历史回查。

费用注意事项：
  - 每次 login 调用都会产生计费（5毛/次）
  - 本模块通过本地 ticket 缓存复用登录凭证，在 expire 时间内不重新登录
  - 缓存路径：~/.ashare-data/.jvquant_ticket_cache.json
  - 柜台地址通过 /query/server 自动获取并缓存
  - 每日费用自动追踪，超过限额（默认 5 元）拒绝调用

费用追踪：
  - 路径：~/.ashare-assistant/broker_data/costs/YYYY-MM-DD.json
  - 每次 login 自动记录 0.5 元
  - 每日累计费用达到限额后，新的 API 调用会被拒绝（抛出 RuntimeError）

持久化存储：
  - 路径：~/.ashare-assistant/broker_data/
  - 持仓快照：positions/YYYY-MM-DD.json （每日覆盖写入，保留最新）
  - 委托记录：orders/YYYY-MM-DD.json    （每日覆盖写入）

配置方式（任选其一，环境变量优先）：
  1. 环境变量（推荐）：
       JVQUANT_APP_TOKEN=your_jvquant_token
       EASTMONEY_ACCOUNT=your_account
       EASTMONEY_PASSWORD=your_password
  2. 配置文件 ~/.ashare-data/jvquant.json：
       {"token": "...", "acc": "...", "pass": "..."}

用法：
    from ashare_data.fetchers.broker_account import fetch_broker_account
    data = fetch_broker_account()       # 采集当日数据（自动持久化）

    from ashare_data.fetchers.broker_account import load_history
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
from ashare_data.core.config import BROKER_DIR
from ashare_data.core.http_client import http_json as core_http_json

# ── 常量 ────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

# jvQuant 柜台接口需直连，禁止经过系统 http_proxy。
_NO_PROXY_OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
)

_CN_TZ = timezone(timedelta(hours=8))

_CACHE_DIR = os.path.expanduser("~/.ashare-data")
_TICKET_CACHE_PATH = os.path.join(_CACHE_DIR, ".jvquant_ticket_cache.json")
_COUNTER_CACHE_PATH = os.path.join(_CACHE_DIR, ".jvquant_counter_cache.json")
_CONFIG_PATH = os.path.join(_CACHE_DIR, "jvquant.json")

# 持久化存储目录
_DATA_DIR = str(BROKER_DIR)
_POSITIONS_DIR = os.path.join(_DATA_DIR, "positions")
_ORDERS_DIR = os.path.join(_DATA_DIR, "orders")
_COSTS_DIR = os.path.join(_DATA_DIR, "costs")

# 柜台地址分配 API
_SERVER_QUERY_URL = "http://jvquant.com/query/server"

# ticket 提前失效窗口（秒），留 5 分钟 buffer 避免边界过期
_EXPIRE_BUFFER_SEC = 300

# 柜台地址缓存有效期（秒），30 分钟
_COUNTER_CACHE_TTL = 1800

_DEFAULT_TIMEOUT = 15.0

# 费用控制
_LOGIN_COST_CNY = 0.5  # 每次 login 计费（元）
_DAILY_BUDGET_CNY = 5.0  # 每日费用上限（元）


# ── 配置加载 ─────────────────────────────────────────────────────


def _load_config() -> dict:
    """加载 jvQuant 配置。

    优先级：环境变量 > 配置文件。
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

    # 环境变量（优先级最高）
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
        with _NO_PROXY_OPENER.open(req, timeout=_DEFAULT_TIMEOUT) as resp:
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
    """获取有效 ticket。优先复用缓存，5 分钟内过期则重新登录。"""
    cache = _load_ticket_cache()
    now = time.time()

    if cache and cache.get("ticket") and cache.get("expire_at"):
        if now < cache["expire_at"] - _EXPIRE_BUFFER_SEC:
            logger.debug(
                "复用 ticket 缓存, 剩余 %.0f 秒",
                cache["expire_at"] - now,
            )
            return cache["ticket"]
        logger.debug(
            "ticket 将在 %.0f 秒内过期, 重新登录",
            max(0, cache["expire_at"] - now),
        )

    return _login(cfg, counter)


# ── 每日费用追踪 ─────────────────────────────────────────────────


def _load_daily_cost(date_str: str | None = None) -> dict:
    """读取当日费用记录。

    Returns:
        {"date": "YYYY-MM-DD", "total_cost": float, "calls": [...]}
    """
    if date_str is None:
        date_str = _today_str()
    path = os.path.join(_COSTS_DIR, f"{date_str}.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"date": date_str, "total_cost": 0.0, "calls": []}


def _record_cost(api_name: str, cost: float) -> float:
    """记录一次 API 调用费用，返回当日累计费用。

    Args:
        api_name: 接口名称（如 "login"）。
        cost: 本次费用（元）。

    Returns:
        当日累计费用。
    """
    date_str = _today_str()
    record = _load_daily_cost(date_str)
    record["total_cost"] = round(record["total_cost"] + cost, 2)
    record["calls"].append(
        {
            "api": api_name,
            "cost": cost,
            "time": datetime.now(_CN_TZ).strftime("%H:%M:%S"),
        }
    )

    os.makedirs(_COSTS_DIR, exist_ok=True)
    path = os.path.join(_COSTS_DIR, f"{date_str}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    logger.debug(
        "记录费用: %s %.2f 元, 当日累计 %.2f 元", api_name, cost, record["total_cost"]
    )
    return record["total_cost"]


def _check_daily_budget() -> None:
    """检查当日费用是否已超出预算，超出则抛出 RuntimeError。"""
    record = _load_daily_cost()
    if record["total_cost"] >= _DAILY_BUDGET_CNY:
        raise RuntimeError(
            f"JVQuant 当日费用已达 {record['total_cost']:.2f} 元，"
            f"超出每日预算 {_DAILY_BUDGET_CNY:.2f} 元，拒绝调用。"
            f"调用明细: {len(record['calls'])} 次"
        )


def get_daily_cost_summary(date_str: str | None = None) -> dict:
    """查询指定日期的费用摘要（公开接口）。

    Args:
        date_str: 日期字符串 YYYY-MM-DD，默认当日。

    Returns:
        {"date": "YYYY-MM-DD", "total_cost": float, "call_count": int,
         "budget": float, "remaining": float}
    """
    record = _load_daily_cost(date_str)
    return {
        "date": record["date"],
        "total_cost": record["total_cost"],
        "call_count": len(record["calls"]),
        "budget": _DAILY_BUDGET_CNY,
        "remaining": round(_DAILY_BUDGET_CNY - record["total_cost"], 2),
    }


def _login(cfg: dict, counter: str) -> str:
    """调用 jvQuant login 接口，返回 ticket 并写入缓存。

    计费说明：此接口每次调用计费 5毛，请勿随意调用。
    模块已实现缓存机制，正常情况下每个 expire 周期只登录一次。
    调用前自动检查每日预算，超出则拒绝。
    """
    _check_daily_budget()

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
        with _NO_PROXY_OPENER.open(req, timeout=_DEFAULT_TIMEOUT) as resp:
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
    total_cost = _record_cost("login", _LOGIN_COST_CNY)
    logger.debug(
        "login 成功, ticket 有效期 %d 秒, 当日累计费用 %.2f 元",
        expire_sec,
        total_cost,
    )
    return ticket


# ── 数据接口 ─────────────────────────────────────────────────────


def _http_get(url: str) -> dict:
    """发送 GET 请求并解析 JSON，失败抛出 RuntimeError。"""
    try:
        return core_http_json(
            url, method="GET", timeout=_DEFAULT_TIMEOUT, retries=2, sleep_sec=0.5
        )
    except Exception as exc:
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


def _is_today_trading_day() -> bool:
    """判断今天是否为交易日（通过金融界 tradedate 接口）。

    Returns:
        True  — 今天是交易日；
        False — 今天是非交易日（周末/节假日）。
        接口调用失败时保守返回 True（宁可调 API 也不漏数据）。
    """
    try:
        from ashare_data.fetchers.trade_date import fetch_trade_date
        today_ymd = datetime.now(_CN_TZ).strftime("%Y%m%d")
        return fetch_trade_date() == today_ymd
    except Exception:
        logger.warning("无法判断是否为交易日，保守视为交易日")
        return True


def _load_most_recent_cache(days: int = 7) -> dict | None:
    """查找最近 N 天内最新的持仓缓存（跨日期，用于非交易日回退）。

    Args:
        days: 向前查找的天数，默认7天。

    Returns:
        与 fetch_broker_account() 格式一致的字典；找不到时返回 None。
    """
    today = datetime.now(_CN_TZ).date()
    for i in range(days):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        cached = _load_post_market_cache(date_str)
        if cached is not None:
            return cached
    return None


def _is_post_close_snapshot(fetched_at: str, today_str: str) -> bool:
    """判断缓存快照是否为当日盘后（>=15:00）生成。"""
    if not fetched_at:
        return False
    try:
        dt = datetime.fromisoformat(fetched_at)
    except ValueError:
        return False

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_CN_TZ)
    else:
        dt = dt.astimezone(_CN_TZ)

    if dt.strftime("%Y-%m-%d") != today_str:
        return False
    return (dt.hour, dt.minute, dt.second) >= (15, 0, 0)


def _load_post_market_cache(today_str: str) -> dict | None:
    """盘后缓存读取：从本地持久化文件拼装账户数据，不调用任何 API。

    Args:
        today_str: 当日日期字符串，格式 YYYY-MM-DD。

    Returns:
        与 fetch_broker_account() 返回格式一致的字典；缓存不存在时返回 None。
    """
    positions_path = os.path.join(_POSITIONS_DIR, f"{today_str}.json")
    if not os.path.exists(positions_path):
        return None
    try:
        with open(positions_path, encoding="utf-8") as f:
            cached_pos = json.load(f)
        fetched_at = str(cached_pos.get("fetched_at", "") or "")
        if not _is_post_close_snapshot(fetched_at, today_str):
            logger.info(
                "当日缓存存在但非盘后快照，忽略缓存并回退 API（fetched_at: %s）",
                fetched_at,
            )
            return None
        orders: list = []
        orders_path = os.path.join(_ORDERS_DIR, f"{today_str}.json")
        if os.path.exists(orders_path):
            with open(orders_path, encoding="utf-8") as f:
                orders = json.load(f).get("order_list", [])
        logger.info(
            "盘后缓存命中，跳过 API 调用（fetched_at: %s, orders: %d 条）",
            fetched_at,
            len(orders),
        )
        return {
            "total": cached_pos.get("total", ""),
            "usable": cached_pos.get("usable", ""),
            "day_earn": cached_pos.get("day_earn", ""),
            "hold_earn": cached_pos.get("hold_earn", ""),
            "hold_list": cached_pos.get("hold_list", []),
            "order_list": orders,
            "fetched_at": fetched_at,
            "ticket_reused": True,
        }
    except Exception:
        logger.warning("盘后缓存读取失败，回退到 API 调用")
        return None


def fetch_broker_account() -> dict:
    """获取账户完整信息（资金 + 持仓 + 当日委托），自动持久化到本地。

    盘后（≥15:00）且当日持仓缓存已存在时，直接从本地返回，不调用任何 API。

    调用前自动执行 guard 检查：
      1. 检查每日费用是否超出预算（5 元/天）
      2. 检查 ticket 是否在 5 分钟内过期，过期则重新登录

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
        RuntimeError: 配置缺失、网络失败、接口返回错误码或每日费用超出预算时抛出。
    """
    # 防护：只有交易日 15:00 后才抓取，其他时间一律用最近缓存
    now_cn = datetime.now(_CN_TZ)
    market_close = now_cn.replace(hour=15, minute=0, second=0, microsecond=0)
    is_trading_day = _is_today_trading_day()
    is_post_close = now_cn >= market_close

    if is_trading_day and is_post_close:
        # 交易日收盘后：优先命中当日缓存，无缓存才走 API
        cached = _load_post_market_cache(now_cn.strftime("%Y-%m-%d"))
        if cached is not None:
            return cached
        # 无当日缓存 → 继续往下走 API 流程
    else:
        # 非交易日 或 交易日盘中/盘前 → 只用缓存，不调 API
        cached = _load_most_recent_cache()
        if cached is not None:
            reason = "非交易日" if not is_trading_day else f"盘中（{now_cn.strftime('%H:%M')}）"
            logger.info("当前为%s，返回最近缓存（fetched_at: %s）", reason, cached.get("fetched_at", ""))
            return cached
        reason = "非交易日" if not is_trading_day else f"盘中（{now_cn.strftime('%H:%M')}，未到15:00收盘）"
        raise RuntimeError(
            f"当前为{reason}，无法获取券商账户数据，且无历史缓存可用。"
            "请在交易日15:00后重新采集。"
        )

    # Guard: 费用预算检查（在任何计费操作之前）
    _check_daily_budget()

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

    # Guard: ticket 过期检查（_get_valid_ticket 内部处理）
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
