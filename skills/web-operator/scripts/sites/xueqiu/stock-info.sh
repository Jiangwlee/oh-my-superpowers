#!/usr/bin/env bash
# Extract the latest stock announcements and discussions from a xueqiu.com stock page.
# Input: a stock symbol or stock URL, optional result limit, and optional target prefix.
# Output: a JSON object with stock_url, announcements, and discussions arrays.
# Public interface: xueqiu-stock-info.sh <symbol_or_stock_url> [limit] [target_prefix].

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

usage() {
  printf 'usage: %s <symbol_or_stock_url> [limit] [target_prefix]\n' "$(basename "$0")" >&2
  exit 1
}

resolve_stock_url() {
  local input="$1"
  if [[ "$input" =~ ^https://xueqiu\.com/S/[A-Za-z0-9._-]+ ]]; then
    normalize_xueqiu_url "$input"
    return 0
  fi

  if [[ "$input" =~ ^[A-Za-z0-9._-]+$ ]]; then
    printf 'https://xueqiu.com/S/%s\n' "${input^^}"
    return 0
  fi

  printf 'stock input must be a xueqiu stock URL or stock symbol/code\n' >&2
  return 1
}

click_stock_tab() {
  local target="$1"
  local tab_text="$2"
  local expr
  read -r -d '' expr <<'EOF' || true
(() => {
  const targetText = TAB_TEXT;
  const tab = [...document.querySelectorAll('.stock-timeline-tabs a')]
    .find(a => (a.innerText || '').trim() === targetText);
  if (!tab) throw new Error(`Missing stock tab: ${targetText}`);
  tab.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
  return targetText;
})()
EOF
  expr="${expr/TAB_TEXT/$(json_string "$tab_text")}"
  cdp_eval_retry "$target" "$expr" >/dev/null
}

wait_for_stock_tab_active() {
  local target="$1"
  local tab_text="$2"
  local limit="${3:-12000}"
  local expr
  read -r -d '' expr <<'EOF' || true
(async () => {
  const expected = TAB_TEXT;
  const deadline = Date.now() + LIMIT_MS;
  while (Date.now() < deadline) {
    const active = [...document.querySelectorAll('.stock-timeline-tabs a.active')]
      .map(a => (a.innerText || '').trim())[0] || '';
    if (active === expected) return active;
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for stock tab: ${expected}`);
})()
EOF
  expr="${expr/TAB_TEXT/$(json_string "$tab_text")}"
  expr="${expr/LIMIT_MS/${limit}}"
  cdp_eval_retry "$target" "$expr" >/dev/null
}

wait_for_stock_items() {
  local target="$1"
  local limit="${2:-12000}"
  local expr
  read -r -d '' expr <<'EOF' || true
(async () => {
  const deadline = Date.now() + LIMIT_MS;
  while (Date.now() < deadline) {
    const count = document.querySelectorAll('.status-list article.timeline__item').length;
    if (count > 0) return count;
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('Timed out waiting for stock timeline items');
})()
EOF
  expr="${expr/LIMIT_MS/${limit}}"
  cdp_eval_retry "$target" "$expr" >/dev/null
}

wait_for_stock_item_kind() {
  local target="$1"
  local kind="$2"
  local limit="${3:-12000}"
  local expr
  read -r -d '' expr <<'EOF' || true
(async () => {
  const expectedKind = EXPECTED_KIND;
  const deadline = Date.now() + LIMIT_MS;
  const normalizeUrl = (href) => {
    if (!href) return '';
    const url = new URL(href, location.origin);
    url.search = '';
    url.hash = '';
    return url.href;
  };

  while (Date.now() < deadline) {
    const items = [...document.querySelectorAll('.status-list article.timeline__item')];
    if (!items.length) {
      await new Promise(resolve => setTimeout(resolve, 250));
      continue;
    }

    const first = items[0];
    const dateHref = normalizeUrl(first.querySelector('a.date-and-source[href]')?.getAttribute('href') || '');
    const pdfHref = normalizeUrl(first.querySelector('a.status-link[href]')?.getAttribute('href') || '');
    const itemHrefs = [...first.querySelectorAll('a[href]')].map(a => normalizeUrl(a.getAttribute('href') || ''));
    const hasAnnouncementShape = Boolean(pdfHref) || /\/S\/[A-Za-z0-9._-]+\/[0-9]+$/.test(dateHref);
    const hasDiscussionShape = itemHrefs.some(href => /^https:\/\/xueqiu\.com\/(?:[A-Za-z0-9_]+|[0-9]+)\/[0-9]+(?:#comment)?$/.test(href));

    if (expectedKind === 'announcement' && hasAnnouncementShape) return 'announcement';
    if (expectedKind === 'discussion' && hasDiscussionShape && !hasAnnouncementShape) return 'discussion';

    await new Promise(resolve => setTimeout(resolve, 250));
  }

  throw new Error(`Timed out waiting for stock items kind: ${expectedKind}`);
})()
EOF
  expr="${expr/EXPECTED_KIND/$(json_string "$kind")}"
  expr="${expr/LIMIT_MS/${limit}}"
  cdp_eval_retry "$target" "$expr" >/dev/null
}

STOCK_INPUT="${1:-}"
LIMIT="${2:-10}"
TARGET="${3:-}"

[[ -n "$STOCK_INPUT" ]] || usage
[[ "$LIMIT" =~ ^[0-9]+$ ]] || { printf 'limit must be an integer\n' >&2; exit 1; }
(( LIMIT > 0 )) || { printf 'limit must be greater than zero\n' >&2; exit 1; }
(( LIMIT <= 10 )) || LIMIT=10

TARGET="$(xueqiu_find_target "$TARGET")"
[[ -n "$TARGET" ]] || { printf 'no usable xueqiu.com tab found\n' >&2; exit 1; }

STOCK_URL="$(resolve_stock_url "$STOCK_INPUT")"

cdp nav "$TARGET" "$STOCK_URL" >/dev/null
wait_for_url_contains "$TARGET" "/S/"
wait_for_xueqiu_selector "$TARGET" '.stock-timeline-tabs'

click_stock_tab "$TARGET" "公告"
wait_for_stock_tab_active "$TARGET" "公告"
wait_for_stock_items "$TARGET"
wait_for_stock_item_kind "$TARGET" "announcement"

read -r -d '' EXTRACT_ANNOUNCEMENTS_EXPR <<'EOF' || true
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
  const cleanText = (text) => String(text || '').replace(/\s+/g, ' ').trim();
  const splitLines = (node) => rawText(node).split(/\n+/).map(s => s.trim()).filter(Boolean);
  const announcementHrefRe = /\/S\/[A-Za-z0-9._-]+\/[0-9]+$/;

  return [...document.querySelectorAll('.status-list article.timeline__item')]
    .map((item) => {
      const dateLink = item.querySelector('a.date-and-source[href]');
      const pdfLink = item.querySelector('a.status-link[href]');
      const dateHref = normalizeUrl(dateLink?.getAttribute('href') || '');
      const pdfHref = normalizeUrl(pdfLink?.getAttribute('href') || '');
      if (!pdfHref && !announcementHrefRe.test(dateHref)) return null;
      const aiSummary = cleanText(rawText(item.querySelector('.ai_abs_con')));
      const contentLines = splitLines(item.querySelector('.timeline__item__content'));
      const title = cleanText((contentLines[0] || '').replace(/\s*网页链接\s*$/g, ''));
      const summary = aiSummary || cleanText(contentLines.slice(1).join(' ')).slice(0, 280);
      const timeText = cleanText(rawText(dateLink)).split('·')[0].trim();
      return {
        title,
        time: timeText,
        summary,
        link: pdfHref || dateHref
      };
    })
    .filter(item => item && item.title && item.link)
    .slice(0, limit);
})()
EOF
EXTRACT_ANNOUNCEMENTS_EXPR="${EXTRACT_ANNOUNCEMENTS_EXPR/LIMIT_VALUE/${LIMIT}}"
ANNOUNCEMENTS="$(cdp_eval "$TARGET" "$EXTRACT_ANNOUNCEMENTS_EXPR")"

click_stock_tab "$TARGET" "讨论"
wait_for_stock_tab_active "$TARGET" "讨论"
wait_for_stock_items "$TARGET" 15000
wait_for_stock_item_kind "$TARGET" "discussion" 15000

read -r -d '' EXTRACT_DISCUSSIONS_EXPR <<'EOF' || true
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
  const cleanText = (text) => String(text || '').replace(/\s+/g, ' ').trim();
  const splitLines = (node) => rawText(node).split(/\n+/).map(s => s.trim()).filter(Boolean);
  const postHrefRe = /^https:\/\/xueqiu\.com\/(?:[A-Za-z0-9_]+|[0-9]+)\/[0-9]+(?:#comment)?$/;

  return [...document.querySelectorAll('.status-list article.timeline__item')]
    .map((item) => {
      const dateLink = item.querySelector('a.date-and-source[href]');
      const contentLines = splitLines(item.querySelector('.timeline__item__content, .timeline__item__bd'));
      const forwardLines = splitLines(item.querySelector('.timeline__item__forward__content, .timeline__item__forward'));
      const titleNode = item.querySelector('.timeline__item__title, h1, h2, h3, h4, h5');
      const itemHref = [...item.querySelectorAll('a[href]')]
        .map(a => normalizeUrl(a.getAttribute('href') || ''))
        .find(href => postHrefRe.test(href) && !href.includes('/S/'));
      if (!itemHref) return null;
      const title = cleanText(rawText(titleNode)) || cleanText(contentLines[0] || '').slice(0, 80);
      const summarySource = contentLines.length > 1 ? contentLines.slice(1) : contentLines;
      const summary = cleanText((summarySource.concat(forwardLines)).join(' ')).slice(0, 280);
      const timeText = cleanText(rawText(dateLink)).split('·')[0].trim();
      return {
        title,
        time: timeText,
        summary,
        link: itemHref
      };
    })
    .filter(item => item && item.title && item.link)
    .slice(0, limit);
})()
EOF
EXTRACT_DISCUSSIONS_EXPR="${EXTRACT_DISCUSSIONS_EXPR/LIMIT_VALUE/${LIMIT}}"
DISCUSSIONS="$(cdp_eval "$TARGET" "$EXTRACT_DISCUSSIONS_EXPR")"

jq -n \
  --arg stock_url "$STOCK_URL" \
  --argjson announcements "$ANNOUNCEMENTS" \
  --argjson discussions "$DISCUSSIONS" \
  '{
    stock_url: $stock_url,
    announcements: $announcements,
    discussions: $discussions
  }'
