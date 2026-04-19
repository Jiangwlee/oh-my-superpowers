#!/usr/bin/env bash
# Smoke test: run xueqiu stock-info.sh and validate the output structure.
# Requires a usable xueqiu.com tab to be open in Chrome.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${SCRIPT_DIR}/../../../scripts/sites/xueqiu/stock-info.sh"
SYMBOL="${1:-00700}"

OUTPUT="$(bash "$SCRIPT" "$SYMBOL" 3)"

printf '%s\n' "$OUTPUT" | jq -e '
  type == "object" and
  (.stock_url | type == "string") and
  (.announcements | type == "array") and
  (.discussions | type == "array") and
  (.announcements | length > 0) and
  (.discussions | length > 0) and
  (.announcements[0].title | type == "string") and
  (.announcements[0].time | type == "string") and
  (.announcements[0].summary | type == "string") and
  (.announcements[0].link | type == "string") and
  (.announcements[0].link | test("^https://stockn\\.xueqiu\\.com/|^https://xueqiu\\.com/S/")) and
  (.discussions[0].title | type == "string") and
  (.discussions[0].time | type == "string") and
  (.discussions[0].summary | type == "string") and
  (.discussions[0].link | type == "string") and
  (.discussions[0].link | test("^https://xueqiu\\.com/[A-Za-z0-9_]+/[0-9]+"))
' >/dev/null

printf '%s\n' "$OUTPUT"
