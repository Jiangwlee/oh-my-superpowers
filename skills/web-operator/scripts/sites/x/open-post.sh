#!/usr/bin/env bash
# This script opens one x.com post URL and extracts the visible main post text.
# Input: a single x.com post URL and an optional target prefix.
# Output: a JSON object with author, handle, time, text, and url.
# Public interface: x-open-post.sh <post_url> [target_prefix].
#
# The script reuses an existing x.com tab resolved through cdp.mjs.
# It navigates directly to the target post URL instead of simulating clicks.
# It waits for the main article to appear before reading page content.
# The extraction reflects the currently visible language version on the page.
# It does not click Show original or Show translation automatically.
# It returns only the main post article and ignores replies or thread expansion.
# The script depends on jq and the sibling common.sh helpers.
# Errors are printed to stderr and the script exits non-zero.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

usage() {
  printf 'usage: %s <x_post_url> [target_prefix]\n' "$(basename "$0")" >&2
  exit 1
}

POST_URL="${1:-}"
TARGET="${2:-}"

[[ -n "$POST_URL" ]] || usage
[[ "$POST_URL" =~ ^https://x\.com/[^/]+/status/[0-9]+ ]] || {
  printf 'post_url must look like https://x.com/<user>/status/<id>\n' >&2
  exit 1
}

TARGET="$(x_find_target "$TARGET")"
[[ -n "$TARGET" ]] || { printf 'no usable x.com tab found\n' >&2; exit 1; }

cdp_nav "$TARGET" "$POST_URL"
wait_for_x_article "$TARGET"

read -r -d '' EXPR <<'EOF' || true
(() => {
  const article = document.querySelector('article');
  if (!article) throw new Error('No main article found on the post page');

  const rawTextOf = (node) => (node?.innerText || '').replace(/\u00A0/g, ' ').trim();
  const flatTextOf = (node) => rawTextOf(node).replace(/\s+/g, ' ').trim();
  const links = [...article.querySelectorAll('a[href]')];
  const handleNode = links.find(a => /^\/[A-Za-z0-9_]{1,15}$/.test(a.getAttribute('href') || ''));
  const timeNode = article.querySelector('time');
  const lines = rawTextOf(article).split(/\n+/).map(s => s.trim()).filter(Boolean);
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

  // Collect all absolute URLs from the article, excluding bare user profile links
  // and the tweet's own URL. Keeps t.co, x.com/i/links wrappers, and direct
  // external URLs so the caller can follow whichever applies.
  const ownBase = window.location.href.split('?')[0];
  const externalLinks = [...new Set(
    links
      .map(a => a.getAttribute('href') || '')
      .filter(href => {
        if (!href.startsWith('https://')) return false;
        // Skip bare user profile URLs (no /status/ segment)
        if (/^https:\/\/(x|twitter)\.com\/[A-Za-z0-9_]+$/.test(href)) return false;
        // Skip this tweet's own URL
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
    external_links: externalLinks
  };
})()
EOF

cdp_eval "$TARGET" "$EXPR"
