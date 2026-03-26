#!/usr/bin/env bash
# read-url — read the main text content of any URL via browser.
# Input:  <url> [--limit N]
# Output: Markdown text (via defuddle) or plain text (fallback).
#
# Three-tier strategy:
#   1. Known sites (reddit, x, xueqiu, taoguba) → delegate to open-post
#   2. Generic: CDP html → defuddle parse --markdown
#   3. Fallback: CDP eval innerText (if defuddle unavailable)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="${OMP_HOME:-$HOME/.oh-my-superpowers}/skills/web-operator"
source "${SCRIPT_DIR}/core/common.sh"

# --- parse arguments ---------------------------------------------------------

URL=""
LIMIT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --limit)
      LIMIT="${2:-}"
      shift 2 ;;
    --help|-h)
      echo "usage: read-url <url> [--limit N]" >&2
      exit 0 ;;
    -*)
      echo "error: unknown option: '$1'" >&2; exit 1 ;;
    *)
      if [[ -z "$URL" ]]; then
        URL="$1"
      else
        echo "error: unexpected argument: '$1'" >&2; exit 1
      fi
      shift ;;
  esac
done

if [[ -z "$URL" ]]; then
  echo "error: URL is required" >&2
  echo "usage: read-url <url> [--limit N]" >&2
  exit 1
fi

# --- tier 1: known sites → open-post ----------------------------------------

domain="${URL#*://}"
domain="${domain%%/*}"
domain="${domain,,}"  # lowercase

case "$domain" in
  *reddit.com)
    exec bash "${SKILL}/scripts/sites/reddit/open-post.sh" "$URL" ;;
  *x.com)
    exec bash "${SKILL}/scripts/sites/x/open-post.sh" "$URL" ;;
  *xueqiu.com)
    exec bash "${SKILL}/scripts/sites/xueqiu/open-post.sh" "$URL" ;;
  *tgb.cn|*taoguba.com.cn)
    exec bash "${SKILL}/scripts/sites/taoguba/open-post.sh" "$URL" ;;
esac

# --- tier 2 & 3: generic path -----------------------------------------------

# Create a dedicated tab for reading (will be closed after extraction)
TARGET="$(create_tab "about:blank")"
if [[ -z "$TARGET" ]]; then
  echo "error: failed to create a browser tab" >&2
  exit 1
fi

# Ensure tab is closed on exit
cleanup_tab() { close_tab "$TARGET"; }
trap 'cleanup_tab' EXIT

# Navigate to URL (waits for load)
cdp_nav "$TARGET" "$URL"

# Extra wait for dynamic content (SPA pages may need JS execution time)
sleep 2

# --- extract content ---------------------------------------------------------

truncate_output() {
  if [[ -n "$LIMIT" ]]; then
    head -c "$LIMIT"
  else
    cat
  fi
}

# Tier 2: CDP html → defuddle (if available)
if command -v defuddle >/dev/null 2>&1; then
  TMPHTML="$(mktemp /tmp/read-url-XXXXXX.html)"
  trap 'rm -f "$TMPHTML"; cleanup_tab' EXIT

  cdp html "$TARGET" > "$TMPHTML" 2>/dev/null

  if output="$(defuddle parse "$TMPHTML" --markdown 2>/dev/null)" && [[ -n "$output" ]]; then
    printf '%s\n' "$output" | truncate_output
    exit 0
  fi
  # defuddle failed on this page, fall through to tier 3
fi

# Tier 3: CDP eval innerText (strip nav/header/footer/aside)
read -r -d '' EXTRACT_JS <<'JSEOF' || true
(() => {
  const remove = ['nav', 'header', 'footer', 'aside', '[role="navigation"]',
                  '[role="banner"]', '[role="contentinfo"]'];
  const clone = document.body.cloneNode(true);
  remove.forEach(sel => clone.querySelectorAll(sel).forEach(el => el.remove()));
  const article = clone.querySelector('article')
    || clone.querySelector('main')
    || clone.querySelector('[role="main"]')
    || clone;
  return article.innerText.replace(/\n{3,}/g, '\n\n').trim();
})()
JSEOF

cdp_eval "$TARGET" "$EXTRACT_JS" | truncate_output
