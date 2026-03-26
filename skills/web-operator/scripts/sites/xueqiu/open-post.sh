#!/usr/bin/env bash
# Open one xueqiu.com post URL and extract the article plus visible comments.
# Input: a Xueqiu post URL, optional comment limit, and optional target prefix.
# Output: a JSON object with author, time, source, title, text, url, and comments.
# Public interface: xueqiu-open-post.sh <post_url> [comment_limit] [target_prefix].

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

usage() {
  printf 'usage: %s <xueqiu_post_url> [comment_limit] [target_prefix]\n' "$(basename "$0")" >&2
  exit 1
}

POST_URL="${1:-}"
COMMENT_LIMIT="${2:-10}"
TARGET="${3:-}"

[[ -n "$POST_URL" ]] || usage
[[ "$POST_URL" =~ ^https://xueqiu\.com/[A-Za-z0-9_]+/[0-9]+([?#].*)?$ || "$POST_URL" =~ ^https://xueqiu\.com/[0-9]+/[0-9]+([?#].*)?$ ]] || {
  printf 'post_url must look like https://xueqiu.com/<user>/<post_id>\n' >&2
  exit 1
}
[[ "$COMMENT_LIMIT" =~ ^[0-9]+$ ]] || { printf 'comment_limit must be an integer\n' >&2; exit 1; }
(( COMMENT_LIMIT > 0 )) || { printf 'comment_limit must be greater than zero\n' >&2; exit 1; }

TARGET="$(xueqiu_find_target "$TARGET")"
[[ -n "$TARGET" ]] || { printf 'no usable xueqiu.com tab found\n' >&2; exit 1; }

POST_PATH="$(jq -nr --arg href "$POST_URL" '
  ($href | sub("^https://xueqiu\\.com"; ""))
  | sub("\\?.*$"; "")
  | sub("#.*$"; "")
')"

xueqiu_nav_fast "$TARGET" "$POST_URL"
wait_for_url_contains "$TARGET" "$POST_PATH"
wait_for_xueqiu_selector "$TARGET" '.article__page'
wait_for_xueqiu_selector "$TARGET" '.article__bd'
wait_for_xueqiu_selector "$TARGET" '.comment__list .comment__item' 15000 || true

read -r -d '' EXPR <<'EOF' || true
(() => {
  const commentLimit = COMMENT_LIMIT_VALUE;
  const normalizeUrl = (href) => {
    if (!href) return '';
    const url = new URL(href, location.origin);
    url.search = '';
    url.hash = '';
    return url.href;
  };
  const rawText = (node) => (node?.innerText || '').replace(/\u00A0/g, ' ').trim();
  const cleanText = (text) => String(text || '').replace(/\s+/g, ' ').trim();
  const article = document.querySelector('.article__page');
  if (!article) throw new Error('No Xueqiu article page found');

  const title = cleanText(rawText(article.querySelector('.article__bd__title')));
  const detail = cleanText(rawText(article.querySelector('.article__bd__detail')));
  const authorLinks = [...article.querySelectorAll('.article__author a[href]')];
  const author =
    cleanText(rawText(authorLinks.find(link =>
      /^https:\/\/xueqiu\.com\/(?:u\/)?[A-Za-z0-9_]+\/?$/.test(normalizeUrl(link.href)) &&
      cleanText(rawText(link)).length > 0 &&
      !/^发布于/.test(rawText(link)) &&
      !/Android|iPhone|雪球/.test(rawText(link))
    ))) ||
    cleanText(rawText(authorLinks.find(link =>
      normalizeUrl(link.href) !== normalizeUrl(location.href) &&
      cleanText(rawText(link)).length > 0
    )));
  const time =
    cleanText(rawText(authorLinks.find(link => /^发布于|^修改于/.test(rawText(link))))) ||
    cleanText(rawText(article.querySelector('.article__author .time')));
  const source =
    cleanText(rawText(authorLinks.find(link => /Android|iPhone|雪球/.test(rawText(link))))) ||
    cleanText(rawText(article.querySelector('.article__author')));
  const comments = [];

  for (const item of document.querySelectorAll('.comment__list .comment__item')) {
    if (comments.length >= commentLimit) break;
    const commentAuthor = cleanText(rawText(item.querySelector('.comment__item__main__hd .user-name')));
    const commentTime = cleanText(rawText(item.querySelector('.comment__item__main__hd .time')));
    const text = cleanText(rawText(item.querySelector('.comment__item__main p')));
    if (!commentAuthor || !text) continue;

    const tagText = cleanText(rawText(item.querySelector('.extend_comment_info')));
    const replyBlock = item.querySelector('.comment__item__reply');
    const replyTo = cleanText(rawText(replyBlock?.querySelector('.user-name')));
    const replyText = cleanText(rawText(replyBlock?.querySelector('.content')));
    const moreReplyText = cleanText(rawText(replyBlock?.querySelector('.more_reply')));
    const likeCount = Number.parseInt(cleanText(rawText(item.querySelector('.comment__item__like span:last-child'))), 10) || 0;

    comments.push({
      author: commentAuthor,
      time: commentTime,
      text,
      tags: tagText,
      reply_to: replyTo,
      reply_text: replyText,
      more_reply: moreReplyText,
      like_count: likeCount
    });
  }

  return {
    author,
    time,
    source,
    title,
    text: detail,
    url: normalizeUrl(location.href),
    comments
  };
})()
EOF
EXPR="${EXPR/COMMENT_LIMIT_VALUE/${COMMENT_LIMIT}}"

cdp_eval "$TARGET" "$EXPR"
