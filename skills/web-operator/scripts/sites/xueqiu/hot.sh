#!/usr/bin/env bash
# Extract the visible hot-post timeline from the xueqiu.com home page.
# Input: optional result limit and optional target prefix.
# Output: a JSON array of hot posts with author, time_hint, title, summary, and url.
# Public interface: xueqiu-hot.sh [limit] [target_prefix].
#
# The script clicks the visible "热门" tab when present, then auto-scrolls the
# SPA feed to trigger lazy loading before extraction. This is necessary because
# Xueqiu often renders only one or two timeline cards initially and loads more
# cards on scroll.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

LIMIT="${1:-10}"
TARGET="${2:-}"

[[ "$LIMIT" =~ ^[0-9]+$ ]] || { printf 'limit must be an integer\n' >&2; exit 1; }
(( LIMIT > 0 )) || { printf 'limit must be greater than zero\n' >&2; exit 1; }
(( LIMIT <= 10 )) || LIMIT=10

TARGET="$(xueqiu_find_target "$TARGET")"
[[ -n "$TARGET" ]] || { printf 'no usable xueqiu.com tab found\n' >&2; exit 1; }

xueqiu_nav_fast "$TARGET" "https://xueqiu.com/"
wait_for_xueqiu_selector "$TARGET" '.timeline__item'

read -r -d '' CLICK_EXPR <<'EOF' || true
(() => {
  const hotLink = [...document.querySelectorAll('a')].find(a => (a.innerText || '').trim() === '热门');
  if (hotLink) hotLink.click();
  return hotLink ? 'CLICKED' : 'MISSING';
})()
EOF
cdp_eval "$TARGET" "$CLICK_EXPR" >/dev/null || true
wait_for_xueqiu_selector "$TARGET" '.timeline__item'

read -r -d '' COLLECT_EXPR <<'EOF' || true
(async () => {
  const targetCount = LIMIT_VALUE;
  const maxRounds = 10;
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  let previousCount = -1;
  let stableRounds = 0;

  for (let round = 0; round < maxRounds; round += 1) {
    const count = document.querySelectorAll('.timeline__item').length;
    if (count >= targetCount) {
      return { count, rounds: round, done: 'enough_items' };
    }

    if (count === previousCount) {
      stableRounds += 1;
    } else {
      stableRounds = 0;
    }
    previousCount = count;

    const before = document.documentElement.scrollHeight;
    window.scrollTo({ top: before, behavior: 'instant' });
    await sleep(900);
    window.scrollBy(0, 600);
    await sleep(900);
    const after = document.documentElement.scrollHeight;

    if (stableRounds >= 2 && after <= before) {
      return { count, rounds: round + 1, done: 'scroll_stable' };
    }
  }

  return {
    count: document.querySelectorAll('.timeline__item').length,
    rounds: maxRounds,
    done: 'max_rounds'
  };
})()
EOF
COLLECT_EXPR="${COLLECT_EXPR/LIMIT_VALUE/${LIMIT}}"
cdp_eval_retry "$TARGET" "$COLLECT_EXPR" >/dev/null

read -r -d '' EXPR <<'EOF' || true
(() => {
  const limit = LIMIT_VALUE;
  const normalizeUrl = (href) => {
    if (!href) return '';
    const url = new URL(href, location.origin);
    url.search = '';
    url.hash = '';
    return url.href;
  };
  const rawText = (node) => (node?.innerText || '').replace(/\u00A0/g, ' ').trim();
  const splitLines = (node) => rawText(node).split(/\n+/).map(s => s.trim()).filter(Boolean);
  const postUrlRe = /^https:\/\/xueqiu\.com\/[A-Za-z0-9_]+\/[0-9]+$/;
  const numericPostUrlRe = /^https:\/\/xueqiu\.com\/[0-9]+\/[0-9]+$/;
  const results = [];
  const seen = new Set();

  for (const item of document.querySelectorAll('.timeline__item')) {
    const lines = splitLines(item);
    const title = rawText(item.querySelector('.timeline__item__title, h1, h2, h3, h4, h5'));
    const url = [...item.querySelectorAll('a[href]')]
      .map(link => normalizeUrl(link.getAttribute('href') || ''))
      .find(href => postUrlRe.test(href) || numericPostUrlRe.test(href)) || '';
    if (!url || seen.has(url)) continue;
    seen.add(url);

    const header = lines[0] || '';
    const author = header.replace(/(修改于|发布于|昨天|今天|\d{2}-\d{2}|\d+小时前).*$/, '').trim();
    const timeHint =
      header.match(/(修改于[^·]+|发布于[^·]+|昨天\s*\d{1,2}:\d{2}|今天\s*\d{1,2}:\d{2}|\d+小时前|\d+分钟前|\d{2}-\d{2}\s+\d{1,2}:\d{2})/)?.[1] ||
      '';
    const summary = lines
      .filter(line =>
        line &&
        line !== header &&
        line !== title &&
        !/^(展开|收藏)$/.test(line) &&
        !/^[]+$/.test(line) &&
        !/^\d+$/.test(line)
      )
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 280);

    results.push({
      author,
      time_hint: timeHint,
      title: title || summary.slice(0, 60),
      summary,
      url
    });

    if (results.length >= limit) break;
  }

  return results;
})()
EOF
EXPR="${EXPR/LIMIT_VALUE/${LIMIT}}"

cdp_eval "$TARGET" "$EXPR"
