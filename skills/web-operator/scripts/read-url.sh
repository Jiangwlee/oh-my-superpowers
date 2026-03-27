#!/usr/bin/env bash
# read-url — read the main text content of any URL.
# Input:  <url> [--limit N]
# Output: Markdown text (via defuddle) or plain text (fallback).
#
# Four-tier strategy:
#   1. Known sites (reddit, x, xueqiu, taoguba) → delegate to open-post
#   2. HTTP-first: defuddle parse <URL> --markdown (no browser needed, ~200ms)
#   3. CDP + defuddle: worker tab → navigate → html → defuddle parse
#   4. CDP fallback: worker tab → eval innerText (if defuddle unavailable)
#
# Tier 2 is the fast path for static content (blogs, docs, papers).
# Tier 3-4 use a persistent worker tab to avoid 15s CDP authorization per call.

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

# --- output helper -----------------------------------------------------------

truncate_output() {
  if [[ -n "$LIMIT" ]]; then
    head -c "$LIMIT"
  else
    cat
  fi
}

# --- tier 2: HTTP-first (defuddle parse URL directly, no browser) -----------

if command -v defuddle >/dev/null 2>&1; then
  if output="$(defuddle parse "$URL" --markdown 2>/dev/null)" && [[ -n "$output" ]]; then
    # Quality gate: content must have meaningful text (>100 chars after trimming)
    text_len=$(printf '%s' "$output" | wc -c)
    if [[ "$text_len" -gt 100 ]]; then
      printf '%s\n' "$output" | truncate_output
      exit 0
    fi
    # Quality too low — fall through to CDP path
  fi
fi

# --- tier 3 & 4: CDP path (worker tab) -------------------------------------

# Acquire a persistent worker tab (reused across calls, no 15s auth overhead)
TARGET="$(acquire_worker_tab)"
if [[ -z "$TARGET" ]]; then
  echo "error: failed to acquire a worker tab" >&2
  exit 1
fi

# Cleanup function for worker tab and temp files
TMPHTML=""
cleanup() {
  [[ -n "$TMPHTML" ]] && rm -f "$TMPHTML"
  release_worker_tab "$TARGET"
}
trap cleanup EXIT

# Navigate to URL (waits for load)
cdp_nav "$TARGET" "$URL"

# Extra wait for dynamic content (SPA pages may need JS execution time)
sleep 2

# Tier 3: CDP html → defuddle (if available)
if command -v defuddle >/dev/null 2>&1; then
  TMPHTML="$(mktemp /tmp/read-url-XXXXXX.html)"

  cdp html "$TARGET" > "$TMPHTML" 2>/dev/null

  if output="$(defuddle parse "$TMPHTML" --markdown 2>/dev/null)" && [[ -n "$output" ]]; then
    printf '%s\n' "$output" | truncate_output
    exit 0
  fi
  # defuddle failed on this page, fall through to tier 4
fi

# Tier 4: CDP eval innerText (strip nav/header/footer/aside)
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
