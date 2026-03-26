#!/usr/bin/env bash
# Search 365.kdocs.cn documents using the Full Text Search panel.
# Input: a query string, optional result limit, and optional target prefix.
# Output: a JSON array of document results with version ranking.
# Public interface: kdocs-search.sh <query> [limit] [target_prefix].
#
# The script reuses the 365.kdocs.cn/latest tab discovered through cdp.mjs.
# It opens the search panel (a modal overlay; no URL change occurs).
# It extracts from the Full Text section first (includes snippets), then from
# the File Name section for additional results not found in Full Text.
# Results are grouped by base name (title stripped of version/date suffixes),
# sorted by version number and date, and the newest is marked is_latest: true.
# The default and maximum limit is 10.
# The script depends on jq and the sibling common.sh helpers.

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

TARGET="$(kdocs_find_main_tab "$TARGET")"
[[ -n "$TARGET" ]] || { printf 'no usable 365.kdocs.cn/latest tab found\n' >&2; exit 1; }

# Navigate to main page to ensure clean state.
cdp_nav "$TARGET" "https://365.kdocs.cn/latest"

# Open the search panel by clicking the search bar.
cdp_eval "$TARGET" \
  "document.querySelector('[placeholder*=\"Search by document\"]')?.click()" \
  >/dev/null

# Give the panel time to open before typing.
sleep 0.6

# Type the query into the focused search input.
cdp type "$TARGET" "$QUERY" >/dev/null

# Wait for search result items to appear. The main latest page also uses
# `.item-container`, so polling that generic selector can race and return
# before the search panel has populated its own result lists.
for i in $(seq 1 40); do
  sleep 0.3
  SEARCH_READY=$(cdp_eval "$TARGET" "
    (() => {
      const fullText = document.querySelectorAll(
        '.search-sdk-content__allTab__fullContent--result__content__list .item-container'
      ).length;
      const fileName = document.querySelectorAll(
        '.search-sdk-content__allTab__fileName--result__content__list .item-container'
      ).length;
      return (fullText + fileName) > 0 ? 'yes' : 'no';
    })()
  " 2>/dev/null || echo '"no"')
  [[ "$SEARCH_READY" == '"yes"' ]] && break
done

# Extract results from Full Text and File Name sections.
read -r -d '' EXPR <<'EOF' || true
(() => {
  const limit = LIMIT_VALUE;
  const results = [];
  const seen = new Set();

  const extractItem = (el, hasSnippet) => {
    const key = el.getAttribute('data-key') || '';
    if (!key || seen.has(key)) return null;
    seen.add(key);

    const title = el.getAttribute('aria-label') || '';
    const rawLines = (el.innerText || '').split('\n').map(s => s.trim()).filter(Boolean);

    // Line 0: title (same as aria-label)
    // Line 1: last opened info ("Today HH:MM Opened by you" etc.)
    // Line 2: location path
    // Remaining lines: snippet text (fulltext) or creator (filename)
    const lastOpened = rawLines[1] || '';
    const location = rawLines[2] || '';
    const rest = rawLines.slice(3);

    let creator = '';
    let snippetLines = [];
    if (rest.length > 0 && rest[rest.length - 1].startsWith('Created by')) {
      creator = rest[rest.length - 1].replace('Created by ', '');
      snippetLines = hasSnippet ? rest.slice(0, -1) : [];
    } else {
      snippetLines = hasSnippet ? rest : [];
    }
    const snippet = snippetLines.join(' ').replace(/\s+/g, ' ').slice(0, 400);

    return { file_key: key, title, last_opened: lastOpened, location, creator, snippet };
  };

  // Full Text results have snippets.
  const ftList = document.querySelector(
    '.search-sdk-content__allTab__fullContent--result__content__list'
  );
  if (ftList) {
    for (const el of ftList.querySelectorAll('.item-container')) {
      const item = extractItem(el, true);
      if (item) results.push(item);
      if (results.length >= limit) break;
    }
  }

  // File Name results fill the remainder.
  const fnList = document.querySelector(
    '.search-sdk-content__allTab__fileName--result__content__list'
  );
  if (fnList && results.length < limit) {
    for (const el of fnList.querySelectorAll('.item-container')) {
      const item = extractItem(el, false);
      if (item) results.push(item);
      if (results.length >= limit) break;
    }
  }

  return results;
})()
EOF
EXPR="${EXPR/LIMIT_VALUE/${LIMIT}}"

RAW=$(cdp_eval "$TARGET" "$EXPR")

# Add is_latest flag by grouping docs on their base name and ranking by version + date.
jq '
  map(
    . + {
      _base: (
        .title
        | ascii_downcase
        | sub("\\.[a-z0-9]+$"; "")
        | gsub("-v[0-9]+[^.]*$"; "")
        | gsub("-[0-9]{8}[^.]*$"; "")
      ),
      _ver: (
        try (.title | capture("-v(?P<n>[0-9]+)") | .n | tonumber) catch 0
      ),
      _date: (
        try (.title | capture("-(?P<d>[0-9]{8})") | .d | tonumber) catch 0
      )
    }
  )
  | group_by(._base)
  | map(
      sort_by([._ver, ._date]) | reverse
      | to_entries
      | map(.value + { is_latest: (.key == 0) })
    )
  | flatten
  | map(del(._base, ._ver, ._date))
' <<<"$RAW"
