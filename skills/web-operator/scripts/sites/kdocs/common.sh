#!/usr/bin/env bash
# Shared helpers for the web-operator 365.kdocs.cn workflow scripts.
# Input: shell arguments, environment variables, and cdp.mjs JSON/text output.
# Output: resolved target prefixes, encoded URLs, and wrapper calls to cdp.mjs.
# Public interface: require_cmd, json_string, url_encode, cdp_list_raw, cdp_nav,
# cdp_eval, kdocs_find_main_tab, kdocs_find_doc_tab, wait_for_kdocs_items,
# wait_for_kdocs_doc, wait_for_kdocs_ai_box, wait_for_kdocs_ai_answer,
# kdocs_snap_text.
#
# kdocs_find_main_tab selects a reusable 365.kdocs.cn main tab.
# If none is open, it creates one at https://365.kdocs.cn/ and waits for it.
# kdocs_find_doc_tab selects an open 365.kdocs.cn/l/ document tab.
# wait_for_kdocs_items polls until search result .item-container nodes appear.
# wait_for_kdocs_doc polls until document.title changes from "WPS 365".
# wait_for_kdocs_ai_box polls until the Docs Chat textarea and send button exist.
# wait_for_kdocs_ai_answer waits for a new Docs Chat answer to finish rendering.
# kdocs_snap_text runs cdp snap and strips toolbar and UI labels from StaticText.
# Source this file from other scripts; it is not intended to be executed directly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=../../core/common.sh
source "${SCRIPT_DIR}/../../core/common.sh"

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    printf 'missing required command: %s\n' "$cmd" >&2
    exit 1
  fi
}

json_string() {
  jq -Rn --arg v "$1" '$v'
}

cdp_nav() {
  local target="$1"
  local url="$2"
  cdp nav "$target" "$url" >/dev/null
}

kdocs_find_main_tab() {
  local preferred="${1:-}"
  if [[ -n "$preferred" ]]; then
    printf '%s\n' "$preferred"
    return 0
  fi
  
  local pages target
  pages="$(cdp_list_raw)"
  
  # Find existing kdocs tab (preserve priority: latest page > any kdocs page not a doc)
  target="$(jq -r '
    map(select(.type == "page")) as $all
    | ($all | map(select(.url | test("^https://365\\.kdocs\\.cn/")))) as $kdocs_tabs
    | ($kdocs_tabs | map(select(.url | test("^https://365\\.kdocs\\.cn/(latest|$)")))) as $latest_tabs
    | ($kdocs_tabs | map(select(.url | (test("^https://365\\.kdocs\\.cn/l/") | not)))) as $non_doc_tabs
    | if ($latest_tabs | length) > 0 then $latest_tabs
        elif ($non_doc_tabs | length) > 0 then $non_doc_tabs
        else $kdocs_tabs end
    | [.[].targetId]
    | reduce .[] as $id ([]; if index($id) then . else . + [$id] end)
    | .[0] // empty
  ' <<<"$pages")"
  
  if [[ -n "$target" ]]; then
    printf '%s\n' "$target"
    return 0
  fi

  # Create new tab and wait for it to appear
  cdp open "https://365.kdocs.cn/" >/dev/null 2>/dev/null || true
  for _ in $(seq 1 40); do
    sleep 0.5
    pages="$(cdp_list_raw)"
    target="$(jq -r '
      map(select(.type == "page")) as $all
      | ($all | map(select(.url | test("^https://365\\.kdocs\\.cn/")))) as $kdocs_tabs
      | ($kdocs_tabs | map(select(.url | (test("^https://365\\.kdocs\\.cn/l/") | not)))) as $non_doc_tabs
      | if ($non_doc_tabs | length) > 0 then $non_doc_tabs else $kdocs_tabs end
      | [.[].targetId]
      | reduce .[] as $id ([]; if index($id) then . else . + [$id] end)
      | .[0] // empty
    ' <<<"$pages")"
    if [[ -n "$target" ]]; then
      printf '%s\n' "$target"
      return 0
    fi
  done

  return 1
}

kdocs_find_doc_tab() {
  local preferred="${1:-}"
  if [[ -n "$preferred" ]]; then
    printf '%s\n' "$preferred"
    return 0
  fi
  local pages
  pages="$(cdp_list_raw)"
  jq -r '
    map(select(.type == "page"))
    | map(select(.url | test("^https://365\\.kdocs\\.cn/l/")))
    | .[0].targetId // empty
  ' <<<"$pages"
}

kdocs_target_url() {
  local target="$1"
  cdp_eval "$target" "window.location.href" | jq -r '.' 2>/dev/null || true
}

wait_for_kdocs_items() {
  local target="$1"
  local limit="${2:-10000}"
  local expr
  read -r -d '' expr <<'EOF' || true
(async () => {
  const deadline = Date.now() + LIMIT_MS;
  while (Date.now() < deadline) {
    if (document.querySelector('.item-container')) return 'READY';
    await new Promise(r => setTimeout(r, 300));
  }
  throw new Error('Timed out waiting for WPS 365 search results');
})()
EOF
  expr="${expr/LIMIT_MS/${limit}}"
  cdp_eval "$target" "$expr" >/dev/null
}

wait_for_kdocs_doc() {
  local target="$1"
  local limit="${2:-20000}"
  local expr
  read -r -d '' expr <<'EOF' || true
(async () => {
  const deadline = Date.now() + LIMIT_MS;
  while (Date.now() < deadline) {
    const t = document.title || '';
    if (t && t !== 'WPS 365' && t !== 'WPS Office') return 'READY';
    await new Promise(r => setTimeout(r, 300));
  }
  throw new Error('Timed out waiting for WPS document to load');
})()
EOF
  expr="${expr/LIMIT_MS/${limit}}"
  cdp_eval "$target" "$expr" >/dev/null
}

wait_for_kdocs_ai_box() {
  local target="$1"
  local limit="${2:-15000}"
  local expr
  read -r -d '' expr <<'EOF' || true
(async () => {
  const deadline = Date.now() + LIMIT_MS;
  while (Date.now() < deadline) {
    const box = Array.from(document.querySelectorAll('textarea'))
      .find(el => /supports @ to specify files for Q&A/i.test(el.getAttribute('placeholder') || ''));
    const send = document.querySelector('button[aria-label="Send"], .kd-chat-sender__send');
    if (box && send) return 'READY';
    await new Promise(r => setTimeout(r, 300));
  }
  throw new Error('Timed out waiting for WPS Docs Chat input');
})()
EOF
  expr="${expr/LIMIT_MS/${limit}}"
  cdp_eval "$target" "$expr" >/dev/null
}

wait_for_kdocs_ai_answer() {
  local target="$1"
  local before_count="${2:-0}"
  local before_answer_b64="${3:-}"
  local limit="${4:-45000}"
  local before_answer
  before_answer="$(printf '%s' "$before_answer_b64" | base64 -d 2>/dev/null || true)"
  local deadline stable_hits state count stop answer changed
  deadline=$(( $(date +%s%3N) + limit ))
  stable_hits=0
  while (( $(date +%s%3N) < deadline )); do
    state="$(cdp_eval "$target" '(() => JSON.stringify({count: document.querySelectorAll(".qa-group").length, answer: Array.from(document.querySelectorAll(".qa-group")).at(-1)?.querySelector(".gpt-chat-block-msg-printer")?.innerText?.trim() || "", stop: !!document.querySelector(".kd-chat-sender__stop")}))()')"
    count="$(jq -r '.count // 0' <<<"$state")"
    answer="$(jq -r '.answer // ""' <<<"$state")"
    stop="$(jq -r '.stop // false' <<<"$state")"
    changed=0
    if (( count > before_count )); then
      changed=1
    elif [[ -n "$answer" && "$answer" != "$before_answer" ]]; then
      changed=1
    fi
    if (( changed == 1 )) && [[ -n "$answer" && "$stop" == "false" ]]; then
      stable_hits=$((stable_hits + 1))
      if (( stable_hits >= 3 )); then
        return 0
      fi
    else
      stable_hits=0
    fi
    sleep 0.5
  done
  printf 'Timed out waiting for WPS Docs Chat answer\n' >&2
  exit 1
}

# Extract document-body text lines from the accessibility tree.
# Runs cdp snap and filters out known toolbar, UI, and metadata labels.
kdocs_snap_text() {
  local target="$1"
  cdp snap "$target" 2>/dev/null \
    | grep -oP '(?<=\[StaticText\] ).*' \
    | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
    | grep -v '^$' \
    | grep -Evx \
        'Home|Insert|Layout|Review|View|Efficiency|WPS AI|Share|WPS AI'\''s writing|Outline|AI Recognition Outline|The title has no content|No Advice|Find|Replace|FindReplace|More|Prev|Next|Enter text to search|Not enabled|AI writing:' \
    | grep -Ev '^(Words:|Section:|Line:|Column:|Page:|Ctrl\+[A-Za-z]|[0-9]+%?|[0-9]+/[0-9]+)$' \
    | grep -Ev '^mmm.*$'
}
