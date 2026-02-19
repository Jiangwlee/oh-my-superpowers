"""淘股吧精华帖数据抓取模块。

目标页面: https://www.tgb.cn/jinghua/1-1
纯 Python 标准库实现，使用 html.parser 解析 HTML。
"""

import http.client
import json
import logging
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.tgb.cn"
_LIST_URL = f"{_BASE_URL}/jinghua/1-1"
_QUOTES_URL = f"{_BASE_URL}/quotes/{{full_code}}"
_XGGN_URL = f"{_BASE_URL}/quotes/getXGGNStockType"
_ZH_URL = f"{_BASE_URL}/newIndex/getZh?pageNo={{page_no}}"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.tgb.cn/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


# ---------------------------------------------------------------------------
# HTTP 请求
# ---------------------------------------------------------------------------

def _fetch_html(url: str, timeout: int = 15) -> str:
    """获取页面 HTML，容忍 IncompleteRead。"""
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except http.client.IncompleteRead as e:
        raw = e.partial
    return raw.decode("utf-8", errors="replace")


def _fetch_json_get(url: str, timeout: int = 15, headers: dict | None = None) -> dict:
    """GET 请求并解析 JSON。"""
    req_headers = dict(_HEADERS)
    req_headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
    req_headers["X-Requested-With"] = "XMLHttpRequest"
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8", errors="replace"))


def _fetch_json_post_form(url: str, form: dict, timeout: int = 15, headers: dict | None = None) -> dict:
    """POST form 请求并解析 JSON。"""
    req_headers = dict(_HEADERS)
    req_headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
    req_headers["X-Requested-With"] = "XMLHttpRequest"
    req_headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    if headers:
        req_headers.update(headers)

    data = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8", errors="replace"))


# ---------------------------------------------------------------------------
# 列表页解析器
# ---------------------------------------------------------------------------

class _ListPageParser(HTMLParser):
    """解析淘股吧精华帖列表页。

    页面结构 (每条帖子):
        <div class="Nbbs-tiezi-lists">
            <div class="left middle-list-tittle ...">
                <a class="overhide mw300" href="a/xxx" title="标题">...</a>
                <span>&nbsp;(评论数)</span>
            </div>
            <div class="left middle-list-talk ...">回复 / 浏览</div>
            <div class="left middle-list-reply">回帖日期</div>
            <div class="left middle-list-user ...">
                <a class="mw100 overhide" ...>作者</a>
            </div>
            <div class="left middle-list-post">发帖日期</div>
        </div>
    """

    def __init__(self) -> None:
        super().__init__()
        self.posts: list[dict] = []

        # 状态跟踪
        self._in_item = False          # 在 Nbbs-tiezi-lists 内
        self._in_title_link = False    # 在标题 <a> 内
        self._in_reply_span = False    # 在评论数 <span> 内
        self._in_talk_div = False      # 在 middle-list-talk 内
        self._in_author_link = False   # 在作者 <a> 内
        self._in_post_date = False     # 在 middle-list-post 内

        self._current: dict = {}
        self._depth = 0                # div 嵌套深度追踪

    def _class_contains(self, attrs: list[tuple[str, str | None]], cls: str) -> bool:
        for name, val in attrs:
            if name == "class" and val and cls in val:
                return True
        return False

    def _get_attr(self, attrs: list[tuple[str, str | None]], key: str) -> str:
        for name, val in attrs:
            if name == key:
                return val or ""
        return ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div" and self._class_contains(attrs, "Nbbs-tiezi-lists"):
            self._in_item = True
            self._depth = 1
            self._current = {
                "title": "", "url": "", "author": "",
                "date": "", "view_count": 0, "reply_count": 0,
            }
            return

        if not self._in_item:
            return

        if tag == "div":
            self._depth += 1

        # 标题链接: <a class="overhide mw300" href="...">
        if tag == "a" and self._class_contains(attrs, "mw300"):
            self._in_title_link = True
            href = self._get_attr(attrs, "href")
            title = self._get_attr(attrs, "title")
            if title:
                self._current["title"] = title
            if href:
                if href.startswith("http"):
                    self._current["url"] = href
                else:
                    self._current["url"] = f"{_BASE_URL}/{href.lstrip('/')}"
            return

        # 评论数 span (紧跟标题链接后面)
        if tag == "span" and not self._in_title_link and self._current.get("url") and not self._current.get("reply_count"):
            self._in_reply_span = True
            return

        # 浏览/回复数: <div class="... middle-list-talk ...">
        if tag == "div" and self._class_contains(attrs, "middle-list-talk"):
            self._in_talk_div = True
            return

        # 作者链接: <a class="mw100 overhide" ...>
        if tag == "a" and self._class_contains(attrs, "mw100"):
            self._in_author_link = True
            return

        # 发帖日期: <div class="... middle-list-post">
        if tag == "div" and self._class_contains(attrs, "middle-list-post"):
            self._in_post_date = True
            return

    def handle_endtag(self, tag: str) -> None:
        if not self._in_item:
            return

        if tag == "a":
            self._in_title_link = False
            self._in_author_link = False

        if tag == "span":
            self._in_reply_span = False

        if tag == "div":
            self._depth -= 1
            self._in_talk_div = False
            self._in_post_date = False
            # 当 item div 关闭
            if self._depth <= 0:
                self._in_item = False
                if self._current.get("title") and self._current.get("url"):
                    # 清理标题
                    title = self._current["title"]
                    for tag_str in ("[精]", "[红包]", "[投票]"):
                        title = title.replace(tag_str, "")
                    self._current["title"] = title.strip()
                    self.posts.append(self._current)
                self._current = {}

    def handle_data(self, data: str) -> None:
        if not self._in_item:
            return

        text = data.strip()
        if not text:
            return

        if self._in_title_link:
            # title 已经从 attr 获取，跳过
            return

        if self._in_reply_span:
            # 格式: "&nbsp;(12345)"
            cleaned = text.replace("\xa0", "").strip()
            if cleaned.startswith("(") and cleaned.endswith(")"):
                try:
                    self._current["reply_count"] = int(cleaned[1:-1])
                except ValueError:
                    pass
            self._in_reply_span = False
            return

        if self._in_talk_div:
            # 格式: "106 / 9616"
            if "/" in text:
                parts = text.split("/")
                if len(parts) == 2:
                    try:
                        self._current["view_count"] = int(parts[1].strip())
                    except ValueError:
                        pass
            self._in_talk_div = False
            return

        if self._in_author_link:
            self._current["author"] = text
            self._in_author_link = False
            return

        if self._in_post_date:
            self._current["date"] = text
            self._in_post_date = False
            return


# ---------------------------------------------------------------------------
# 详情页解析器
# ---------------------------------------------------------------------------

class _DetailPageParser(HTMLParser):
    """解析淘股吧帖子详情页，提取正文文本。

    正文在 <div class="article-text p_coten" id="first"> 内。
    """

    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []

        self._in_content = False
        self._depth = 0
        self._skip_tags = {"script", "style", "img"}
        self._skip_depth = 0

    def _class_contains(self, attrs: list[tuple[str, str | None]], cls: str) -> bool:
        for name, val in attrs:
            if name == "class" and val and cls in val:
                return True
        return False

    def _get_attr(self, attrs: list[tuple[str, str | None]], key: str) -> str:
        for name, val in attrs:
            if name == key:
                return val or ""
        return ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # 进入正文区域: <div class="article-text p_coten" id="first">
        if tag == "div" and self._get_attr(attrs, "id") == "first" and self._class_contains(attrs, "article-text"):
            self._in_content = True
            self._depth = 1
            return

        if not self._in_content:
            return

        if tag == "div":
            self._depth += 1

        # 跳过脚本和样式
        if tag in self._skip_tags:
            self._skip_depth += 1

        # br 标签当作换行
        if tag == "br":
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self._in_content:
            return

        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1

        if tag == "div":
            self._depth -= 1
            if self._depth <= 0:
                self._in_content = False

    def handle_data(self, data: str) -> None:
        if not self._in_content or self._skip_depth > 0:
            return
        text = data.strip()
        if text and text != "[淘股吧]":
            self.text_parts.append(text)

    def get_text(self, max_len: int = 500) -> str:
        content = " ".join(self.text_parts)
        # 合并多余空白
        while "  " in content:
            content = content.replace("  ", " ")
        content = content.strip()
        if len(content) > max_len:
            content = content[:max_len]
        return content


class _HtmlFragmentTextParser(HTMLParser):
    """提取 HTML 片段中的纯文本。"""

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
        if tag in {"br", "p", "div", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if self._skip_depth > 0:
            return
        if tag in {"p", "div", "li"}:
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


def _strip_html_fragment(html_text: str, max_len: int = 500) -> str:
    parser = _HtmlFragmentTextParser()
    parser.feed(html_text or "")
    parser.close()
    text = parser.to_text()
    if len(text) > max_len:
        text = text[:max_len]
    return text


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


# ---------------------------------------------------------------------------
# 详情页获取
# ---------------------------------------------------------------------------

def _fetch_detail(url: str) -> str:
    """获取单个帖子详情页的正文摘要。"""
    try:
        html = _fetch_html(url, timeout=15)
        parser = _DetailPageParser()
        parser.feed(html)
        return parser.get_text(500)
    except Exception as e:
        logger.debug("获取详情页失败 %s: %s", url, e)
        return ""


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
        parser = _ListPageParser()
        parser.feed(html)
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
        logger.exception("fetch_taoguba_hot 出错: %s", e)
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
        logger.exception("fetch_taoguba_stock_tags 出错: %s", e)
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
                # 接口常见格式: 2026-02-19T15:17:28.000+08:00
                post_time = item.get("actionDate")

            posts.append(
                {
                    "topic_id": str(topic_id or ""),
                    "new_topic_id": str(new_topic_id or ""),
                    "user_name": item.get("userName") or "",
                    "subject": item.get("subject") or "",
                    "summary": _strip_html_fragment(body, max_len=500),
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
        logger.exception("fetch_taoguba_quotes_posts 出错: %s", e)
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
        logger.exception("fetch_taoguba_zh_recommend 出错: %s", e)
        return []
