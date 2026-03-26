#!/usr/bin/env bash
# This script searches weixin.sogou.com (搜狗微信搜索) and returns article search results.
# Input: a query string, optional result limit, and optional target prefix.
# Output: a JSON array of search results with title, summary, account, time, and link.
# Public interface: weixin-sogou-search.sh <query> [limit] [target_prefix].
#
# The script reuses or falls back to any available Chrome tab.
# It fetches results from a single page (10 results per page).
# It uses Page.navigate with evalraw to avoid race conditions.
# Extraction collects all ul.news-list li containers in a single eval call.
# Only results with a valid title are kept.
# The default limit is 10 and the hard cap is also 10 (single page limit).
# Snippet text is truncated to 280 characters.
# The script depends on jq and the sibling common.sh helpers.
# Errors are printed to stderr and the script exits non-zero.

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

TARGET="$(sogou_find_target "$TARGET")"
[[ -n "$TARGET" ]] || { printf 'no usable browser tab found\n' >&2; exit 1; }

ENCODED_QUERY="$(url_encode "$QUERY")"

read -r -d '' EXTRACT_EXPR <<'EOF' || true
(() => {
  const results = [];
  const items = document.querySelectorAll('ul.news-list li');

  for (const item of items) {
    // Title: must have an h3 > a
    const titleEl = item.querySelector('h3 a');
    const title = (titleEl?.innerText || '').replace(/\s+/g, ' ').trim();
    if (!title) continue;

    // Link: from the title element
    const link = titleEl?.href || '';
    if (!link) continue;

    // Summary: from p.txt-info
    const summaryEl = item.querySelector('p.txt-info');
    let summary = (summaryEl?.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 280);

    // Account: from .s-p span:first-child
    const accountEl = item.querySelector('.s-p span:first-child');
    const account = (accountEl?.innerText || '').trim();

    // Time: from .s2
    const timeEl = item.querySelector('.s2');
    const time = (timeEl?.innerText || '').trim();

    results.push({ title, summary, account, time, link });
  }

  return results;
})()
EOF

# Navigate to Sogou Weixin search
SEARCH_URL="https://weixin.sogou.com/weixin?query=${ENCODED_QUERY}&type=2&page=1&ie=utf8"
sogou_nav_fast "$TARGET" "$SEARCH_URL"

# Wait for URL to change and results to appear
sleep 2
wait_for_url_contains "$TARGET" 'weixin.sogou.com/weixin' 15000
wait_for_sogou_selector "$TARGET" 'ul.news-list li' 15000

# Extract results
PAGE_RESULTS="$(cdp_eval "$TARGET" "$EXTRACT_EXPR")"

# Apply limit
RESULTS=$(jq -n \
  --argjson page "$PAGE_RESULTS" \
  --argjson limit "$LIMIT" \
  '$page | .[:$limit]')

printf '%s\n' "$RESULTS"
