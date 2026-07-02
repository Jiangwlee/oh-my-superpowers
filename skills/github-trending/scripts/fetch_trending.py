#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""抓取 GitHub Trending 页面并用 GitHub API 补全仓库详情，输出 JSON。

数据流：scrape github.com/trending（无官方 API）→ 解析仓库列表 →
逐仓库调用 GitHub REST API（优先 gh CLI，未登录时降级匿名 curl）→
附带 README 摘要 → 输出结构化 JSON 供 Agent 撰写点评与渲染报告。
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from html.parser import HTMLParser

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("github-trending")

TIMEOUT = 120
Repo = dict[str, object]


class TrendingParser(HTMLParser):
    """从 trending 页面 HTML 提取仓库行（article.Box-row）。"""

    def __init__(self) -> None:
        super().__init__()
        self.repos: list[Repo] = []
        self.cur: Repo | None = None
        self.in_article = False
        self.in_desc = False
        self.data_target = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        cls = a.get("class", "")
        if tag == "article" and "Box-row" in cls:
            self.in_article = True
            self.cur = {"name": "", "desc": "", "lang": "", "stars_today": ""}
        if not self.in_article or self.cur is None:
            return
        href = a.get("href", "")
        if (
            tag == "a"
            and not self.cur["name"]
            and href.count("/") == 2
            and not href.startswith(("/login", "/sponsors", "/trending"))
            and cls.startswith("Link")
        ):
            self.cur["name"] = href.strip("/")
        if tag == "p" and "col-9" in cls:
            self.in_desc = True
        if tag == "span" and a.get("itemprop") == "programmingLanguage":
            self.data_target = "lang"
        if tag == "span" and "float-sm-right" in cls:
            self.data_target = "stars_today"

    def handle_data(self, data: str) -> None:
        if not self.in_article or self.cur is None:
            return
        if self.in_desc:
            self.cur["desc"] = f"{self.cur['desc']}{data.strip()} "
        if self.data_target:
            self.cur[self.data_target] = f"{self.cur[self.data_target]}{data.strip()}".strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "p":
            self.in_desc = False
        if tag == "span":
            self.data_target = ""
        if tag == "article" and self.in_article:
            self.in_article = False
            if self.cur and self.cur["name"]:
                self.cur["desc"] = str(self.cur["desc"]).strip()
                self.repos.append(self.cur)
            self.cur = None


def _curl(url: str, *headers: str) -> str:
    """用 curl 抓取 URL，失败返回空串。"""
    cmd = ["curl", "-sL", "--max-time", str(TIMEOUT)]
    for h in headers:
        cmd += ["-H", h]
    cmd.append(url)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT + 5).stdout
    except Exception:
        logger.exception("curl failed: %s", url)
        return ""


def _gh_authed() -> bool:
    """检查 gh CLI 是否已登录。"""
    try:
        return subprocess.run(["gh", "auth", "status"], capture_output=True, timeout=10).returncode == 0
    except Exception:
        return False


def _api_json(path: str, use_gh: bool, raw: bool = False) -> str:
    """调用 GitHub REST API，返回原始响应文本。"""
    if use_gh:
        cmd = ["gh", "api", path]
        if raw:
            cmd += ["-H", "Accept: application/vnd.github.raw+json"]
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT).stdout
        except Exception:
            logger.exception("gh api failed: %s", path)
            return ""
    headers = ["Accept: application/vnd.github.raw+json"] if raw else []
    return _curl(f"https://api.github.com/{path}", *headers)


def fetch_trending(since: str, lang: str) -> list[Repo]:
    """抓取并解析 trending 页面。

    Args:
        since: daily / weekly / monthly。
        lang: 语言过滤，空串为全部。

    Returns:
        仓库列表，出错时返回空列表。
    """
    url = f"https://github.com/trending/{lang}?since={since}" if lang else f"https://github.com/trending?since={since}"
    page = _curl(url)
    if not page:
        return []
    parser = TrendingParser()
    parser.feed(page)
    return parser.repos


def enrich(repos: list[Repo], readme_chars: int) -> list[Repo]:
    """用 GitHub API 补全仓库详情和 README 摘要。"""
    use_gh = _gh_authed()
    if not use_gh:
        logger.info("gh 未登录，降级为匿名 GitHub API（限额 60 次/小时）")
    for r in repos:
        name = r["name"]
        try:
            info = json.loads(_api_json(f"repos/{name}", use_gh) or "{}")
        except json.JSONDecodeError:
            info = {}
        if "stargazers_count" not in info:
            r["error"] = info.get("message", "api request failed")
            logger.warning("enrich failed: %s (%s)", name, r["error"])
            continue
        r.update(
            {
                "stars": info.get("stargazers_count", 0),
                "forks": info.get("forks_count", 0),
                "full_desc": info.get("description") or r["desc"],
                "topics": info.get("topics", []),
                "license": (info.get("license") or {}).get("spdx_id") or "",
                "created_at": str(info.get("created_at", ""))[:10],
                "pushed_at": str(info.get("pushed_at", ""))[:10],
                "homepage": info.get("homepage") or "",
                "open_issues": info.get("open_issues_count", 0),
            }
        )
        if readme_chars > 0:
            r["readme"] = _api_json(f"repos/{name}/readme", use_gh, raw=True)[:readme_chars]
        logger.info("enriched %s (★%s)", name, r.get("stars"))
    return repos


def main() -> int:
    """CLI 入口。"""
    ap = argparse.ArgumentParser(description="Fetch GitHub trending repos as enriched JSON.")
    ap.add_argument("--since", choices=["daily", "weekly", "monthly"], default="daily")
    ap.add_argument("--lang", default="", help="语言过滤，如 python；默认全部")
    ap.add_argument("--readme-chars", type=int, default=4000, help="README 摘要长度，0 表示不抓取")
    ap.add_argument("--out", default="", help="输出文件路径；默认 stdout")
    args = ap.parse_args()

    repos = fetch_trending(args.since, args.lang)
    if not repos:
        logger.error("未能解析到任何 trending 仓库；检查网络或 GitHub 页面结构变化")
        return 1
    repos = enrich(repos, args.readme_chars)
    payload = json.dumps(repos, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        logger.info("written %d repos -> %s", len(repos), args.out)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
