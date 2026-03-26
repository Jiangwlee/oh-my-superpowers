#!/usr/bin/env bash
# Shared core helpers for all web-operator site workflows.
# Input: environment variables and cdp.mjs JSON/text output.
# Output: tab management, URL encoding, and CDP wrappers.
# Public interface: find_or_create_tab, create_tab, find_existing_tab,
# require_cmd, url_encode, cdp, cdp_list_raw, cdp_eval, cdp_nav.
#
# This file provides abstraction over tab lifecycle management:
# - find_or_create_tab: finds existing site tab or creates new one
# - find_existing_tab: finds tab matching URL patterns (with priority)
# - create_tab: creates new tab and navigates to homepage
# - cdp_nav: unified navigation function with optional fast mode
#
# Source this from site-specific common.sh files.
# Requires: jq, and cdp.mjs in the parent directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CDP_SCRIPT="${SCRIPT_DIR}/../cdp.mjs"

# Check if required command exists
require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    printf 'missing required command: %s\n' "$cmd" >&2
    exit 1
  fi
}

# URL encode a string
url_encode() {
  jq -nr --arg v "$1" '$v|@uri'
}

# Invoke cdp.mjs
cdp() {
  "$CDP_SCRIPT" "$@"
}

# Get raw page list as JSON
cdp_list_raw() {
  cdp list_raw
}

# Evaluate JS expression in a tab
cdp_eval() {
  local target="$1"
  local expr="$2"
  cdp eval "$target" "$expr"
}

# Navigate to URL using cdp.mjs nav command (waits for load completion)
# Usage: cdp_nav <target> <url> [fast]
#   If fast=true, uses evalraw Page.navigate without waiting for load
cdp_nav() {
  local target="$1"
  local url="$2"
  local fast="${3:-false}"
  
  if [[ "$fast" == "true" ]]; then
    # Fast navigation: use Page.navigate without waiting for loadEventFired
    local params
    params="$(jq -nc --arg url "$url" '{url: $url}')"
    cdp evalraw "$target" "Page.navigate" "$params" >/dev/null 2>&1 || true
  else
    # Normal navigation: wait for load completion
    cdp nav "$target" "$url" >/dev/null
  fi
}

# Create a new tab and navigate to homepage
# Usage: create_tab <homepage_url>
create_tab() {
  local homepage="$1"
  local target
  
  # Create new tab
  target=$(cdp open "about:blank" 2>/dev/null | grep -oE '[A-F0-9]{8,}' | head -1)
  [[ -n "$target" ]] || { printf 'failed to create new tab\n' >&2; return 1; }
  
  # Navigate to homepage
  cdp nav "$target" "$homepage" >/dev/null 2>&1 || true
  sleep 2
  
  printf '%s\n' "$target"
}

# Find existing tab for a specific domain
# Usage: find_existing_tab <domain> [homepage_url]
#   domain: domain name for URL matching, e.g.: "baidu.com"
#   homepage_url: optional, if provided also matches this exact URL
find_existing_tab() {
  local domain="$1"
  local homepage="${2:-}"
  local pages
  pages="$(cdp_list_raw)"
  
  # Build jq filter for URL patterns
  local search_pattern="test(\"^https://[^/]*${domain}\")"
  
  jq -r --arg domain "$domain" --arg homepage "$homepage" '
    map(select(.type == "page")) as $all
    | ($all | map(select(.url | test("^https://[^/]*" + $domain + "/")))) as $domain_tabs
    | if $homepage != "" then
        ($domain_tabs | map(select(.url | startswith($homepage)))) as $homepage_tabs
        | if ($homepage_tabs | length) > 0 then $homepage_tabs else $domain_tabs end
      else $domain_tabs
      end
    | [.[].targetId]
    | reduce .[] as $id ([]; if index($id) then . else . + [$id] end)
    | .[0] // empty
  ' <<<"$pages"
}

# Find existing tab or create new one for a site
# Usage: find_or_create_tab <homepage_url> [domain]
#   homepage_url: site homepage URL, e.g.: "https://www.baidu.com"
#   domain: optional domain for matching (derived from homepage if not provided)
find_or_create_tab() {
  local homepage="$1"
  local domain="${2:-}"
  local target
  
  # Extract domain from homepage if not provided
  if [[ -z "$domain" ]]; then
    domain=$(jq -nr --arg url "$homepage" '$url | capture("https?://([^/]+)").string')
  fi
  
  # Try to find existing tab
  target=$(find_existing_tab "$domain" "$homepage")
  
  # If not found, create new tab
  if [[ -z "$target" ]]; then
    target=$(create_tab "$homepage")
  fi
  
  printf '%s\n' "$target"
}
