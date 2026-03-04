"""东方财富股吧数据抓取模块。

说明
----
- 使用 Scrapling Fetcher（curl_cffi 后端），提供 TLS 指纹模拟和自动反爬能力
- 使用 CSS/XPath 选择器解析 HTML，替代 html.parser 手写解析器
- 返回结构化数据，无需额外提取

支持功能
--------
1. 最新帖子列表（gbapi JSONP）
2. 单帖正文（news 页面内嵌 post_article）
3. 股票资讯列表（list,code,1,f.html）
4. 股票公告列表（list,code,3,f.html，支持近 N 天过滤）
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from html import unescape
from typing import Any

from ashare_data.core.cache import cache_get, cache_set
from ashare_data.core.http_client import http_text
from ashare_data.core.scraper import parse_html

logger = logging.getLogger(__name__)


_GBAPI_LIST_URL = (
    "https://gbapi.eastmoney.com/webarticlelist/api/Article/Articlelist"
    "?code={code}&sorttype=1&ps={ps}&from=CommonBaPost"
    "&deviceid=quoteweb&version=200&product=Guba&plat=Web&needzd=true"
    "&callback={callback}"
)

_GUBA_NEWS_URL = "https://guba.eastmoney.com/news,{code},{post_id}.html"
_GUBA_LIST_URL = "https://guba.eastmoney.com/list,{code},{tab},f.html"
_GUBA_BASE = "https://guba.eastmoney.com"


def _http_text(url: str, timeout: float = 15.0, headers: dict[str, str] | None = None) -> str:
    """获取文本并缓存。"""
    cache_key = f"em_guba_text|{datetime.now().strftime('%Y-%m-%d')}|{url}"
    cached = cache_get("eastmoney", cache_key)
    if isinstance(cached, str):
        return cached
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://guba.eastmoney.com/",
    }
    if headers:
        req_headers.update(headers)
    text = http_text(url, headers=req_headers, timeout=timeout)
    ttl = 1800
    cache_set("eastmoney", cache_key, text, ttl_seconds=ttl)
    return text


def _parse_jsonp(payload: str) -> dict[str, Any]:
    """解析 JSONP 为 dict。"""
    left = payload.find("(")
    right = payload.rfind(")")
    if left == -1 or right == -1 or left >= right:
        raise ValueError("invalid JSONP payload")
    inner = payload[left + 1 : right]
    return json.loads(inner)


def _html_to_text(html_fragment: str) -> str:
    """提取 HTML 片段中的纯文本。"""
    if not html_fragment:
        return ""
    try:
        resp = parse_html(html_fragment, url="")

        # 跳过 script/style，收集文本
        text_parts: list[str] = []
        for el in resp.below_elements:
            tag = el.tag.lower()
            if tag in ("script", "style"):
                continue
            text = el.text.clean() if el.text else ""
            if text:
                text_parts.append(text)
            if tag in ("br", "p", "div", "li", "tr"):
                text_parts.append("\n")

        merged = " ".join(p if p != "\n" else "\n" for p in text_parts)
        lines = [" ".join(line.split()) for line in merged.splitlines()]
        lines = [l for l in lines if l]
        return unescape("\n".join(lines))
    except Exception:
        return unescape(html_fragment.strip())


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


class _GubaListParser:
    """解析股吧列表页（资讯/公告）（Scrapling）。"""

    def __init__(self, html: str):
        self.rows: list[dict[str, Any]] = []
        self._parse(html)

    def _parse(self, html: str) -> None:
        """使用 Scrapling Response 解析 HTML。"""
        try:
            resp = parse_html(html, url="")

            # 查找所有 tr.listitem
            items = resp.css("tr.listitem")
            for item in items:
                row = self._parse_row(item)
                if row and row.post_id and row.title:
                    self.rows.append({
                        "post_id": row.post_id,
                        "title": row.title,
                        "href": row.href,
                        "url": self._normalize_url(row.href),
                        "post_type": row.post_type,
                        "read": row.read,
                        "reply": row.reply,
                        "notice_type": row.notice_type,
                        "pub_time": row.pub_time,
                    })
        except Exception as e:
            logger.exception("列表页解析失败：%s", e)

    def _parse_row(self, item: Any) -> _Row:
        """解析单个行。"""
        row = _Row()

        # 阅读数：<div class="read">
        read_div = item.css("div.read")
        if read_div:
            text = read_div.first.text if read_div.first else ""
            try:
                row.read = int(text.replace(",", "").strip())
            except ValueError:
                pass

        # 回复数：<div class="reply">
        reply_div = item.css("div.reply")
        if reply_div:
            text = reply_div.first.text if reply_div.first else ""
            try:
                row.reply = int(text.replace(",", "").strip())
            except ValueError:
                pass

        # 标题链接：<a class="title" ...>
        title_a = item.css("a.title")
        if title_a:
            link_el = title_a.first
            if link_el:
                row.href = link_el.attrib.get("href", "")
                row.title = link_el.text if link_el.text else ""

        # 其他字段
        notice_div = item.css("div.notice_type")
        if notice_div:
            row.notice_type = notice_div.first.text if notice_div.first else ""

        pub_div = item.css("div.pub_time, div.update")
        if pub_div:
            row.pub_time = pub_div.first.text if pub_div.first else ""

        return row

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


# ---------------------------------------------------------------------------
# 核心函数
# ---------------------------------------------------------------------------

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
    parser = _GubaListParser(html)
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
    parser = _GubaListParser(html)

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
    """聚合抓取：帖子列表 + 资讯 + 近 N 天公告。"""
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
