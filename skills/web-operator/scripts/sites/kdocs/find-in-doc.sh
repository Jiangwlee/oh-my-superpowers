#!/usr/bin/env bash
# Search for a keyword inside the currently open WPS document.
# Input: a keyword and an optional doc tab prefix.
# Output: a JSON object with keyword, match_count, and context lines.
# Public interface: kdocs-find-in-doc.sh <keyword> [doc_target_prefix].
#
# The script opens the WPS Find dialog via the magnifier button dropdown.
# It types the keyword, clicks Next, and reads the match count from the DOM.
# It then reads visible text via snap to capture context around the match.
# The document tab must already be open (call open-doc.sh first).
# The script depends on jq and the sibling common.sh helpers.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

usage() {
  printf 'usage: %s <keyword> [doc_target_prefix]\n' "$(basename "$0")" >&2
  exit 1
}

KEYWORD="${1:-}"
DOC_TARGET="${2:-}"

[[ -n "$KEYWORD" ]] || usage

DOC_TARGET="$(kdocs_find_doc_tab "$DOC_TARGET")"
[[ -n "$DOC_TARGET" ]] || { printf 'no open 365.kdocs.cn document tab found\n' >&2; exit 1; }

# Close any existing Find dialog before opening a fresh one.
cdp_eval "$DOC_TARGET" \
  "document.querySelector('.kd-modal-close')?.click()" \
  >/dev/null 2>/dev/null || true
sleep 0.3

# Click the magnifier button to show the Find/Replace dropdown.
cdp_eval "$DOC_TARGET" \
  "document.querySelector('.kd-icon-magnifier')?.closest('button, [class*=\"wo-button\"]')?.click()" \
  >/dev/null

# Wait for the dropdown to appear.
for i in $(seq 1 20); do
  sleep 0.2
  VISIBLE=$(cdp_eval "$DOC_TARGET" \
    "document.querySelector('.component-find-dropdown-item') ? 'yes' : 'no'" 2>/dev/null || echo '"no"')
  [[ "$VISIBLE" == '"yes"' ]] && break
done

# Click the Find item (not Replace).
cdp_eval "$DOC_TARGET" "
  Array.from(document.querySelectorAll('.component-find-dropdown-item'))
    .find(el => el.innerText.includes('Find') && !el.innerText.includes('Replace'))
    ?.click()
" >/dev/null

# Wait for the Find modal to open.
for i in $(seq 1 20); do
  sleep 0.2
  MODAL=$(cdp_eval "$DOC_TARGET" \
    "document.querySelector('.component-find-input') ? 'yes' : 'no'" 2>/dev/null || echo '"no"')
  [[ "$MODAL" == '"yes"' ]] && break
done

# Focus the input and type the keyword.
cdp_eval "$DOC_TARGET" \
  "document.querySelector('.component-find-input')?.focus()" \
  >/dev/null
cdp type "$DOC_TARGET" "$KEYWORD" >/dev/null

sleep 0.5

# Click Next to jump to the first match.
cdp_eval "$DOC_TARGET" "
  Array.from(document.querySelectorAll('button'))
    .find(b => b.innerText.trim() === 'Next')
    ?.click()
" >/dev/null

sleep 1.0

# Read match count from .find-result (format: "N/M" or empty when no match).
MATCH_RAW=$(cdp_eval "$DOC_TARGET" \
  "document.querySelector('.find-result')?.innerText || '0/0'" | jq -r '.')

MATCH_COUNT=$(echo "$MATCH_RAW" | grep -oE '[0-9]+$' || echo "0")

if [[ "$MATCH_COUNT" == "0" ]]; then
  jq -n \
    --arg kw    "$KEYWORD" \
    --argjson mc 0 \
    --argjson ctx '[]' \
    '{keyword: $kw, match_count: $mc, context: $ctx}'
  exit 0
fi

# Read visible text for context around the match.
SNAP_LINES=$(kdocs_snap_text "$DOC_TARGET")
CONTEXT=$(echo "$SNAP_LINES" | jq -Rsc '[split("\n") | .[] | select(length > 0)]')

jq -n \
  --arg  kw      "$KEYWORD" \
  --arg  match   "$MATCH_RAW" \
  --argjson mc   "$MATCH_COUNT" \
  --argjson ctx  "$CONTEXT" \
  '{keyword: $kw, match_position: $match, match_count: $mc, context: $ctx}'
