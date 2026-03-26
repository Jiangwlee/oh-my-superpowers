#!/usr/bin/env bash
# This file provides shared helpers for the web-operator reddit.com workflows.
# Input: shell arguments, environment variables, and cdp.mjs JSON/text output.
# Output: resolved target prefixes, encoded URLs, and wrapper calls to cdp.mjs.
# Public interface: require_cmd, url_encode, cdp_list_raw, cdp_eval,
# cdp_evalraw, reddit_find_target, reddit_nav_fast, wait_for_url_contains,
# wait_for_reddit_selector, and wait_for_reddit_text.
#
# The helpers keep search.sh and open-post.sh deterministic.
# reddit_find_target finds an existing reddit.com tab or creates a new one.
# They use Page.navigate via evalraw because Reddit often keeps background
# activity alive after navigation even when the visible page is already ready.
# They rely on jq for JSON handling and URL encoding.
# Failures are printed to stderr and exit non-zero.
# Source this file from sibling scripts; it is not intended to run directly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=../../core/common.sh
source "${SCRIPT_DIR}/../../core/common.sh"

require_cmd jq

reddit_find_target() {
  local preferred="${1:-}"
  if [[ -n "$preferred" ]]; then
    printf '%s\n' "$preferred"
    return 0
  fi

  find_or_create_tab "https://www.reddit.com" "reddit.com"
}

# Use the unified cdp_nav from core/common.sh
# reddit_nav_fast is kept for backward compatibility but now delegates to cdp_nav
reddit_nav_fast() {
  cdp_nav "$@"
}

wait_for_url_contains() {
  local target="$1"
  local needle="$2"
  local limit="${3:-10000}"
  local expr
  read -r -d '' expr <<'EOF' || true
(async () => {
  const deadline = Date.now() + LIMIT_MS;
  while (Date.now() < deadline) {
    if (location.href.includes(NEEDLE)) return location.href;
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('Timed out waiting for URL match');
})()
EOF
  expr="${expr/LIMIT_MS/${limit}}"
  expr="${expr/NEEDLE/$(jq -Rn --arg v "$needle" '$v')}"
  cdp_eval "$target" "$expr" >/dev/null
}

wait_for_reddit_selector() {
  local target="$1"
  local selector="$2"
  local limit="${3:-12000}"
  local expr
  read -r -d '' expr <<'EOF' || true
(async () => {
  const deadline = Date.now() + LIMIT_MS;
  while (Date.now() < deadline) {
    if (document.querySelector(SELECTOR)) return 'READY';
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('Timed out waiting for Reddit selector');
})()
EOF
  expr="${expr/LIMIT_MS/${limit}}"
  expr="${expr/SELECTOR/$(jq -Rn --arg v "$selector" '$v')}"
  cdp_eval "$target" "$expr" >/dev/null
}

wait_for_reddit_text() {
  local target="$1"
  local needle="$2"
  local limit="${3:-12000}"
  local expr
  read -r -d '' expr <<'EOF' || true
(async () => {
  const deadline = Date.now() + LIMIT_MS;
  while (Date.now() < deadline) {
    if ((document.body?.innerText || '').includes(NEEDLE)) return 'READY';
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('Timed out waiting for Reddit text');
})()
EOF
  expr="${expr/LIMIT_MS/${limit}}"
  expr="${expr/NEEDLE/$(jq -Rn --arg v "$needle" '$v')}"
  cdp_eval "$target" "$expr" >/dev/null
}
