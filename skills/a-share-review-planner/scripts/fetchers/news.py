"""金融界新闻数据抓取模块。"""

import json
import urllib.request


def _http_json(url: str, *, method: str = "GET", body: dict | None = None, headers: dict | None = None) -> dict:
    """纯标准库实现的 HTTP JSON 请求函数。"""
    _headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        _headers.update(headers)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=_headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_list(resp: dict) -> list[dict]:
    """从接口响应中提取新闻列表。

    接口返回格式为 {"code": 20000, "data": {"total": N, "data": [...]}}。
    """
    outer = resp.get("data") or {}
    if isinstance(outer, list):
        return outer
    if isinstance(outer, dict):
        for key in ("data", "list", "records"):
            items = outer.get(key)
            if isinstance(items, list):
                return items
    return []


# ---------------------------------------------------------------------------
# 核心抓取函数
# ---------------------------------------------------------------------------

def fetch_news_list(channel_num: str, info_cls: str, page_size: int = 20) -> list[dict]:
    """查询新闻列表。

    Args:
        channel_num: 频道编号，如 "010"、"103"。
        info_cls: 信息分类编号，如 "001062"。
        page_size: 每页条数，默认 20。

    Returns:
        新闻条目列表。
    """
    url = "https://gateway.jrj.com/jrj-news/news/queryNewsList"
    payload = {
        "sortBy": 1,
        "pageSize": page_size,
        "makeDate": "",
        "channelNum": channel_num,
        "infoCls": info_cls,
    }
    resp = _http_json(url, method="POST", body=payload)
    return _extract_list(resp)


def fetch_news_flash(page_size: int = 20) -> list[dict]:
    """查询新闻快讯。"""
    url = "https://gateway.jrj.com/jrj-news/news/queryNewsFlash"
    payload = {"pageSize": page_size}
    resp = _http_json(url, method="POST", body=payload)
    return _extract_list(resp)[:page_size]


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def fetch_headline(page_size: int = 20) -> list[dict]:
    """A股头条 (channelNum=010, infoCls=001062)。"""
    return fetch_news_list("010", "001062", page_size=page_size)


def fetch_realtime(page_size: int = 20) -> list[dict]:
    """市况直击 (channelNum=010, infoCls=001140)。"""
    return fetch_news_list("010", "001140", page_size=page_size)


def fetch_opportunity(page_size: int = 20) -> list[dict]:
    """机会情报 (channelNum=010, infoCls=001161)。"""
    return fetch_news_list("010", "001161", page_size=page_size)


def fetch_daily_finance(page_size: int = 20) -> list[dict]:
    """每日财经 (channelNum=103, infoCls=001116)。"""
    return fetch_news_list("103", "001116", page_size=page_size)


# ---------------------------------------------------------------------------
# 聚合函数
# ---------------------------------------------------------------------------

def fetch_all_news(page_size: int = 20) -> dict:
    """一次性抓取所有新闻分类。

    Returns:
        包含 headline / realtime / opportunity / daily_finance / flash 五个键的字典。
    """
    return {
        "headline": fetch_headline(page_size=page_size),
        "realtime": fetch_realtime(page_size=page_size),
        "opportunity": fetch_opportunity(page_size=page_size),
        "daily_finance": fetch_daily_finance(page_size=page_size),
        "flash": fetch_news_flash(page_size=page_size),
    }
