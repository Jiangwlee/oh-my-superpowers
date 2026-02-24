"""金融界新闻数据抓取模块。"""

import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html.parser import HTMLParser

from scripts.core.cache import cache_get, cache_set
from scripts.core.http_client import http_json as core_http_json


def _today_ymd() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _http_json(url: str, *, method: str = "GET", body: dict | None = None, headers: dict | None = None) -> dict:
    """纯标准库实现的 HTTP JSON 请求函数。"""
    cache_key = f"news_http|{method}|{url}|{json.dumps(body or {}, ensure_ascii=False, sort_keys=True)}"
    cached = cache_get("news", cache_key)
    if isinstance(cached, dict):
        return cached
    _headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        _headers.update(headers)
    data = core_http_json(url, method=method, payload=body, headers=_headers, timeout=15)
    ttl = 7200 if "queryNewsFlash" in url else 1800
    cache_set("news", cache_key, data, ttl_seconds=ttl)
    return data


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
# 文章正文抓取（HTMLParser，不使用正则）
# ---------------------------------------------------------------------------

class _ArticleContentParser(HTMLParser):
    """提取 <div class="article_content"> 内的纯文本。"""

    def __init__(self) -> None:
        super().__init__()
        self._in_article = False
        self._depth = 0          # article_content div 的嵌套深度计数
        self._skip_depth = 0     # script/style 跳过深度
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attr_map = dict(attrs)
        cls = attr_map.get("class") or ""
        if tag == "div" and "article_content" in cls:
            self._in_article = True
            self._depth = 1
            return
        if self._in_article:
            if tag == "div":
                self._depth += 1
            if tag in {"script", "style"}:
                self._skip_depth += 1
            if tag in {"br", "p", "li"}:
                self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self._in_article:
            return
        if tag in {"script", "style"} and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "div":
            self._depth -= 1
            if self._depth <= 0:
                self._in_article = False

    def handle_data(self, data: str) -> None:
        if self._in_article and self._skip_depth == 0:
            text = data.strip()
            if text:
                self.parts.append(text)

    def get_text(self) -> str:
        text = " ".join(self.parts)
        while "  " in text:
            text = text.replace("  ", " ")
        return text.strip()


def _fetch_article_body(url: str) -> str:
    """抓取文章详情页，返回正文纯文本。失败返回空字符串。"""
    if not url:
        return ""
    cache_key = f"news_body|{_today_ymd()}|{url}"
    cached = cache_get("news", cache_key)
    if isinstance(cached, str):
        return cached
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        parser = _ArticleContentParser()
        parser.feed(html)
        text = parser.get_text()
        cache_set("news", cache_key, text, ttl_seconds=1800)
        return text
    except Exception:
        return ""


def _enrich_with_body(items: list[dict], max_workers: int = 5) -> list[dict]:
    """并发为列表中每条新闻补充 detail 字段（从 pcInfoUrl 抓取正文）。

    若 detail 已有内容则跳过。inplace 修改并返回原列表。
    """
    targets = [
        (i, item["pcInfoUrl"])
        for i, item in enumerate(items)
        if not item.get("detail") and item.get("pcInfoUrl")
    ]
    if not targets:
        return items

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {pool.submit(_fetch_article_body, url): i for i, url in targets}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                items[idx]["detail"] = future.result()
            except Exception:
                items[idx]["detail"] = ""
    return items


# ---------------------------------------------------------------------------
# 核心抓取函数
# ---------------------------------------------------------------------------

def fetch_news_list(
    channel_num: str,
    info_cls: str,
    page_size: int = 20,
    fetch_body: bool = False,
) -> list[dict]:
    """查询新闻列表。

    Args:
        channel_num: 频道编号，如 "010"、"103"。
        info_cls: 信息分类编号，如 "001062"。
        page_size: 每页条数，默认 20。
        fetch_body: 是否并发抓取每篇文章正文（填充 detail 字段），默认 False。

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
    items = _extract_list(resp)
    if fetch_body:
        _enrich_with_body(items)
    return items


def fetch_news_flash(page_size: int = 20) -> list[dict]:
    """查询新闻快讯。"""
    url = "https://gateway.jrj.com/jrj-news/news/queryNewsFlash"
    payload = {"pageSize": page_size}
    resp = _http_json(url, method="POST", body=payload)
    return _extract_list(resp)[:page_size]


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def fetch_headline(page_size: int = 20, fetch_body: bool = False) -> list[dict]:
    """A股头条 (channelNum=010, infoCls=001062)。"""
    return fetch_news_list("010", "001062", page_size=page_size, fetch_body=fetch_body)


def fetch_realtime(page_size: int = 20, fetch_body: bool = False) -> list[dict]:
    """市况直击 (channelNum=010, infoCls=001140)。"""
    return fetch_news_list("010", "001140", page_size=page_size, fetch_body=fetch_body)


def fetch_opportunity(page_size: int = 20, fetch_body: bool = False) -> list[dict]:
    """机会情报 (channelNum=010, infoCls=001161)。"""
    return fetch_news_list("010", "001161", page_size=page_size, fetch_body=fetch_body)


def fetch_daily_finance(page_size: int = 20, fetch_body: bool = False) -> list[dict]:
    """每日财经 (channelNum=103, infoCls=001116)。"""
    return fetch_news_list("103", "001116", page_size=page_size, fetch_body=fetch_body)


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
