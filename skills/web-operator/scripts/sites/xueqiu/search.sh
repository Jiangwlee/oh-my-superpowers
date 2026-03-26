#!/usr/bin/env bash
# Search xueqiu.com and return discussion-post summaries from the visible page.
# Input: a query string, optional result limit, and optional target prefix.
# Output: a JSON array of search results with author, time_hint, title, summary, and url.
# Public interface: xueqiu-search.sh <query> [limit] [target_prefix].

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

usage() {
  printf 'usage: %s <query> [limit] [target_prefix]\n' "$(basename "$0")" >&2
  exit 1
}

QUERY="${1:-}"
LIMIT="${2:-10}"
TARGET="${3:-}"

[[ -n "$QUERY" ]] || usage
[[ "$LIMIT" =~ ^[0-9]+$ ]] || { printf 'limit must be an integer\n' >&2; exit 1; }
(( LIMIT > 0 )) || { printf 'limit must be greater than zero\n' >&2; exit 1; }
(( LIMIT <= 10 )) || LIMIT=10

TARGET="$(xueqiu_find_target "$TARGET")"
[[ -n "$TARGET" ]] || { printf 'no usable xueqiu.com tab found\n' >&2; exit 1; }

SEARCH_URL="https://xueqiu.com/k?q=$(url_encode "$QUERY")"
xueqiu_nav_fast "$TARGET" "$SEARCH_URL"
wait_for_url_contains "$TARGET" "xueqiu.com/k?"
wait_for_xueqiu_text "$TARGET" "讨论"
wait_for_xueqiu_selector "$TARGET" '.timeline__item'

read -r -d '' EXPR <<'EOF' || true
(() => {
  const limit = LIMIT_VALUE;
  const normalizeUrl = (href) => {
    if (!href) return '';
    const url = new URL(href, location.origin);
    url.search = '';
    url.hash = '';
    return url.href;
  };
  const rawText = (node) => (node?.innerText || '').replace(/\u00A0/g, ' ').trim();
  const splitLines = (node) => rawText(node).split(/\n+/).map(s => s.trim()).filter(Boolean);
  const postUrlRe = /^https:\/\/xueqiu\.com\/[A-Za-z0-9_]+\/[0-9]+$/;
  const numericPostUrlRe = /^https:\/\/xueqiu\.com\/[0-9]+\/[0-9]+$/;
  const profileUrlRe = /^https:\/\/xueqiu\.com\/(?:u\/)?[A-Za-z0-9_]+\/?$/;
  const noiseRe = /^(展开|收藏|转发|讨论|赞|转发中|发布|投诉|加自选|默认排序.*|查看全部)$/;
  const results = [];
  const seen = new Set();

  for (const item of document.querySelectorAll('.timeline__item')) {
    const links = [...item.querySelectorAll('a[href]')];
    const hrefs = links.map(link => normalizeUrl(link.getAttribute('href') || '')).filter(Boolean);
    const url = hrefs.find(href => postUrlRe.test(href) || numericPostUrlRe.test(href)) || '';
    if (!url || seen.has(url)) continue;
    seen.add(url);

    const lines = splitLines(item);
    const header = lines[0] || '';
    const authorLink = links.find(link => {
      const href = normalizeUrl(link.getAttribute('href') || '');
      return profileUrlRe.test(href) && href !== location.origin + '/';
    });
    const author = rawText(authorLink) || header.replace(/(修改于|发布于|昨天|今天|\d{2}-\d{2}|\d+小时前).*$/, '').trim();
    const timeHint =
      header.match(/(修改于[^·]+|发布于[^·]+|昨天\s*\d{1,2}:\d{2}|今天\s*\d{1,2}:\d{2}|\d+小时前|\d+分钟前|\d{2}-\d{2}\s+\d{1,2}:\d{2})/)?.[1] ||
      '';
    const title = rawText(item.querySelector('.timeline__item__title, h1, h2, h3, h4, h5'));
    const contentLines = splitLines(item.querySelector('.timeline__item__content, .timeline__item__bd, .timeline__item__main'));
    const summary = contentLines
      .filter(line =>
        line &&
        line !== author &&
        line !== header &&
        line !== title &&
        !noiseRe.test(line) &&
        !/^[]+$/.test(line) &&
        !/^\d+$/.test(line)
      )
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 280);

    results.push({
      author,
      time_hint: timeHint,
      title: title || summary.slice(0, 60),
      summary,
      url
    });

    if (results.length >= limit) break;
  }

  return results;
})()
EOF
EXPR="${EXPR/LIMIT_VALUE/${LIMIT}}"

cdp_eval "$TARGET" "$EXPR"
