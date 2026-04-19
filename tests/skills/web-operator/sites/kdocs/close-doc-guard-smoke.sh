#!/usr/bin/env bash
# Smoke test: ensure close-doc.sh refuses to close the main 365.kdocs.cn/latest tab.
# Requires a 365.kdocs.cn/latest tab to be open in Chrome.
# Exits 0 on success, non-zero on failure.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CDP="${SCRIPT_DIR}/../../../scripts/cdp.mjs"
CLOSE_DOC="${SCRIPT_DIR}/../../../scripts/sites/kdocs/close-doc.sh"

MAIN_TARGET="$("$CDP" list_raw | jq -r '
  map(select(.type == "page"))
  | map(select(.url | test("^https://365\\.kdocs\\.cn/(latest|$)")))
  | .[0].targetId // empty
')"

[[ -n "$MAIN_TARGET" ]] || {
  printf 'no usable 365.kdocs.cn/latest tab found\n' >&2
  exit 1
}

set +e
OUTPUT=$(bash "$CLOSE_DOC" "$MAIN_TARGET" 2>&1)
STATUS=$?
set -e

[[ $STATUS -ne 0 ]] || {
  printf 'close-doc.sh unexpectedly accepted the main tab target\n' >&2
  exit 1
}

printf '%s\n' "$OUTPUT" | grep -q 'refusing to close non-document tab'
printf '%s\n' "$OUTPUT"
