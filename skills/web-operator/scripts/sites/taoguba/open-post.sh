#!/usr/bin/env bash
# This script opens one Taoguba post URL and extracts the main post body.
# Input: a Taoguba post URL and an optional target prefix.
# Output: a JSON object with title, author, publish time, stats, text, and url.
# Public interface: taoguba-open-post.sh <post_url> [target_prefix].
#
# The script reuses an existing Taoguba tab resolved through cdp.mjs.
# It navigates to the target URL and waits for the post title text to appear.
# The extraction reads the visible post body before the reply-floor section.
# It returns only the main post content and ignores comments/floors.
# The script depends on jq and the sibling common.sh helpers.
# Errors are printed to stderr and the script exits non-zero.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

POST_URL="${1:-}"
TARGET="${2:-}"

[[ -n "$POST_URL" ]] || {
  printf 'usage: %s <taoguba_post_url> [target_prefix]\n' "$(basename "$0")" >&2
  exit 1
}
[[ "$POST_URL" =~ ^https://www\.tgb\.cn/a/[A-Za-z0-9]+ ]] || {
  printf 'post_url must look like https://www.tgb.cn/a/<id>\n' >&2
  exit 1
}

TARGET="$(taoguba_find_target "$TARGET" "tgb\\.cn/(a/|jinghua/|user/getMoreListAction)")"
[[ -n "$TARGET" ]] || { printf 'no usable Taoguba tab found\n' >&2; exit 1; }

taoguba_nav_fast "$TARGET" "$POST_URL"
wait_for_url_contains "$TARGET" "/a/"

TITLE_HINT="$(basename "$POST_URL")"
wait_for_taoguba_text "$TARGET" "淘股吧原创"

read -r -d '' EXPR <<'EOF' || true
(() => {
  const lines = (document.body.innerText || '')
    .split(/\n+/)
    .map(s => s.trim())
    .filter(Boolean);
  const pageTitle = (document.title || '').split('_')[0].trim();
  const title = lines.find(line => line === pageTitle) || pageTitle;
  const titleIndex = title ? lines.indexOf(title) : -1;
  const metaLine = lines.find(line => /淘股吧原创/.test(line)) || '';
  const authorSpace = lines.find(line => /的空间$/.test(line)) || '';
  const author = authorSpace.replace(/的空间$/, '');
  const publishTimeMatch = metaLine.match(/\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}/);
  const publishTime = publishTimeMatch ? publishTimeMatch[0] : '';
  const browseMatch = metaLine.match(/浏览\s+(\d+)/);
  const commentMatch = metaLine.match(/评论\s+(\d+)/);

  const start = titleIndex >= 0 ? titleIndex + 1 : 0;
  let end = lines.length;
  for (let i = start; i < lines.length; i++) {
    if (
      /^第\d+楼/.test(lines[i]) ||
      /^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}$/.test(lines[i]) ||
      lines[i] === '举报' ||
      lines[i] === '话题与分类：' ||
      lines[i] === '最早' ||
      lines[i] === '最新评论' ||
      lines[i] === '点赞榜' ||
      lines[i] === '打赏榜' ||
      lines[i] === '查看选项' ||
      lines[i] === '发布回帖'
    ) {
      end = i;
      break;
    }
  }

  const text = lines
    .slice(start, end)
    .filter(line =>
      line &&
      line !== metaLine &&
      !/空间$/.test(line) &&
      line !== '淘股吧原创' &&
      !/^浏览\s+\d+/.test(line) &&
      !/^评论\s+\d+/.test(line) &&
      !/^\d+\s+9\/9/.test(line) &&
      line !== '举报' &&
      line !== '评论 打赏Ta' &&
      line !== '打赏Ta' &&
      !/^分享文章/.test(line) &&
      !/^加油/.test(line) &&
      line !== '只看楼主' &&
      line !== '数据加载中，请等待...'
    )
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();

  return {
    title,
    author,
    publish_time: publishTime,
    stats: {
      browse: browseMatch ? Number(browseMatch[1]) : null,
      comments: commentMatch ? Number(commentMatch[1]) : null
    },
    text,
    url: location.href
  };
})()
EOF

cdp_eval "$TARGET" "$EXPR"
