#!/usr/bin/env bash
# Open a WPS 365 document by file key and return its outline and visible text.
# Input: a file key (e.g. file_503025782506) and optional main tab prefix.
# Output: a JSON object with title, url, doc_target, word_count, and visible_text.
# Public interface: kdocs-open-doc.sh <file_key> [main_target_prefix].
#
# The script finds the item matching file_key in the current DOM. If the search
# panel from search.sh is still open the item will be found there. Otherwise
# the script navigates to 365.kdocs.cn/latest and looks in the recent list.
# It clicks the document title, which opens a new tab at 365.kdocs.cn/l/<id>.
# It waits for the document to load, then reads accessible text via snap.
# The script depends on jq and the sibling common.sh helpers.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

require_cmd jq

usage() {
  printf 'usage: %s <file_key> [main_target_prefix]\n' "$(basename "$0")" >&2
  exit 1
}

FILE_KEY="${1:-}"
MAIN_TARGET="${2:-}"

[[ -n "$FILE_KEY" ]] || usage
[[ "$FILE_KEY" =~ ^file_[0-9]+$ ]] || {
  printf 'file_key must look like file_<numeric_id>\n' >&2
  exit 1
}

MAIN_TARGET="$(kdocs_find_main_tab "$MAIN_TARGET")"
[[ -n "$MAIN_TARGET" ]] || { printf 'no usable 365.kdocs.cn/latest tab found\n' >&2; exit 1; }

# Derive the document URL directly from the file key (file_<id> → /l/<id>).
FILE_NUM="${FILE_KEY#file_}"
DOC_URL="https://365.kdocs.cn/l/${FILE_NUM}"

# Record existing doc tab IDs before opening.
BEFORE_IDS=$(cdp_list_raw | jq -r '
  .[] | select(.type == "page") | select(.url | startswith("https://365.kdocs.cn/l/")) | .targetId
')

# Open the document in a new tab via CDP (window.open is blocked by the popup blocker).
cdp evalraw "$MAIN_TARGET" Target.createTarget \
  "$(jq -n --arg url "$DOC_URL" '{"url":$url}')" >/dev/null

# Poll until a new 365.kdocs.cn/l/ tab appears.
DOC_TARGET=""
for i in $(seq 1 40); do
  sleep 0.5
  while IFS= read -r tid; do
    if [[ -n "$tid" ]] && ! grep -qF "$tid" <<<"$BEFORE_IDS"; then
      DOC_TARGET="$tid"
      break 2
    fi
  done < <(cdp_list_raw | jq -r '
    .[] | select(.type == "page") | select(.url | startswith("https://365.kdocs.cn/l/")) | .targetId
  ')
done

[[ -n "$DOC_TARGET" ]] || { printf 'document tab did not open in time\n' >&2; exit 1; }

# Wait for document content to load.
wait_for_kdocs_doc "$DOC_TARGET"

# Read document title (cdp eval returns raw string, not JSON-encoded).
TITLE=$(cdp_eval "$DOC_TARGET" "document.title")
# DOC_URL is already known from the file key derivation above.

# Extract word count from accessibility tree status bar.
WORD_COUNT=$(cdp snap "$DOC_TARGET" 2>/dev/null \
  | grep -oP '(?<=\[StaticText\] )\d+' \
  | tail -1 || echo "0")

# Extract visible document text.
SNAP_LINES=$(kdocs_snap_text "$DOC_TARGET")
VISIBLE_TEXT=$(echo "$SNAP_LINES" | jq -Rsc '[split("\n") | .[] | select(length > 0)]')

# Build output.
jq -n \
  --arg title    "$TITLE" \
  --arg url      "$DOC_URL" \
  --arg target   "$DOC_TARGET" \
  --arg wc       "$WORD_COUNT" \
  --argjson text "$VISIBLE_TEXT" \
  '{title: $title, url: $url, doc_target: $target, word_count: ($wc | tonumber), visible_text: $text}'
