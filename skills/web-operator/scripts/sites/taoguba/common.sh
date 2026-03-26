#!/usr/bin/env bash
# This file provides shared helpers for the web-operator Taoguba workflows.
# Input: shell arguments, environment variables, and cdp.mjs JSON/text output.
# Output: resolved target prefixes, encoded URLs, and wrapper calls to cdp.mjs.
# Public interface: require_cmd, cdp_list_raw, cdp_eval, taoguba_find_target,
# taoguba_nav_fast, wait_for_url_contains, wait_for_taoguba_text, and
# wait_for_taoguba_selector.
#
# The helpers keep Taoguba workflow scripts small and deterministic.
# taoguba_find_target finds an existing taoguba.com tab or creates a new one.
# They use Page.navigate but tolerate timeout noise from pages that continue
# background loading after the visible content is already ready.
# They rely on jq for JSON handling.
# Failures are printed to stderr and exit non-zero.
# Source this file from sibling scripts; it is not intended to run directly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=../../core/common.sh
source "${SCRIPT_DIR}/../../core/common.sh"

require_cmd jq

taoguba_find_target() {
  local preferred="${1:-}"
  if [[ -n "$preferred" ]]; then
    printf '%s\n' "$preferred"
    return 0
  fi

  find_or_create_tab "https://www.tgb.cn" "tgb.cn"
}

# Use the unified cdp_nav from core/common.sh
# taoguba_nav_fast is kept for backward compatibility but now delegates to cdp_nav
taoguba_nav_fast() {
  cdp_nav "$@"
}

wait_for_url_contains() {
  local target="$1"
  local needle="$2"
  local limit="${3:-12000}"
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

wait_for_taoguba_text() {
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
  throw new Error('Timed out waiting for Taoguba text');
})()
EOF
  expr="${expr/LIMIT_MS/${limit}}"
  expr="${expr/NEEDLE/$(jq -Rn --arg v "$needle" '$v')}"
  cdp_eval "$target" "$expr" >/dev/null
}

wait_for_taoguba_selector() {
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
  throw new Error('Timed out waiting for Taoguba selector');
})()
EOF
  expr="${expr/LIMIT_MS/${limit}}"
  expr="${expr/SELECTOR/$(jq -Rn --arg v "$selector" '$v')}"  cdp_eval "$target" "$expr" >/dev/null
}
