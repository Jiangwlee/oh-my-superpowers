#!/usr/bin/env bash
# Smoke test: run kdocs search.sh and validate the output structure.
# Requires a 365.kdocs.cn/latest tab to be open in Chrome.
# Exits 0 on success, non-zero on failure.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEARCH="${SCRIPT_DIR}/../../../scripts/sites/kdocs/search.sh"
OUTPUT=$("$SEARCH" "天基遥感" 3 2>&1)
echo "$OUTPUT" | jq -e '
  type == "array"
  and length > 0
  and .[0].file_key != null
  and (.[0].file_key | startswith("file_"))
  and .[0].title != null
  and (.[0] | has("is_latest"))
' >/dev/null
echo "$OUTPUT"
