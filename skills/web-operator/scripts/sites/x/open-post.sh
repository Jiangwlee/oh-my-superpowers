#!/usr/bin/env bash
# This script opens one x.com post URL and extracts the main post plus comments.
# Input: a single x.com post URL, optional comment limit, and optional target prefix.
# Output: a JSON object with author, handle, time, text, url, external_links, and comments.
# Public interface: open-post.sh <post_url> [comment_limit] [target_prefix].
#
# The script reuses an existing x.com tab resolved through cdp.mjs.
# It navigates directly to the target post URL instead of simulating clicks.
# It waits for the main article to appear before reading page content.
# The extraction reflects the currently visible language version on the page.
# It does not click Show original or Show translation automatically.
# Comments are collected by a shell-driven scroll loop: each iteration scrolls
# the page via cdp scroll, then runs a short eval to extract newly visible
# reply articles. This avoids long-running evals that hit the CDP timeout.
# The default comment limit is 20. Pass 0 to fetch all comments.
# The script depends on jq and the sibling common.sh helpers.
# Errors are printed to stderr and the script exits non-zero.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

usage() {
  printf 'usage: %s <x_post_url> [comment_limit] [target_prefix]\n' "$(basename "$0")" >&2
  exit 1
}

POST_URL="${1:-}"
COMMENT_LIMIT="${2:-20}"
TARGET="${3:-}"

[[ -n "$POST_URL" ]] || usage
[[ "$POST_URL" =~ ^https://x\.com/[^/]+/status/[0-9]+ ]] || {
  printf 'post_url must look like https://x.com/<user>/status/<id>\n' >&2
  exit 1
}
[[ "$COMMENT_LIMIT" =~ ^[0-9]+$ ]] || { printf 'comment_limit must be an integer (0 = all)\n' >&2; exit 1; }

TARGET="$(x_find_target "$TARGET")"
[[ -n "$TARGET" ]] || { printf 'no usable x.com tab found\n' >&2; exit 1; }

cdp_nav "$TARGET" "$POST_URL"
wait_for_x_article "$TARGET"
cdp_bring_to_front "$TARGET"

# --- Step 1: Extract main post (short eval, no scrolling) ---
read -r -d '' MAIN_EXPR <<'EOF' || true
(() => {
  const rawTextOf = (node) => (node?.innerText || '').replace(/\u00A0/g, ' ').trim();
  const flatTextOf = (node) => rawTextOf(node).replace(/\s+/g, ' ').trim();

  const articles = document.querySelectorAll('article');
  const mainArticle = articles[0];
  if (!mainArticle) throw new Error('No main article found on the post page');

  const replyBtn = mainArticle.querySelector('button[aria-label*="Repl"]');
  const replyLabel = replyBtn ? replyBtn.getAttribute('aria-label') : '';
  const replyCountMatch = replyLabel.match(/^([\d,]+)/);
  const replyCount = replyCountMatch ? parseInt(replyCountMatch[1].replace(/,/g, ''), 10) : 0;

  const links = [...mainArticle.querySelectorAll('a[href]')];
  const handleNode = links.find(a => /^\/[A-Za-z0-9_]{1,15}$/.test(a.getAttribute('href') || ''));
  const timeNode = mainArticle.querySelector('time');
  const lines = rawTextOf(mainArticle).split(/\n+/).map(s => s.trim()).filter(Boolean);
  const handle = handleNode ? (handleNode.getAttribute('href') || '').slice(1) : '';
  const timeText = timeNode ? (timeNode.getAttribute('datetime') || flatTextOf(timeNode)) : '';
  const author = lines.find(line => line && line !== '@' + handle && line !== handle) || '';
  const body = lines.filter(line => {
    if (!line) return false;
    if (author && line === author) return false;
    if (handle && (line === handle || line === '@' + handle)) return false;
    if (/^Translated from /i.test(line)) return false;
    if (/^(Show original|Show translation|About automatic translation|Rate this translation:|Replying to)$/i.test(line)) return false;
    if (timeText && line === timeText) return false;
    if (/^·?\s*\d+\s+Views$/i.test(line)) return false;
    if (/^\d{1,2}:\d{2}\s+(AM|PM)\s+·\s+/.test(line)) return false;
    return true;
  }).join(' ').replace(/\s+·\s+\d+\s+Views?$/i, '').trim();

  const ownBase = window.location.href.split('?')[0];
  const externalLinks = [...new Set(
    links
      .map(a => a.getAttribute('href') || '')
      .filter(href => {
        if (!href.startsWith('https://')) return false;
        if (/^https:\/\/(x|twitter)\.com\/[A-Za-z0-9_]+$/.test(href)) return false;
        if (href.startsWith(ownBase)) return false;
        return true;
      })
  )];

  return {
    author,
    handle: handle ? '@' + handle : '',
    time: timeText,
    text: body,
    url: window.location.href,
    reply_count: replyCount,
    external_links: externalLinks
  };
})()
EOF

MAIN_JSON="$(cdp_eval "$TARGET" "$MAIN_EXPR")"
REPLY_COUNT="$(printf '%s' "$MAIN_JSON" | jq -r '.reply_count // 0')"

# Determine effective comment limit
if [[ "$COMMENT_LIMIT" -eq 0 ]]; then
  EFFECTIVE_LIMIT="${REPLY_COUNT:-9999}"
  [[ "$EFFECTIVE_LIMIT" -eq 0 ]] && EFFECTIVE_LIMIT=9999
else
  EFFECTIVE_LIMIT="$COMMENT_LIMIT"
fi

# --- Step 2: Shell-driven scroll loop to collect comments ---
# Initialize the seen-set in the browser as a global variable
cdp_eval "$TARGET" "window.__omp_seen = new Set(); 'initialized'" >/dev/null

# JS expression to extract currently visible comments (short, no scrolling)
read -r -d '' EXTRACT_EXPR <<'EOF' || true
(() => {
  const seen = window.__omp_seen;
  const rawTextOf = (node) => (node?.innerText || '').replace(/\u00A0/g, ' ').trim();
  const flatTextOf = (node) => rawTextOf(node).replace(/\s+/g, ' ').trim();
  const items = [];
  const allArticles = document.querySelectorAll('article');
  for (let i = 1; i < allArticles.length; i++) {
    const article = allArticles[i];
    const cLinks = [...article.querySelectorAll('a[href]')];
    const statusHref = cLinks.find(a => /^\/[^/]+\/status\/\d+$/.test(a.getAttribute('href') || ''));
    const commentId = statusHref ? statusHref.getAttribute('href') : article.innerText.slice(0, 80);
    if (seen.has(commentId)) continue;
    seen.add(commentId);

    const cHandleNode = cLinks.find(a => /^\/[A-Za-z0-9_]{1,15}$/.test(a.getAttribute('href') || ''));
    const cTimeNode = article.querySelector('time');
    const cLines = rawTextOf(article).split(/\n+/).map(s => s.trim()).filter(Boolean);
    const cHandle = cHandleNode ? (cHandleNode.getAttribute('href') || '').slice(1) : '';
    const cTime = cTimeNode ? (cTimeNode.getAttribute('datetime') || flatTextOf(cTimeNode)) : '';
    const cAuthor = cLines.find(line => line && line !== '@' + cHandle && line !== cHandle) || '';

    const cText = cLines.filter(line => {
      if (!line) return false;
      if (cAuthor && line === cAuthor) return false;
      if (cHandle && (line === cHandle || line === '@' + cHandle)) return false;
      if (/^(Replying to|Show original|Show translation|Translated from)$/i.test(line)) return false;
      if (cTime && line === cTime) return false;
      if (/^Replying to\s+@/i.test(line)) return false;
      return true;
    }).join(' ').replace(/\s+/g, ' ').trim();

    if (cText) {
      items.push({
        author: cAuthor,
        handle: cHandle ? '@' + cHandle : '',
        time: cTime,
        text: cText,
        url: statusHref ? 'https://x.com' + statusHref.getAttribute('href') : ''
      });
    }
  }
  return items;
})()
EOF

# JS expression to click "Show probable spam" or similar fold buttons
read -r -d '' CLICK_SHOW_MORE_EXPR <<'EOF' || true
(() => {
  const btns = [...document.querySelectorAll('button, [role="button"]')];
  for (const btn of btns) {
    const label = (btn.innerText || '').trim();
    if (/^Show\s+(probable\s+spam|additional\s+repl)/i.test(label)) {
      btn.click();
      return true;
    }
  }
  return false;
})()
EOF

COMMENTS_FILE="$(mktemp)"
printf '[]' > "$COMMENTS_FILE"
TOTAL_COMMENTS=0
EMPTY_ROUNDS=0
MAX_EMPTY_ROUNDS=5
MAX_SCROLL_ROUNDS=500
SCROLL_WAIT=1.5

for (( round=0; round<MAX_SCROLL_ROUNDS && TOTAL_COMMENTS<EFFECTIVE_LIMIT; round++ )); do
  # Scroll down
  cdp scroll "$TARGET" down 3 >/dev/null 2>&1
  sleep "$SCROLL_WAIT"

  # Click "Show probable spam" etc. if present
  CLICKED="$(cdp_eval "$TARGET" "$CLICK_SHOW_MORE_EXPR" 2>/dev/null || echo 'false')"
  if [[ "$CLICKED" == "true" ]]; then
    sleep "$SCROLL_WAIT"
  fi

  # Extract newly visible comments
  NEW_COMMENTS="$(cdp_eval "$TARGET" "$EXTRACT_EXPR")"
  NEW_COUNT="$(printf '%s' "$NEW_COMMENTS" | jq 'length')"

  if [[ "$NEW_COUNT" -gt 0 ]]; then
    # Merge new comments into accumulated file
    jq -s '.[0] + .[1]' "$COMMENTS_FILE" <(printf '%s' "$NEW_COMMENTS") > "${COMMENTS_FILE}.tmp"
    mv "${COMMENTS_FILE}.tmp" "$COMMENTS_FILE"
    TOTAL_COMMENTS="$(jq 'length' "$COMMENTS_FILE")"
    EMPTY_ROUNDS=0
    printf 'round %d: +%d comments (total: %d/%d)\n' "$round" "$NEW_COUNT" "$TOTAL_COMMENTS" "$EFFECTIVE_LIMIT" >&2
  else
    EMPTY_ROUNDS=$((EMPTY_ROUNDS + 1))
    if [[ "$EMPTY_ROUNDS" -ge "$MAX_EMPTY_ROUNDS" ]]; then
      printf 'stopping after %d consecutive empty rounds (total: %d)\n' "$MAX_EMPTY_ROUNDS" "$TOTAL_COMMENTS" >&2
      break
    fi
  fi
done

# Clean up global
cdp_eval "$TARGET" "delete window.__omp_seen; 'done'" >/dev/null 2>&1 || true

# --- Step 3: Assemble final JSON ---
jq --argjson limit "$EFFECTIVE_LIMIT" '.[:$limit]' "$COMMENTS_FILE" > "${COMMENTS_FILE}.trimmed"

MAIN_FILE="$(mktemp)"
printf '%s' "$MAIN_JSON" > "$MAIN_FILE"

jq -s '.[0] + {comments: .[1]}' "$MAIN_FILE" "${COMMENTS_FILE}.trimmed"
rm -f "$COMMENTS_FILE" "${COMMENTS_FILE}.trimmed" "$MAIN_FILE"
