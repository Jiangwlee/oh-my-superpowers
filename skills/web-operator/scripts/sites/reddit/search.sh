#!/usr/bin/env bash
# This script searches reddit.com using the default search results page.
# Input: a query string, optional result limit, and optional target prefix.
# Output: a JSON array of search result summaries with Reddit post URLs.
# Public interface: reddit-search.sh <query> [limit] [target_prefix].
#
# The script reuses an existing Reddit tab discovered through cdp.mjs.
# It navigates directly to the default Reddit search URL.
# It waits for post links on the search page instead of waiting for full idle.
# Extraction keeps only unique post URLs under /r/.../comments/... .
# The output fields are title, subreddit, time_hint, summary, and url.
# The default limit is 20 and the hard cap is 100. Scroll pagination is used to collect up to the limit.
# Summary text is the visible result-card summary, not the full post body.
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
LIMIT="${2:-20}"
TARGET="${3:-}"

[[ -n "$QUERY" ]] || usage
[[ "$LIMIT" =~ ^[0-9]+$ ]] || { printf 'limit must be an integer\n' >&2; exit 1; }
(( LIMIT > 0 )) || { printf 'limit must be greater than zero\n' >&2; exit 1; }
(( LIMIT <= 100 )) || LIMIT=100

TARGET="$(reddit_find_target "$TARGET")"
[[ -n "$TARGET" ]] || { printf 'no usable reddit.com tab found\n' >&2; exit 1; }

SEARCH_URL="https://www.reddit.com/search/?q=$(url_encode "$QUERY")"
reddit_nav_fast "$TARGET" "$SEARCH_URL"
wait_for_url_contains "$TARGET" "reddit.com/search"
wait_for_reddit_selector "$TARGET" 'a[href*="/comments/"]'

read -r -d '' EXPR <<'EOF' || true
(async () => {
  const limit = LIMIT_VALUE;
  const maxScrollRounds = Math.min(Math.ceil(limit / 5) + 2, 20);
  const scrollWaitMs = 2000;

  const normalize = (href) => {
    if (!href) return '';
    const url = new URL(href, location.origin);
    url.search = '';
    url.hash = '';
    return url.href;
  };
  const textLines = (node) => (node?.innerText || '')
    .split(/\n+/)
    .map(s => s.trim())
    .filter(Boolean);
  const postRegex = /^https:\/\/www\.reddit\.com\/r\/[^/]+\/comments\/[^/]+\/[^/]*\/?$/;
  const seen = new Set();
  const results = [];

  const extractNew = () => {
    const items = [];
    for (const anchor of document.querySelectorAll('a[href]')) {
      const url = normalize(anchor.getAttribute('href'));
      if (!postRegex.test(url)) continue;
      if (seen.has(url)) continue;

      const title = (anchor.innerText || '').replace(/\s+/g, ' ').trim();
      if (!title) continue;

      let container = anchor;
      for (let i = 0; i < 7 && container.parentElement; i++) {
        const candidate = container.parentElement;
        const candidateText = (candidate.innerText || '').trim();
        container = candidate;
        if (candidateText.length > title.length + 20) break;
      }

      const lines = textLines(container);
      const subreddit = lines.find(line => /^r\//.test(line)) || '';
      const timeHint = lines.find(line => /^\d+\s?(?:sec|min|hr|day|week|month|year|mo|yr|d|h|m)s?\s+ago$/i.test(line) || /^\d+[smhdwy]$/.test(line)) || '';
      const summary = lines.find(line =>
        line !== title &&
        line !== subreddit &&
        line !== timeHint &&
        !/^\d+\s*(votes?|comments?)$/i.test(line) &&
        line.length >= 24
      ) || '';

      seen.add(url);
      items.push({
        title,
        subreddit,
        time_hint: timeHint,
        summary: summary.replace(/\s+/g, ' ').slice(0, 280),
        url
      });
    }
    return items;
  };

  results.push(...extractNew());

  for (let round = 0; round < maxScrollRounds && results.length < limit; round++) {
    const prevCount = results.length;
    window.scrollBy(0, window.innerHeight * 3);
    await new Promise(resolve => setTimeout(resolve, scrollWaitMs));
    results.push(...extractNew());
    if (results.length === prevCount) break;
  }

  return results.slice(0, limit);
})()
EOF
EXPR="${EXPR/LIMIT_VALUE/${LIMIT}}"

cdp_eval "$TARGET" "$EXPR"
