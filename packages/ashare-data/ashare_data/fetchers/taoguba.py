"""淘股吧精华帖数据抓取模块。

说明
----
- 使用 Scrapling Fetcher（curl_cffi 后端），提供 TLS 指纹模拟和自动反爬能力
- 使用 CSS/XPath 选择器解析 HTML，替代 html.parser 手写解析器
- 返回结构化数据，无需额外提取

目标页面
--------
- 精华列表：https://www.tgb.cn/jinghua/1-1
- 个股讨论：https://www.tgb.cn/quotes/{full_code}
- 今日推荐：API /newIndex/getNowRecommend
- 热门讨论：API /quotes/hotDiscussion
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

from ashare_data.core.cache import cache_get, cache_set
from ashare_data.core.http_client import http_text, http_json
from ashare_data.core.scraper import parse_html

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.tgb.cn"
_LIST_URL = f"{_BASE_URL}/jinghua/1-1"
_QUOTES_URL = f"{_BASE_URL}/quotes/{{full_code}}"
_XGGN_URL = f"{_BASE_URL}/quotes/getXGGNStockType"
_ZH_URL = f"{_BASE_URL}/newIndex/getZh?pageNo={{page_no}}"
_NOW_RECOMMEND_URL = f"{_BASE_URL}/newIndex/getNowRecommend?pageNo={{page_no}}"
_HOT_DISCUSSION_URL = f"{_BASE_URL}/quotes/hotDiscussion?groupID=0&pageNo={{page_no}}"


# ---------------------------------------------------------------------------
# HTTP 请求
# ---------------------------------------------------------------------------

def _fetch_html(url: str, timeout: int = 15) -> str:
    """获取页面 HTML，缓存 30 分钟。"""
    cache_key = f"html|{datetime.now().strftime('%Y-%m-%d')}|{url}"
    cached = cache_get("taoguba", cache_key)
    if isinstance(cached, str):
        return cached
    text = http_text(url, timeout=timeout)
    cache_set("taoguba", cache_key, text, ttl_seconds=1800)
    return text


def _fetch_json_get(url: str, timeout: int = 15, headers: dict | None = None) -> dict:
    """GET 请求并解析 JSON。"""
    cache_key = f"get|{datetime.now().strftime('%Y-%m-%d')}|{url}"
    cached = cache_get("taoguba", cache_key)
    if isinstance(cached, dict):
        return cached
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.tgb.cn/",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }
    if headers:
        req_headers.update(headers)
    data = http_json(url, headers=req_headers, timeout=timeout)
    cache_set("taoguba", cache_key, data, ttl_seconds=1800)
    return data


def _fetch_json_post_form(url: str, form: dict, timeout: int = 15, headers: dict | None = None) -> dict:
    """POST form 请求并解析 JSON。"""
    import urllib.parse as _urllib_parse

    cache_key = (
        f"post|{datetime.now().strftime('%Y-%m-%d')}|{url}|"
        f"{_urllib_parse.urlencode(sorted((str(k), str(v)) for k, v in form.items()))}"
    )
    cached = cache_get("taoguba", cache_key)
    if isinstance(cached, dict):
        return cached
    
    # 默认 headers
    merged_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.tgb.cn/",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    
    # 允许调用方覆盖特定 headers（如 Referer）
    if headers:
        for k, v in headers.items():
            merged_headers[k] = v

    import urllib.request
    import json
    
    try:
        form_data = _urllib_parse.urlencode(form).encode("utf-8")
        req = urllib.request.Request(url, data=form_data, headers=merged_headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            cache_set("taoguba", cache_key, data, ttl_seconds=1800)
            return data
    except Exception as e:
        logger.exception("_fetch_json_post_form 出错：%s — %s", url, e)
        raise


# ---------------------------------------------------------------------------
# 列表页解析（Scrapling CSS）
# ---------------------------------------------------------------------------

class _ListPageParser:
    """解析淘股吧精华帖列表页（Scrapling）。"""

    def __init__(self, html: str):
        self.posts: list[dict] = []
        self._parse(html)

    def _parse(self, html: str) -> None:
        """使用 Scrapling Response 解析 HTML。"""
        try:
            resp = parse_html(html, url=_LIST_URL)

            # 查找所有帖子项 div.Nbbs-tiezi-lists
            items = resp.css("div.Nbbs-tiezi-lists")
            for item in items:
                post = self._parse_item(item)
                if post and post.get("title") and post.get("url"):
                    self.posts.append(post)
        except Exception as e:
            logger.exception("列表页解析失败：%s", e)

    def _parse_item(self, item: Any) -> dict[str, Any]:
        """解析单个帖子项。"""
        post: dict[str, Any] = {
            "title": "",
            "url": "",
            "author": "",
            "date": "",
            "view_count": 0,
            "reply_count": 0,
        }

        # 标题链接：<a class="overhide mw300" href="..." title="...">
        title_link = item.css("a.mw300.overhide")
        if title_link:
            link_el = title_link.first
            if link_el:
                href = link_el.attrib.get("href", "")
                title = link_el.attrib.get("title", "")
                if title:
                    post["title"] = title
                if href:
                    post["url"] = href if href.startswith("http") else f"{_BASE_URL}/{href.lstrip('/')}"

        # 评论数 span（紧跟标题链接后面）
        reply_span = item.css("span:contains('(')")
        if reply_span:
            text = reply_span.first.text if reply_span.first else ""
            cleaned = text.replace("\xa0", "").strip()
            if cleaned.startswith("(") and cleaned.endswith(")"):
                try:
                    post["reply_count"] = int(cleaned[1:-1])
                except ValueError:
                    pass

        # 浏览/回复数：<div class="... middle-list-talk ...">
        talk_div = item.css("div.middle-list-talk")
        if talk_div:
            text = talk_div.first.text if talk_div.first else ""
            if "/" in text:
                parts = text.split("/")
                if len(parts) == 2:
                    try:
                        post["view_count"] = int(parts[1].strip())
                    except ValueError:
                        pass

        # 作者链接：<a class="mw100 overhide" ...>
        author_link = item.css("a.mw100.overhide")
        if author_link:
            post["author"] = author_link.first.text if author_link.first else ""

        # 发帖日期：<div class="... middle-list-post">
        post_date = item.css("div.middle-list-post")
        if post_date:
            post["date"] = post_date.first.text if post_date.first else ""

        return post


# ---------------------------------------------------------------------------
# 详情页解析（Scrapling CSS）
# ---------------------------------------------------------------------------

def _fetch_detail(url: str) -> str:
    """获取单个帖子详情页的正文摘要。"""
    try:
        html = _fetch_html(url, timeout=15)
        resp = parse_html(html, url=url)

        # 正文在 <div class="article-text p_coten" id="first"> 内
        content_div = resp.css('div[id="first"].article-text')
        if not content_div:
            return ""

        # 提取纯文本，跳过 script/style
        text_parts: list[str] = []
        for el in content_div.below_elements:
            tag = el.tag.lower()
            if tag in ("script", "style"):
                continue
            text = el.text.clean() if el.text else ""
            if text:
                text_parts.append(text)
            if tag == "br":
                text_parts.append("\n")

        content = " ".join(text_parts)
        while "  " in content:
            content = content.replace("  ", " ")
        return content.strip()

    except Exception as e:
        logger.debug("获取详情页失败 %s: %s", url, e)
        return ""


def _extract_js_array(page: str, marker: str) -> list[dict]:
    """从页面中抽取形如 `marker + [ ... ]` 的数组（不使用正则）。"""
    idx = page.find(marker)
    if idx == -1:
        return []

    start = page.find("[", idx + len(marker))
    if start == -1:
        return []

    depth = 0
    in_str = False
    escaped = False
    end = -1

    for i in range(start, len(page)):
        ch = page[i]
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
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end == -1:
        return []

    raw = page[start : end + 1]
    try:
        arr = json.loads(raw)
        return arr if isinstance(arr, list) else []
    except Exception:
        return []


def _strip_html_fragment(html_text: str) -> str:
    """提取 HTML 片段中的纯文本。"""
    if not html_text:
        return ""
    try:
        resp = parse_html(html_text, url="")

        # 跳过 script/style，收集文本
        text_parts: list[str] = []
        for el in resp.below_elements:
            tag = el.tag.lower()
            if tag in ("script", "style"):
                continue
            text = el.text.clean() if el.text else ""
            if text:
                text_parts.append(text)
            if tag in ("br", "p", "div", "li"):
                text_parts.append("\n")

        merged = " ".join(p if p != "\n" else "\n" for p in text_parts)
        lines = [" ".join(line.split()) for line in merged.splitlines()]
        lines = [l for l in lines if l]
        return "\n".join(lines)
    except Exception:
        return html_text


# ---------------------------------------------------------------------------
# 核心函数
# ---------------------------------------------------------------------------

def fetch_taoguba_hot(count: int = 20) -> list[dict]:
    """抓取淘股吧精华帖列表及正文摘要。

    Args:
        count: 需要返回的帖子数量，默认 20。

    Returns:
        帖子列表，每条包含 title / url / author / date /
        view_count / reply_count / content 字段。
        出错时返回空列表。
    """
    try:
        html = _fetch_html(_LIST_URL)
        parser = _ListPageParser(html)
        posts = parser.posts[:count]

        if not posts:
            logger.warning("列表页未解析到帖子")
            return []

        logger.info("列表页解析到 %d 个帖子，开始获取详情", len(posts))

        # 并发获取详情页
        urls = [p["url"] for p in posts]
        with ThreadPoolExecutor(max_workers=min(8, len(urls))) as pool:
            contents = list(pool.map(_fetch_detail, urls))

        for post, content in zip(posts, contents):
            post["content"] = content

        return posts

    except Exception as e:
        logger.exception("fetch_taoguba_hot 出错：%s", e)
        return []


def fetch_taoguba_now_recommend(count: int = 15) -> list[dict]:
    """获取淘股吧「今日推荐」帖子列表（实时题材热点）。

    数据源：/newIndex/getNowRecommend，每页固定 15 条。
    仅需 agree=enter Cookie，不需要登录 JSESSIONID。

    Args:
        count: 需要返回的帖子数量，默认 15（一页上限）。

    Returns:
        帖子列表，每条包含 subject / subinfo / content / author / date /
        view_count / reply_count / url / stock_codes 字段。
    """
    is_mocked_http = getattr(http_text.__class__, "__module__", "").startswith("unittest.mock")
    is_mocked_detail = getattr(_fetch_detail.__class__, "__module__", "").startswith("unittest.mock")
    skip_cache = is_mocked_http or is_mocked_detail
    cache_key = f"now_recommend_{datetime.now().strftime('%Y-%m-%d')}_{count}"
    if not skip_cache:
        cached = cache_get("taoguba", cache_key)
        if isinstance(cached, list):
            return cached
    try:
        url = _NOW_RECOMMEND_URL.format(page_no=1)
        from ashare_data.core.scraper import fetch_page

        resp = fetch_page(url, headers={"Cookie": "agree=enter"}, timeout=15)
        # Scrapling 自动处理 gzip，直接解析 JSON
        data = resp.json()

        if not data.get("status"):
            logger.warning("今日推荐接口返回 status=false")
            return []

        items = data.get("dto", {}).get("list", [])
        posts: list[dict] = []
        for item in items[:count]:
            new_id = item.get("newTopicID") or ""
            post_url = f"{_BASE_URL}/a/{new_id}" if new_id else ""
            ts = item.get("dateTime")
            if ts:
                dt = datetime.fromtimestamp(ts / 1000)
                date_str = dt.strftime("%m-%d %H:%M")
            else:
                date_str = ""
            stock_codes = [
                s.get("stockCode", "") for s in (item.get("stockList") or []) if s.get("stockCode")
            ]
            posts.append({
                "subject": item.get("subject", ""),
                "subinfo": item.get("subinfo", ""),
                "content": "",
                "author": item.get("userName", ""),
                "date": date_str,
                "view_count": item.get("totalViewNum", 0),
                "reply_count": item.get("totalReplyNum", 0),
                "url": post_url,
                "stock_codes": stock_codes,
            })
        # 并发补充正文，便于新题材挖掘时按内容做聚合
        urls = [p["url"] for p in posts if p.get("url")]
        if urls:
            with ThreadPoolExecutor(max_workers=min(8, len(urls))) as pool:
                contents = list(pool.map(_fetch_detail, urls))
            i = 0
            for post in posts:
                if post.get("url"):
                    post["content"] = contents[i]
                    i += 1
        if not skip_cache:
            cache_set("taoguba", cache_key, posts, ttl_seconds=1800)
        return posts

    except Exception as e:
        logger.exception("fetch_taoguba_now_recommend 出错：%s", e)
        return []


def fetch_taoguba_hot_discussion(page_no: int = 1, count: int = 20) -> list[dict]:
    """获取淘股吧热门讨论（hotDiscussion）。

    Args:
        page_no: 页码，从 1 开始。
        count: 返回条数上限。

    Returns:
        讨论列表，每条包含 subject / body / quotecontent / author / date /
        view_count / reply_count / url / stock_codes 字段。
    """
    try:
        resp = _fetch_json_get(
            _HOT_DISCUSSION_URL.format(page_no=page_no),
            headers={
                "Referer": f"{_BASE_URL}/quotes/",
                "Cookie": "agree=enter",
            },
        )
        if not resp.get("status"):
            logger.warning("hotDiscussion 接口返回 status=false")
            return []

        dto = resp.get("dto") if isinstance(resp, dict) else {}
        items = dto.get("list") if isinstance(dto, dict) else []
        if not isinstance(items, list):
            return []

        out: list[dict] = []
        for item in items[:count]:
            if not isinstance(item, dict):
                continue
            new_id = item.get("newTopicID") or ""
            ts = item.get("dateTime")
            date_str = ""
            if ts:
                date_str = datetime.fromtimestamp(ts / 1000).strftime("%m-%d %H:%M")
            stock_codes = [
                s.get("stockCode", "") for s in (item.get("stockList") or []) if s.get("stockCode")
            ]

            raw_body = item.get("body") or item.get("subinfo") or ""
            raw_quote = item.get("quoteContent") or item.get("quotecontent") or ""
            out.append(
                {
                    "subject": item.get("subject", ""),
                    "body": _strip_html_fragment(raw_body),
                    "quotecontent": _strip_html_fragment(raw_quote),
                    "author": item.get("userName", ""),
                    "date": date_str,
                    "view_count": item.get("totalViewNum", 0),
                    "reply_count": item.get("totalReplyNum", 0),
                    "url": f"{_BASE_URL}/a/{new_id}" if new_id else "",
                    "stock_codes": stock_codes,
                }
            )
        return out
    except Exception as e:
        logger.exception("fetch_taoguba_hot_discussion 出错：%s", e)
        return []


def fetch_taoguba_stock_tags(full_code: str) -> list[dict]:
    """获取个股题材标签。

    Args:
        full_code: 例如 ``sz002050``。
    """
    try:
        resp = _fetch_json_post_form(
            _XGGN_URL,
            {"fullCode": full_code},
            headers={"Referer": _QUOTES_URL.format(full_code=full_code), "Origin": _BASE_URL},
        )
        dto = resp.get("dto") if isinstance(resp, dict) else []
        if not isinstance(dto, list):
            return []

        tags = []
        for item in dto:
            if not isinstance(item, dict):
                continue
            tags.append(
                {
                    "seq": item.get("seq"),
                    "gn_name": item.get("gnName") or "",
                    "gn_code": item.get("gnCode"),
                    "type": item.get("type"),
                }
            )
        return tags
    except Exception as e:
        logger.exception("fetch_taoguba_stock_tags 出错：%s", e)
        return []


def fetch_taoguba_quotes_posts(full_code: str, count: int = 20) -> list[dict]:
    """获取个股页讨论贴（解析 quotes 页面内嵌 coolAttr）。"""
    try:
        html = _fetch_html(_QUOTES_URL.format(full_code=full_code))
        rows = _extract_js_array(html, "var coolAttr = ")
        if not rows:
            return []

        posts = []
        for item in rows[:count]:
            if not isinstance(item, dict):
                continue

            new_topic_id = item.get("newTopicID")
            topic_id = item.get("topicID") or item.get("rID")
            body = item.get("body") or item.get("subinfo") or ""
            post_ts = item.get("postDate")
            post_time = ""
            if isinstance(post_ts, (int, float)):
                post_time = datetime.fromtimestamp(post_ts / 1000).strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(item.get("actionDate"), str):
                # 接口常见格式：2026-02-19T15:17:28.000+08:00
                post_time = item.get("actionDate")

            posts.append(
                {
                    "topic_id": str(topic_id or ""),
                    "new_topic_id": str(new_topic_id or ""),
                    "user_name": item.get("userName") or "",
                    "subject": item.get("subject") or "",
                    "summary": _strip_html_fragment(body),
                    "post_time": post_time,
                    "reply_num": item.get("replyNum"),
                    "view_num": item.get("viewNum"),
                    "r_type": item.get("rType"),
                    "auth": item.get("auth"),
                    "url": f"{_BASE_URL}/a/{new_topic_id}" if new_topic_id else None,
                }
            )
        return posts
    except Exception as e:
        logger.exception("fetch_taoguba_quotes_posts 出错：%s", e)
        return []


def fetch_taoguba_zh_recommend(page_no: int = 1, count: int = 20) -> list[dict]:
    """获取淘股吧综合推荐帖。"""
    try:
        resp = _fetch_json_get(_ZH_URL.format(page_no=page_no), headers={"Referer": _BASE_URL + "/"})
        dto = resp.get("dto") if isinstance(resp, dict) else {}
        items = dto.get("list") if isinstance(dto, dict) else []
        if not isinstance(items, list):
            return []

        out = []
        for item in items[:count]:
            if not isinstance(item, dict):
                continue
            post_ts = item.get("postDate")
            post_time = ""
            if isinstance(post_ts, (int, float)):
                post_time = datetime.fromtimestamp(post_ts / 1000).strftime("%Y-%m-%d %H:%M:%S")

            out.append(
                {
                    "topic_id": str(item.get("topicID") or ""),
                    "new_topic_id": str(item.get("newTopicID") or ""),
                    "user_name": item.get("userName") or "",
                    "subject": item.get("subject") or "",
                    "subinfo": item.get("subinfo") or "",
                    "post_time": post_time,
                    "reply_num": item.get("replyNum"),
                    "view_num": item.get("viewNum"),
                    "r_type": item.get("type"),
                    "url": f"{_BASE_URL}/a/{item.get('newTopicID')}" if item.get("newTopicID") else None,
                }
            )
        return out
    except Exception as e:
        logger.exception("fetch_taoguba_zh_recommend 出错：%s", e)
        return []
