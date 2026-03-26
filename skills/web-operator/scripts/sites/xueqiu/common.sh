#!/usr/bin/env bash
# Shared helpers for the web-operator xueqiu.com workflow scripts.
# Input: shell arguments plus cdp.mjs JSON/text output from a local browser tab.
# Output: resolved target prefixes, encoded URLs, normalized URLs, and waits.
# Public interface: require_cmd, json_string, url_encode, normalize_xueqiu_url,
# cdp_list_raw, cdp_eval, cdp_eval_retry, cdp_evalraw, xueqiu_find_target,
# xueqiu_nav_fast, wait_for_url_contains, wait_for_xueqiu_selector, and
# wait_for_xueqiu_text.
#
# The helpers keep site scripts deterministic and aligned with the repository's
# common shell conventions. xueqiu_find_target finds an existing xueqiu.com tab
# or creates a new one.
# Source this file from other scripts; it is not intended to run directly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=../../core/common.sh
source "${SCRIPT_DIR}/../../core/common.sh"

require_cmd jq

json_string() {
  jq -Rn --arg v "$1" '$v'
}

normalize_xueqiu_url() {
  jq -nr --arg href "$1" '
    ($href | if test("^https?://") then . else "https://xueqiu.com" + . end)
    | sub("\\?.*$"; "")
    | sub("#.*$"; "")
  '
}

cdp_eval_retry() {
  local target="$1"
  local expr="$2"
  local attempts="${3:-24}"
  local delay="${4:-0.25}"
  local output=''
  local i

  for ((i = 0; i < attempts; i += 1)); do
    if output="$(cdp_eval "$target" "$expr" 2>&1)"; then
      printf '%s\n' "$output"
      return 0
    fi
    if grep -qiE 'Inspected target navigated or closed|Cannot find context|Execution context was destroyed' <<<"$output"; then
      sleep "$delay"
      continue
    fi
    printf '%s\n' "$output" >&2
    return 1
  done

  printf '%s\n' "$output" >&2
  return 1
}

cdp_evalraw() {
  local target="$1"
  shift
  cdp evalraw "$target" "$@" >/dev/null
}

xueqiu_find_target() {
  local preferred="${1:-}"
  if [[ -n "$preferred" ]]; then
    printf '%s\n' "$preferred"
    return 0
  fi

  find_or_create_tab "https://xueqiu.com" "xueqiu.com"
}

# Use the unified cdp_nav from core/common.sh
# xueqiu_nav_fast is kept for backward compatibility but now delegates to cdp_nav
xueqiu_nav_fast() {
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
  throw new Error('Timed out waiting for Xueqiu URL match');
})()
EOF
  expr="${expr/LIMIT_MS/${limit}}"
  expr="${expr/NEEDLE/$(jq -Rn --arg v "$needle" '$v')}"
  cdp_eval_retry "$target" "$expr" >/dev/null
}

wait_for_xueqiu_selector() {
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
  throw new Error('Timed out waiting for Xueqiu selector');
})()
EOF
  expr="${expr/LIMIT_MS/${limit}}"
  expr="${expr/SELECTOR/$(jq -Rn --arg v "$selector" '$v')}"
  cdp_eval_retry "$target" "$expr" >/dev/null
}

wait_for_xueqiu_text() {
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
  throw new Error('Timed out waiting for Xueqiu text');
})()
EOF
  expr="${expr/LIMIT_MS/${limit}}"
  expr="${expr/NEEDLE/$(jq -Rn --arg v "$needle" '$v')}"
  cdp_eval_retry "$target" "$expr" >/dev/null
}
