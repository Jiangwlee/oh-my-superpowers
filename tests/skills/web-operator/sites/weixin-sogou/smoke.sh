#!/usr/bin/env bash
# Weixin-Sogou search smoke test
# Exits 0 on success, non-zero on failure
# Outputs JSON array of results to stdout

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEARCH_SCRIPT="${SCRIPT_DIR}/../../../scripts/sites/weixin-sogou/search.sh"

QUERY="${1:-Python}"
LIMIT="${2:-3}"

if [[ ! -x "$SEARCH_SCRIPT" ]]; then
  printf 'search script not found: %s\n' "$SEARCH_SCRIPT" >&2
  exit 1
fi

exec bash "$SEARCH_SCRIPT" "$QUERY" "$LIMIT"
