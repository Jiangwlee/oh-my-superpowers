#!/usr/bin/env bash
# This script opens one reddit.com post URL and extracts the post and comments.
# Input: a Reddit post URL, optional comment limit, and optional target prefix.
# Output: a JSON object with post metadata, body text, and visible comments.
# Public interface: reddit-open-post.sh <post_url> [comment_limit] [target_prefix].
#
# The script reuses an existing Reddit tab resolved through cdp.mjs.
# It navigates with Page.navigate and waits for title/comment selectors.
# The main post text is parsed from visible page content around the post title.
# The comments array follows DOM order and does not expand more replies.
# The default comment limit is 10.
# The script depends on jq and the sibling common.sh helpers.
# Errors are printed to stderr and the script exits non-zero.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

usage() {
  printf 'usage: %s <reddit_post_url> [comment_limit] [target_prefix]\n' "$(basename "$0")" >&2
  exit 1
}

POST_URL="${1:-}"
COMMENT_LIMIT="${2:-10}"
TARGET="${3:-}"

[[ -n "$POST_URL" ]] || usage
[[ "$POST_URL" =~ ^https://www\.reddit\.com/r/[^/]+/comments/[^/]+ ]] || {
  printf 'post_url must look like https://www.reddit.com/r/<sub>/comments/<id>/...\n' >&2
  exit 1
}
[[ "$COMMENT_LIMIT" =~ ^[0-9]+$ ]] || { printf 'comment_limit must be an integer\n' >&2; exit 1; }
(( COMMENT_LIMIT > 0 )) || { printf 'comment_limit must be greater than zero\n' >&2; exit 1; }

TARGET="$(reddit_find_target "$TARGET")"
[[ -n "$TARGET" ]] || { printf 'no usable reddit.com tab found\n' >&2; exit 1; }

reddit_nav_fast "$TARGET" "$POST_URL"
wait_for_url_contains "$TARGET" "/comments/"
wait_for_reddit_text "$TARGET" 'Sort by:'

read -r -d '' EXPR <<'EOF' || true
(() => {
  const commentLimit = COMMENT_LIMIT_VALUE;
  const title = (document.querySelector('h1')?.innerText || '').replace(/\s+/g, ' ').trim();
  const lines = (document.body.innerText || '')
    .split(/\n+/)
    .map(s => s.trim())
    .filter(Boolean);

  const subreddit = lines.find(line => /^r\//.test(line)) || '';
  const isTime = (line) => /^\d+\s?(?:sec|min|hr|day|week|month|year|mo|yr|d|h|m)s?\s+ago$/i.test(line) || /^\d+[smhdwy]$/.test(line);
  const titleIndex = title ? lines.indexOf(title) : -1;
  const metaWindow = titleIndex > 0 ? lines.slice(Math.max(0, titleIndex - 8), titleIndex) : lines.slice(0, 12);
  const time = metaWindow.find(line => isTime(line)) || '';

  let author = '';
  for (const line of metaWindow) {
    if (line && line !== subreddit && line !== time && !/^Go to /.test(line) && !/^(Member|Pro User|New User|Moderator|MOD|Top .*)$/i.test(line)) {
      author = line;
    }
  }
  if (!author) {
    for (const link of document.querySelectorAll('a[href^="/user/"]')) {
      const txt = (link.innerText || '').trim();
      if (txt) {
        author = txt;
        break;
      }
    }
  }

  const bodyStart = titleIndex >= 0 ? titleIndex + 1 : -1;
  const endMarkers = new Set(['Share', 'Sort by:', 'Comments Section']);
  let bodyEnd = lines.length;
  for (let i = bodyStart; i < lines.length; i++) {
    if (endMarkers.has(lines[i])) {
      bodyEnd = i;
      break;
    }
  }

  const body = (bodyStart > 0 ? lines.slice(bodyStart, bodyEnd) : [])
    .filter(line =>
      line &&
      line !== subreddit &&
      line !== time &&
      line !== author &&
      !/^(Discussion|Question|News|Guide|Member|Pro User|New User|Moderator|MOD|Top .*|Share)$/i.test(line) &&
      !/^\d+\s*(votes?|comments?)$/i.test(line)
    )
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();

  const commentBadges = /^(MOD|OP|Member|Pro User|New User|Top .*|Stickied comment)$/i;
  const stopCommentScan = new Set([
    'Community Info Section',
    'Community information',
    'Promotion',
    'R/OPENCLAW RULES',
    'OFFICIAL LINKS',
    'MODERATORS',
    'INSTALLED APPS'
  ]);
  const isUsername = (line) => /^[A-Za-z0-9_-]{3,}$/.test(line) && !/^r\//.test(line);
  const isCommentStart = (index) =>
    isUsername(lines[index] || '') &&
    (
      ((lines[index + 1] || '') === '•' && isTime(lines[index + 2] || '')) ||
      isTime(lines[index + 1] || '')
    );
  const comments = [];
  const sortIndex = lines.indexOf('Sort by:');
  const commentsSectionIndex = lines.indexOf('Comments Section');
  const commentStartIndex = sortIndex >= 0 ? sortIndex : commentsSectionIndex;
  for (let i = commentStartIndex >= 0 ? commentStartIndex + 1 : bodyEnd; i < lines.length && comments.length < commentLimit;) {
    if (stopCommentScan.has(lines[i])) break;
    if (!isCommentStart(i)) {
      i += 1;
      continue;
    }

    const commentAuthor = lines[i];
    let j = i + 1;
    if (lines[j] === '•') j += 1;
    const commentTimeLine = isTime(lines[j] || '') ? lines[j] : '';
    if (commentTimeLine) j += 1;

    const bodyLines = [];
    for (; j < lines.length; j++) {
      if (stopCommentScan.has(lines[j])) break;
      if (isCommentStart(j)) break;
      if (
        !lines[j] ||
        commentBadges.test(lines[j]) ||
        lines[j] === '•' ||
        /^Toggle Comment Thread$/i.test(lines[j]) ||
        /^Metadata for /i.test(lines[j])
      ) {
        continue;
      }
      bodyLines.push(lines[j]);
    }

    const text = bodyLines.join(' ').replace(/\s+/g, ' ').trim();
    if (text) {
      comments.push({
        author: commentAuthor,
        time: commentTimeLine,
        text,
        url: ''
      });
    }
    i = Math.max(j, i + 1);
  }

  return {
    title,
    subreddit,
    author,
    time,
    text: body,
    url: location.href,
    comments
  };
})()
EOF
EXPR="${EXPR/COMMENT_LIMIT_VALUE/${COMMENT_LIMIT}}"

cdp_eval "$TARGET" "$EXPR"
