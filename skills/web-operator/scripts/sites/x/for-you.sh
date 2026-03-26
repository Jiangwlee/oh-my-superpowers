#!/usr/bin/env bash
# This script reads the X.com For You recommendation feed.
# Input: optional result limit and optional target prefix.
# Output: a JSON array of post summaries from the For You feed.
# Public interface: x-for-you.sh [limit] [target_prefix].
#
# The script reuses an existing x.com tab discovered through cdp.mjs.
# It navigates to x.com/explore/tabs/for_you to access the recommendation feed.
# Scroll pagination is used to collect up to the requested limit.
# Extraction keeps only unique post URLs and ignores analytics links.
# The output fields are author, handle, time_hint, summary, and url.
# The default limit is 20 and the hard cap is 100.
# The script depends on jq and the sibling common.sh helpers.
# Errors are printed to stderr and the script exits non-zero.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

usage() {
  printf 'usage: %s [limit] [target_prefix]\n' "$(basename "$0")" >&2
  exit 1
}

LIMIT="${1:-20}"
TARGET="${2:-}"

[[ "$LIMIT" =~ ^[0-9]+$ ]] || { printf 'limit must be an integer\n' >&2; exit 1; }
(( LIMIT > 0 )) || { printf 'limit must be greater than zero\n' >&2; exit 1; }
(( LIMIT <= 100 )) || LIMIT=100

TARGET="$(x_find_target "$TARGET")"
[[ -n "$TARGET" ]] || { printf 'no usable x.com tab found\n' >&2; exit 1; }

cdp_nav "$TARGET" "https://x.com/explore/tabs/for_you"
wait_for_x_article "$TARGET"

read -r -d '' EXPR <<'EOF' || true
(async () => {
  const limit = LIMIT_VALUE;
  const maxScrollRounds = Math.min(Math.ceil(limit / 5) + 2, 20);
  const scrollWaitMs = 1500;

  const rawTextOf = (node) => (node?.innerText || '').replace(/\u00A0/g, ' ').trim();
  const flatTextOf = (node) => rawTextOf(node).replace(/\s+/g, ' ').trim();

  const extractNew = (seen) => {
    const items = [];
    for (const article of document.querySelectorAll('article')) {
      const links = [...article.querySelectorAll('a[href]')].map(a => a.getAttribute('href') || '');
      const statusHref = links.find(href => /^\/[^/]+\/status\/\d+$/.test(href));
      if (!statusHref) continue;
      const url = 'https://x.com' + statusHref;
      if (seen.has(url)) continue;
      seen.add(url);

      const handleHref = links.find(href => /^\/[A-Za-z0-9_]{1,15}$/.test(href));
      const timeNode = article.querySelector('time');
      const blocks = rawTextOf(article).split(/\n+/).map(s => s.trim()).filter(Boolean);
      const handle = handleHref ? handleHref.slice(1) : '';
      const summary = blocks
        .find(line =>
          line !== (blocks[0] || '') &&
          line !== handle &&
          line !== '@' + handle &&
          !/^(@[A-Za-z0-9_]{1,15}|Replying to|Show more|Show original|Show translation|Promoted|Ad)$/i.test(line) &&
          line.length >= 16 &&
          !/^\d+[smhdwy]$/.test(line)
        ) || flatTextOf(article);

      items.push({
        author: blocks.find(line => line !== handle && line !== '@' + handle) || '',
        handle: handle ? '@' + handle : '',
        time_hint: timeNode ? timeNode.getAttribute('datetime') || flatTextOf(timeNode) : '',
        summary: summary.replace(/\s+/g, ' ').slice(0, 280),
        url
      });
    }
    return items;
  };

  const seen = new Set();
  const result = [];

  result.push(...extractNew(seen));

  for (let round = 0; round < maxScrollRounds && result.length < limit; round++) {
    const prevCount = result.length;
    window.scrollBy(0, window.innerHeight * 3);
    await new Promise(resolve => setTimeout(resolve, scrollWaitMs));
    result.push(...extractNew(seen));
    if (result.length === prevCount) break;
  }

  return result.slice(0, limit);
})()
EOF
EXPR="${EXPR/LIMIT_VALUE/${LIMIT}}"

cdp_eval "$TARGET" "$EXPR"
