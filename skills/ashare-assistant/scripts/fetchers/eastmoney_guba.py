"""东方财富股吧数据抓取模块。

说明
----
- 使用标准库实现（urllib + html.parser），避免正则解析 HTML。
- 支持：
  1) 最新帖子列表（gbapi JSONP）
  2) 单帖正文（news 页面内嵌 post_article）
  3) 股票资讯列表（list,code,1,f.html）
  4) 股票公告列表（list,code,3,f.html，支持近 N 天过滤）
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from html import unescape
from html.parser import HTMLParser
from typing import Any

from scripts.core.cache import cache_get, cache_set
from scripts.core.http_client import http_text

_GBAPI_LIST_URL = (
    "https://gbapi.eastmoney.com/webarticlelist/api/Article/Articlelist"
    "?code={code}&sorttype=1&ps={ps}&from=CommonBaPost"
    "&deviceid=quoteweb&version=200&product=Guba&plat=Web&needzd=true"
    "&callback={callback}"
)

_GUBA_NEWS_URL = "https://guba.eastmoney.com/news,{code},{post_id}.html"
_GUBA_LIST_URL = "https://guba.eastmoney.com/list,{code},{tab},f.html"
_GUBA_BASE = "https://guba.eastmoney.com"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "Gecko/20100101 Firefox/147.0"
    ),
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _http_text(url: str, timeout: float = 15.0, headers: dict[str, str] | None = None) -> str:
    cache_key = f"em_guba_text|{datetime.now().strftime('%Y-%m-%d')}|{url}"
    cached = cache_get("eastmoney", cache_key)
    if isinstance(cached, str):
        return cached
    req_headers = dict(_HEADERS)
    if headers:
        req_headers.update(headers)
    text = http_text(url, headers=req_headers, timeout=timeout)
    ttl = 1800
    cache_set("eastmoney", cache_key, text, ttl_seconds=ttl)
    return text


def _parse_jsonp(payload: str) -> dict[str, Any]:
    """解析 JSONP 为 dict，不使用正则。"""
    left = payload.find("(")
    right = payload.rfind(")")
    if left == -1 or right == -1 or left >= right:
        raise ValueError("invalid JSONP payload")
    inner = payload[left + 1 : right]
    return json.loads(inner)


class _TextExtractor(HTMLParser):
    """HTML 转纯文本（简单提取）。"""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return
        if tag in {"br", "p", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if self._skip_depth > 0:
            return
        if tag in {"p", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        text = data.strip()
        if text:
            self.parts.append(text)

    def to_text(self) -> str:
        merged = " ".join(p if p != "\n" else "\n" for p in self.parts)
        lines = [" ".join(line.split()) for line in merged.splitlines()]
        lines = [l for l in lines if l]
        return "\n".join(lines)


def _html_to_text(html_fragment: str) -> str:
    parser = _TextExtractor()
    parser.feed(html_fragment)
    parser.close()
    return unescape(parser.to_text())


def _extract_js_object(page: str, marker: str) -> dict[str, Any]:
    """从页面中抽取 `marker + { ... }` 的 JSON 对象。"""
    i = page.find(marker)
    if i == -1:
        raise ValueError(f"marker not found: {marker}")

    start = page.find("{", i)
    if start == -1:
        raise ValueError("object start not found")

    depth = 0
    in_str = False
    escaped = False
    end = -1

    for idx in range(start, len(page)):
        ch = page[idx]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = idx
                break

    if end == -1:
        raise ValueError("object end not found")

    raw = page[start : end + 1]
    return json.loads(raw)


@dataclass
class _Row:
    read: int = 0
    reply: int = 0
    title: str = ""
    href: str = ""
    post_id: str = ""
    post_type: str = ""
    notice_type: str = ""
    pub_time: str = ""


class _GubaListParser(HTMLParser):
    """解析股吧列表页（资讯/公告）。"""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict[str, Any]] = []

        self._in_row = False
        self._row_depth = 0
        self._row: _Row | None = None
        self._field: str = ""
        self._in_title_a = False

    def _class_has(self, attrs: list[tuple[str, str | None]], key: str) -> bool:
        for k, v in attrs:
            if k == "class" and v:
                parts = v.split()
                if key in parts:
                    return True
        return False

    def _get_attr(self, attrs: list[tuple[str, str | None]], key: str) -> str:
        for k, v in attrs:
            if k == key:
                return v or ""
        return ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr" and self._class_has(attrs, "listitem"):
            self._in_row = True
            self._row_depth = 1
            self._row = _Row()
            return

        if not self._in_row or self._row is None:
            return

        if tag == "tr":
            self._row_depth += 1

        if tag == "div":
            if self._class_has(attrs, "read"):
                self._field = "read"
            elif self._class_has(attrs, "reply"):
                self._field = "reply"
            elif self._class_has(attrs, "notice_type"):
                self._field = "notice_type"
            elif self._class_has(attrs, "pub_time") or self._class_has(attrs, "update"):
                self._field = "pub_time"

        if tag == "a" and self._class_has(attrs, "title"):
            # 页面结构里 title class 在 div 上，a 无 class，这里兜底
            self._in_title_a = True

        if tag == "a":
            href = self._get_attr(attrs, "href")
            data_post_id = self._get_attr(attrs, "data-postid")
            data_post_type = self._get_attr(attrs, "data-posttype")
            if href and data_post_id:
                self._in_title_a = True
                self._row.href = href
                self._row.post_id = data_post_id
                self._row.post_type = data_post_type

    def handle_endtag(self, tag: str) -> None:
        if not self._in_row:
            return

        if tag == "a":
            self._in_title_a = False

        if tag == "tr":
            self._row_depth -= 1
            if self._row_depth <= 0 and self._row is not None:
                if self._row.post_id and self._row.title:
                    item = {
                        "post_id": self._row.post_id,
                        "title": self._row.title,
                        "href": self._row.href,
                        "url": self._normalize_url(self._row.href),
                        "post_type": self._row.post_type,
                        "read": self._row.read,
                        "reply": self._row.reply,
                        "notice_type": self._row.notice_type,
                        "pub_time": self._row.pub_time,
                    }
                    self.rows.append(item)
                self._in_row = False
                self._row = None
                self._field = ""

    def handle_data(self, data: str) -> None:
        if not self._in_row or self._row is None:
            return

        text = data.strip()
        if not text:
            return

        if self._in_title_a and not self._row.title:
            self._row.title = text
            return

        if self._field == "read":
            try:
                self._row.read = int(text)
            except ValueError:
                pass
        elif self._field == "reply":
            try:
                self._row.reply = int(text)
            except ValueError:
                pass
        elif self._field == "notice_type":
            self._row.notice_type = text
        elif self._field == "pub_time":
            # list 页面时间通常形如 "02-19 10:24" 或 "10-31 07:41"
            self._row.pub_time = text

    def _normalize_url(self, href: str) -> str:
        if href.startswith("http://") or href.startswith("https://"):
            return href
        return f"{_GUBA_BASE}{href}"


def _parse_mmdd_hhmm(text: str, now: datetime) -> datetime | None:
    """解析 'MM-DD HH:MM'，推断年份。"""
    s = text.strip()
    if len(s) < 11:
        return None
    try:
        month = int(s[0:2])
        day = int(s[3:5])
        hour = int(s[6:8])
        minute = int(s[9:11])
    except ValueError:
        return None

    dt = datetime(now.year, month, day, hour, minute)
    # 若推断后日期明显在未来，视为上一年
    if dt - now > timedelta(days=1):
        dt = datetime(now.year - 1, month, day, hour, minute)
    return dt


def fetch_latest_posts(code: str, limit: int = 36) -> list[dict[str, Any]]:
    """抓取最新帖子列表（JSONP）。"""
    cache_key = f"em_guba_latest_{code}_{limit}_{datetime.now().strftime('%Y-%m-%d')}"
    cached = cache_get("eastmoney", cache_key)
    if isinstance(cached, list):
        return cached
    url = _GBAPI_LIST_URL.format(code=code, ps=limit, callback="jsonp_cb")
    payload = _http_text(url)
    data = _parse_jsonp(payload)

    items = data.get("re") or []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        post_id = str(item.get("post_id") or "")
        if not post_id:
            continue
        out.append(
            {
                "post_id": post_id,
                "post_title": item.get("post_title") or "",
                "stockbar_code": item.get("stockbar_code") or "",
                "stockbar_name": item.get("stockbar_name") or "",
                "post_publish_time": item.get("post_publish_time") or "",
                "post_last_time": item.get("post_last_time") or "",
                "post_type": item.get("post_type"),
                "post_click_count": item.get("post_click_count"),
                "post_comment_count": item.get("post_comment_count"),
                "url": _GUBA_NEWS_URL.format(code=code, post_id=post_id),
            }
        )
    cache_set("eastmoney", cache_key, out, ttl_seconds=1800)
    return out


def fetch_post_detail(code: str, post_id: str) -> dict[str, Any]:
    """抓取帖子正文详情。"""
    cache_key = f"em_guba_post_{code}_{post_id}_{datetime.now().strftime('%Y-%m-%d')}"
    cached = cache_get("eastmoney", cache_key)
    if isinstance(cached, dict):
        return cached
    url = _GUBA_NEWS_URL.format(code=code, post_id=post_id)
    page = _http_text(url, headers={"Accept": "text/html,application/xhtml+xml"})

    # 正文页内嵌：var post_article={...}
    article = _extract_js_object(page, "var post_article=")
    content_html = article.get("post_content") or ""

    result = {
        "post_id": str(article.get("post_id") or post_id),
        "post_title": article.get("post_title") or "",
        "post_publish_time": article.get("post_publish_time") or "",
        "post_last_time": article.get("post_last_time") or "",
        "post_abstract": article.get("post_abstract") or "",
        "post_ip_address": article.get("post_ip_address") or "",
        "post_like_count": article.get("post_like_count"),
        "post_comment_count": article.get("post_comment_count"),
        "post_click_count": article.get("post_click_count"),
        "post_content_html": content_html,
        "post_content_text": _html_to_text(content_html) if content_html else "",
        "url": url,
    }
    cache_set("eastmoney", cache_key, result, ttl_seconds=1800)
    return result


def fetch_stock_info_list(code: str) -> list[dict[str, Any]]:
    """抓取股票资讯列表（tab=1）。"""
    cache_key = f"em_guba_info_{code}_{datetime.now().strftime('%Y-%m-%d')}"
    cached = cache_get("eastmoney", cache_key)
    if isinstance(cached, list):
        return cached
    url = _GUBA_LIST_URL.format(code=code, tab=1)
    html = _http_text(url, headers={"Accept": "text/html,application/xhtml+xml"})
    parser = _GubaListParser()
    parser.feed(html)
    parser.close()
    cache_set("eastmoney", cache_key, parser.rows, ttl_seconds=1800)
    return parser.rows


def fetch_stock_notice_list(code: str, recent_days: int = 3) -> list[dict[str, Any]]:
    """抓取股票公告列表（tab=3），并按近 N 天过滤。"""
    cache_key = f"em_guba_notice_{code}_{recent_days}_{datetime.now().strftime('%Y-%m-%d')}"
    cached = cache_get("eastmoney", cache_key)
    if isinstance(cached, list):
        return cached
    url = _GUBA_LIST_URL.format(code=code, tab=3)
    html = _http_text(url, headers={"Accept": "text/html,application/xhtml+xml"})
    parser = _GubaListParser()
    parser.feed(html)
    parser.close()

    now = datetime.now()
    threshold = now - timedelta(days=recent_days)

    out: list[dict[str, Any]] = []
    for row in parser.rows:
        dt = _parse_mmdd_hhmm(row.get("pub_time") or "", now)
        if dt is None:
            continue
        if dt >= threshold:
            row2 = dict(row)
            row2["pub_datetime"] = dt.strftime("%Y-%m-%d %H:%M")
            out.append(row2)

    out.sort(key=lambda x: x.get("pub_datetime", ""), reverse=True)
    cache_set("eastmoney", cache_key, out, ttl_seconds=1800)
    return out


def fetch_stock_deep_research_inputs(code: str, notice_days: int = 3, post_limit: int = 36) -> dict[str, Any]:
    """聚合抓取：帖子列表 + 资讯 + 近N天公告。"""
    cache_key = (
        f"em_guba_deep_{code}_{notice_days}_{post_limit}_{datetime.now().strftime('%Y-%m-%d')}"
    )
    cached = cache_get("eastmoney", cache_key)
    if isinstance(cached, dict):
        return cached
    posts = fetch_latest_posts(code, limit=post_limit)
    infos = fetch_stock_info_list(code)
    notices = fetch_stock_notice_list(code, recent_days=notice_days)
    result = {
        "code": code,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latest_posts": posts,
        "stock_infos": infos,
        "stock_notices_recent": notices,
    }
    cache_set("eastmoney", cache_key, result, ttl_seconds=1800)
    return result
