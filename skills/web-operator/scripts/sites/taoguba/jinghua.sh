#!/usr/bin/env bash
# This script extracts recent Taoguba jinghua posts from the list page.
# Input: optional hour window, optional result limit, and optional target prefix.
# Output: a JSON array of recent jinghua posts within the requested time window.
# Public interface: taoguba-jinghua.sh [hours] [limit] [target_prefix].
#
# The script navigates to https://www.tgb.cn/jinghua/ in an existing Taoguba tab.
# It waits for the table header text and parses visible list entries.
# Time filtering uses the browser's current local time and assumes the current
# year for month-day timestamps shown on the page.
# The output fields are title, author, post_time, reply_time, stats, and url.
# The default window is 24 hours and the default limit is 20.
# The script depends on jq and the sibling common.sh helpers.
# Errors are printed to stderr and the script exits non-zero.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

HOURS="${1:-24}"
LIMIT="${2:-20}"
TARGET="${3:-}"

[[ "$HOURS" =~ ^[0-9]+$ ]] || { printf 'hours must be an integer\n' >&2; exit 1; }
[[ "$LIMIT" =~ ^[0-9]+$ ]] || { printf 'limit must be an integer\n' >&2; exit 1; }
(( HOURS > 0 )) || { printf 'hours must be greater than zero\n' >&2; exit 1; }
(( LIMIT > 0 )) || { printf 'limit must be greater than zero\n' >&2; exit 1; }

TARGET="$(taoguba_find_target "$TARGET" "tgb\\.cn/(jinghua/|a/)")"
[[ -n "$TARGET" ]] || { printf 'no usable Taoguba tab found\n' >&2; exit 1; }

taoguba_nav_fast "$TARGET" "https://www.tgb.cn/jinghua/"
wait_for_url_contains "$TARGET" "/jinghua/"
wait_for_taoguba_text "$TARGET" "回帖日期"

read -r -d '' EXPR <<'EOF' || true
(() => {
  const hours = HOURS_VALUE;
  const limit = LIMIT_VALUE;
  const now = new Date();
  const cutoff = now.getTime() - hours * 3600 * 1000;
  const parseMdHm = (text) => {
    const m = /^(\d{2})-(\d{2})\s+(\d{2}):(\d{2})$/.exec(text || '');
    if (!m) return null;
    const dt = new Date(now.getFullYear(), Number(m[1]) - 1, Number(m[2]), Number(m[3]), Number(m[4]), 0);
    if (dt.getTime() - now.getTime() > 12 * 3600 * 1000) dt.setFullYear(dt.getFullYear() - 1);
    return dt;
  };
  const normalizeUrl = (href) => new URL(href.replace(/^\//, ''), location.origin + '/').href;
  const seen = new Set();
  const items = [];
  const timeRegex = /^\d{2}-\d{2}\s+\d{2}:\d{2}$/;

  for (const anchor of document.querySelectorAll('a[href]')) {
    const href = anchor.getAttribute('href') || '';
    if (!/^(?:\/)?a\/[A-Za-z0-9]+$/.test(href)) continue;
    const title = (anchor.innerText || '').replace(/\s+/g, ' ').trim();
    if (!title || title === '查看原文') continue;

    let container = anchor;
    for (let i = 0; i < 6 && container.parentElement; i++) {
      const candidate = container.parentElement;
      const candidateText = (candidate.innerText || '').trim();
      container = candidate;
      if ((candidateText.match(/\d{2}-\d{2}\s+\d{2}:\d{2}/g) || []).length >= 2) break;
    }

    const lines = (container.innerText || '')
      .split(/\n+/)
      .map(s => s.trim())
      .filter(Boolean);
    const times = lines.filter(line => timeRegex.test(line));
    if (times.length < 2) continue;
    const replyTime = times[0];
    const postTime = times[1];
    const parsedPostTime = parseMdHm(postTime);
    if (!parsedPostTime || parsedPostTime.getTime() < cutoff) continue;

    const stats = lines.find(line => /^\d+\s*\/\s*\d+$/.test(line)) || '';
    const authorIndex = lines.indexOf(replyTime) + 1;
    const author = authorIndex > 0 ? (lines[authorIndex] || '') : '';
    const url = normalizeUrl(href);
    if (seen.has(url)) continue;
    seen.add(url);

    items.push({
      title,
      author,
      post_time: postTime,
      reply_time: replyTime,
      stats,
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
