#!/usr/bin/env bash
# This script extracts recent updates from Taoguba's followed-content page.
# Input: optional hour window, optional result limit, and optional target prefix.
# Output: a JSON array of followed-content updates within the requested window.
# Public interface: taoguba-following.sh [hours] [limit] [target_prefix].
#
# The script navigates to the followed-content page in an existing Taoguba tab.
# It waits for "我的关注" content and parses visible update cards.
# Time filtering uses the full timestamp exposed in each card.
# The output fields are actor, update_time, action, text, post_title, and url.
# The default window is 12 hours and the default limit is 30.
# The script depends on jq and the sibling common.sh helpers.
# Errors are printed to stderr and the script exits non-zero.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

HOURS="${1:-12}"
LIMIT="${2:-30}"
TARGET="${3:-}"

[[ "$HOURS" =~ ^[0-9]+$ ]] || { printf 'hours must be an integer\n' >&2; exit 1; }
[[ "$LIMIT" =~ ^[0-9]+$ ]] || { printf 'limit must be an integer\n' >&2; exit 1; }
(( HOURS > 0 )) || { printf 'hours must be greater than zero\n' >&2; exit 1; }
(( LIMIT > 0 )) || { printf 'limit must be greater than zero\n' >&2; exit 1; }

TARGET="$(taoguba_find_target "$TARGET" "tgb\\.cn/user/getMoreListAction")"
[[ -n "$TARGET" ]] || { printf 'no usable Taoguba follow tab found\n' >&2; exit 1; }

taoguba_nav_fast "$TARGET" "https://www.tgb.cn/user/getMoreListAction"
wait_for_url_contains "$TARGET" "getMoreListAction"
wait_for_taoguba_selector "$TARGET" "div.superM_content"

read -r -d '' EXPR <<'EOF' || true
(() => {
  const hours = HOURS_VALUE;
  const limit = LIMIT_VALUE;
  const cutoff = Date.now() - hours * 3600 * 1000;
  const parseTs = (text) => {
    const m = /^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})$/.exec(text || '');
    if (!m) return null;
    return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), Number(m[4]), Number(m[5]), Number(m[6]));
  };
  const normalizeUrl = (href) => new URL(href.replace(/^\//, ''), location.origin + '/').href;
  const cards = [...document.querySelectorAll('div.superM_content')];
  const items = [];
  const seen = new Set();

  for (const card of cards) {
    const lines = (card.innerText || '')
      .split(/\n+/)
      .map(s => s.trim())
      .filter(Boolean);
    if (lines.length < 3) continue;

    const actor = lines[0] || '';
    const meta = lines[1] || '';
    const timeMatch = meta.match(/\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}/);
    const updateTime = timeMatch ? timeMatch[0] : '';
    const parsed = parseTs(updateTime);
    if (!parsed || parsed.getTime() < cutoff) continue;
    const action = meta.includes('·') ? meta.split('·').slice(1).join('·').trim() : '';
    const fromIndex = lines.findIndex(line => line === '来自《');
    const postTitle = fromIndex >= 0 ? (lines[fromIndex + 1] || '') : '';
    const text = lines
      .slice(2, fromIndex >= 0 ? fromIndex : lines.length)
      .filter(line => line !== '赞' && line !== '评论')
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim();

    const postAnchor = [...card.querySelectorAll('a[href]')]
      .map(a => ({ text: (a.innerText || '').trim(), href: a.getAttribute('href') || '' }))
      .find(item => /^(?:\/)?a\/[A-Za-z0-9]+(?:\/\d+#\d+)?$/.test(item.href) && item.text === postTitle);
    const url = postAnchor ? normalizeUrl(postAnchor.href) : '';
    const dedupeKey = `${actor}|${updateTime}|${postTitle}|${text}`;
    if (seen.has(dedupeKey)) continue;
    seen.add(dedupeKey);

    items.push({
      actor,
      update_time: updateTime,
      action,
      text,
      post_title: postTitle,
      url
    });
    if (items.length >= limit) break;
  }
  return items;
})()
EOF
EXPR="${EXPR/HOURS_VALUE/${HOURS}}"
EXPR="${EXPR/LIMIT_VALUE/${LIMIT}}"

cdp_eval "$TARGET" "$EXPR"
