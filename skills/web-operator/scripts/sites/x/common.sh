#!/usr/bin/env bash
# This file provides shared helpers for the web-operator x.com workflow scripts.
# Input: shell arguments, environment variables, and cdp.mjs JSON/text output.
# Output: resolved target prefixes, encoded URLs, and wrapper calls to cdp.mjs.
# Public interface: require_cmd, x_find_target, cdp_list_raw, cdp_nav,
# cdp_eval, json_string, url_encode, and wait_for_x_article.
#
# The helpers keep search.sh and open-post.sh deterministic and small.
# x_find_target finds an existing x.com tab or creates a new one.
# They rely on jq for robust JSON parsing and URI encoding.
# They return plain strings or forward cdp.mjs output unchanged.
# Failures are reported to stderr and exit non-zero.
# Source this file from other scripts in this directory; it is not intended to
# be executed directly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=../../core/common.sh
source "${SCRIPT_DIR}/../../core/common.sh"

require_cmd jq

json_string() {
  jq -Rn --arg v "$1" '$v'
}

x_find_target() {
  local preferred="${1:-}"
  if [[ -n "$preferred" ]]; then
    printf '%s\n' "$preferred"
    return 0
  fi

  find_or_create_tab "https://x.com" "x.com"
}

cdp_nav() {
  local target="$1"
  local url="$2"
  cdp nav "$target" "$url" >/dev/null
}

wait_for_x_article() {
  local target="$1"
  local limit="${2:-10000}"
  local expr
  read -r -d '' expr <<'EOF' || true
(async () => {
  const deadline = Date.now() + LIMIT_MS;
  // Phase 1: wait for stale content to clear (SPA navigation resets DOM)
  const hadOldEmpty = !!document.querySelector('[data-testid="empty_state_header_text"]');
  if (hadOldEmpty) {
    while (Date.now() < deadline) {
      if (!document.querySelector('[data-testid="empty_state_header_text"]')) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
  }
  // Phase 2: wait for new content (article or fresh empty state)
  while (Date.now() < deadline) {
    if (document.querySelector('article')) return 'READY';
    if (document.querySelector('[data-testid="empty_state_header_text"]')) return 'EMPTY';
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  return 'TIMEOUT';
})()
EOF
  expr="${expr/LIMIT_MS/${limit}}"
  cdp_eval "$target" "$expr" >/dev/null
}
