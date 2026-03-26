#!/usr/bin/env bash
# Close the open WPS document tab and verify the main page is still open.
# Input: optional doc tab prefix.
# Output: a JSON object confirming closure and main tab status.
# Public interface: kdocs-close-doc.sh [doc_target_prefix].
#
# The script finds the 365.kdocs.cn/l/ tab and closes it with Page.close.
# If a target is passed explicitly, it must already point to a document tab.
# It then confirms the 365.kdocs.cn/latest main tab is still alive.
# The script depends on jq and the sibling common.sh helpers.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

DOC_TARGET="${1:-}"

DOC_TARGET="$(kdocs_find_doc_tab "$DOC_TARGET")"
[[ -n "$DOC_TARGET" ]] || { printf 'no open 365.kdocs.cn document tab found\n' >&2; exit 1; }

# Read doc URL before closing for the output message.
DOC_URL="$(kdocs_target_url "$DOC_TARGET")"
[[ "$DOC_URL" =~ ^https://365\.kdocs\.cn/l/ ]] || {
  printf 'refusing to close non-document tab: %s\n' "${DOC_URL:-<unknown>}" >&2
  exit 1
}

# Close the document tab.
cdp evalraw "$DOC_TARGET" Page.close '{}' >/dev/null 2>/dev/null || true

sleep 0.5

# Verify main tab is still open.
MAIN_ALIVE=$(cdp_list_raw | jq -r '
  [.[] | select(.type == "page") | select(.url | test("^https://365\\.kdocs\\.cn/(latest|$)"))]
  | length > 0
')

jq -n \
  --arg  doc_target "$DOC_TARGET" \
  --arg  doc_url    "$DOC_URL" \
  --argjson main_ok "$MAIN_ALIVE" \
  '{closed_target: $doc_target, closed_url: $doc_url, main_tab_alive: $main_ok}'
