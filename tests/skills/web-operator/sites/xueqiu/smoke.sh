#!/usr/bin/env bash
# Smoke test: run xueqiu hot.sh and validate the output structure.
# Requires a usable xueqiu.com tab to be open in Chrome.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOT="${SCRIPT_DIR}/../../../scripts/sites/xueqiu/hot.sh"

OUTPUT="$(bash "$HOT" 3)"

printf '%s\n' "$OUTPUT" | jq -e '
  type == "array" and
  length > 0 and
  (.[0].url | type == "string") and
  (.[0].author | type == "string")
' >/dev/null

printf '%s\n' "$OUTPUT"
