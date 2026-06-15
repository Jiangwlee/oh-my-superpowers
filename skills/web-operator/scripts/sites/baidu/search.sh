#!/usr/bin/env bash
# This script searches baidu.com and returns the top organic search results.
# Input: a query string, optional result limit, and optional target prefix.
# Output: a JSON array of search results with title, snippet, and URL.
# Public interface: baidu-search.sh <query> [limit] [target_prefix].
#
# The script reuses or falls back to any available Chrome tab.
# It fetches results from a single page (Baidu's results are typically on one page).
# It uses cdp nav (waits for Page.loadEventFired) to avoid a race condition
# where wait conditions match the old DOM before navigation completes.
# It waits for the organic results section (.result) to appear before extracting.
# Extraction collects all .result.c-container containers in a single eval call.
# Only result cards with an h3 title and a valid http(s) destination URL are kept.
# Featured snippets, ads, and other non-organic results without proper structure are silently skipped.
# The default limit is 20 and the hard cap is also 20.
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
LIMIT="${2:-20}"
TARGET="${3:-}"

[[ -n "$QUERY" ]] || usage
[[ "$LIMIT" =~ ^[0-9]+$ ]] || { printf 'limit must be an integer\n' >&2; exit 1; }
(( LIMIT > 0 )) || { printf 'limit must be greater than zero\n' >&2; exit 1; }
(( LIMIT <= 20 )) || LIMIT=20

TARGET="$(baidu_find_target "$TARGET")"
[[ -n "$TARGET" ]] || { printf 'no usable browser tab found\n' >&2; exit 1; }

ENCODED_QUERY="$(url_encode "$QUERY")"

read -r -d '' EXTRACT_EXPR <<'EOF' || true
(() => {
  const results = [];
  const containers = document.querySelectorAll('.result.c-container, .result-op.c-container');

  for (const container of containers) {
    // Title: must have an h3
    const h3 = container.querySelector('h3');
    if (!h3) continue;
    const title = (h3.innerText || '').replace(/\s+/g, ' ').trim();
    if (!title) continue;

    // URL: get from h3 > a link
    const linkEl = h3.querySelector('a');
    let url = '';
    if (linkEl && linkEl.href) {
      url = linkEl.href;
    }
    // Skip if no valid URL or if it's a baidu internal link without redirect
    if (!url || (!url.startsWith('http://') && !url.startsWith('https://'))) continue;
    // Skip video search and other special pages
    if (url.includes('baidu.com/sf/vsearch')) continue;

    // Snippet: try known Baidu snippet selectors in priority order
    let snippet = '';
    const snippetSelectors = [
      '.c-color.summary-gap',
      '.c-color',
      '[class*="summary"]',
      '[class*="abstract"]',
      '[class*="content"]',
      '.cos-col',
      '.content-gap'
    ];
    for (const sel of snippetSelectors) {
      const snippetEl = container.querySelector(sel);
      if (snippetEl) {
        const text = (snippetEl.innerText || '').trim();
        // Skip if too short or contains the title
        if (text.length > 20 && !text.includes(title.slice(0, 10))) {
          snippet = text;
          break;
        }
      }
    }

    // Fallback: find the longest text content that's not the title
    if (!snippet) {
      let maxText = '';
      container.querySelectorAll('div, p').forEach(el => {
        const text = (el.innerText || '').trim();
        if (text.length > maxText.length && text.length < 300 && !text.includes(title)) {
          maxText = text;
        }
      });
      snippet = maxText;
    }

    // Truncate snippet to 280 chars
    snippet = snippet.slice(0, 280);

    results.push({ title, snippet, url });
  }

  return results;
})()
EOF

# Navigate to Baidu search
SEARCH_URL="https://www.baidu.com/s?wd=${ENCODED_QUERY}&tn=baidu"
baidu_nav_fast "$TARGET" "$SEARCH_URL"

# Wait for URL to change and results to appear
sleep 2
wait_for_url_contains "$TARGET" 'baidu.com/s' 15000
wait_for_baidu_selector "$TARGET" '.result.c-container'

# Extract results
PAGE_RESULTS="$(cdp_eval "$TARGET" "$EXTRACT_EXPR")"

# Guard against non-JSON (page change / CDP error) before jq --argjson.
PAGE_RESULTS="$(json_or_empty "$PAGE_RESULTS" "baidu extraction")"

# Apply limit
RESULTS=$(jq -n \
  --argjson page "$PAGE_RESULTS" \
  --argjson limit "$LIMIT" \
  '$page | unique_by(.url) | .[:$limit]')

printf '%s\n' "$RESULTS"
