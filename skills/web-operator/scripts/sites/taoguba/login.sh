#!/usr/bin/env bash
# This script signs in to Taoguba with credentials already stored in Chrome.
# Input: optional timeout in seconds and optional CDP target prefix.
# Output: one compact JSON object with status logged_in or already_logged_in.
# Public interface: taoguba-login.sh [timeout_seconds] [target_prefix].
#
# The script opens the login modal, selects account login, checks only whether
# the browser-autofilled fields are non-empty, and submits exactly once.
# It never returns or persists the username, password, cookies, or session data.
# Authentication and page-schema failures are emitted as compact JSON on stderr.

set -euo pipefail

TAOGUBA_LOGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${TAOGUBA_LOGIN_DIR}/common.sh"

require_cmd jq

TIMEOUT_SECONDS="${1:-15}"
TARGET="${2:-}"

[[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || {
  printf '%s\n' \
    '{"ok":false,"site":"taoguba","error":{"code":"invalid_timeout","message":"timeout must be an integer","hint":"Pass a timeout between 1 and 60 seconds."}}' >&2
  exit 2
}
(( TIMEOUT_SECONDS >= 1 && TIMEOUT_SECONDS <= 60 )) || {
  printf '%s\n' \
    '{"ok":false,"site":"taoguba","error":{"code":"invalid_timeout","message":"timeout is outside the supported range","hint":"Pass a timeout between 1 and 60 seconds."}}' >&2
  exit 2
}

emit_error() {
  local code="$1"
  local message="$2"
  local hint="$3"
  jq -cn \
    --arg code "$code" \
    --arg message "$message" \
    --arg hint "$hint" \
    '{ok:false,site:"taoguba",error:{code:$code,message:$message,hint:$hint}}' >&2
}

if ! TARGET="$(taoguba_find_target "$TARGET" 2>/dev/null)"; then
  emit_error \
    "browser_unavailable" \
    "Chrome could not resolve a Taoguba tab" \
    "Enable Chrome remote debugging and retry."
  exit 4
fi
[[ -n "$TARGET" ]] || {
  emit_error \
    "browser_unavailable" \
    "no usable Taoguba tab was found" \
    "Enable Chrome remote debugging and retry."
  exit 4
}

if ! taoguba_nav_fast "$TARGET" "https://www.tgb.cn/" >/dev/null 2>&1; then
  emit_error \
    "browser_unavailable" \
    "Chrome could not navigate to the Taoguba homepage" \
    "Confirm the CDP tab is reachable and retry."
  exit 4
fi
if ! wait_for_url_contains \
  "$TARGET" "tgb.cn/" "$((TIMEOUT_SECONDS * 1000))" 2>/dev/null; then
  emit_error \
    "page_not_ready" \
    "Taoguba did not reach its homepage before timeout" \
    "Inspect the tab for a network or verification page."
  exit 4
fi
if ! wait_for_taoguba_text \
  "$TARGET" "实盘比赛" "$((TIMEOUT_SECONDS * 1000))" 2>/dev/null; then
  emit_error \
    "page_not_ready" \
    "Taoguba homepage content did not become ready before timeout" \
    "Inspect the tab for a network or verification page."
  exit 4
fi

read -r -d '' PREPARE_EXPR <<'EOF' || true
(async () => {
  const deadline = Date.now() + TIMEOUT_MS;
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  const visible = (element) =>
    Boolean(element && element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden');
  const findLoginEntry = () =>
    [...document.querySelectorAll('a')].find(
      element => visible(element) && element.textContent.trim() === '登录/注册'
    );
  const findUserEntry = () =>
    document.querySelector(
      '.right.header-user a[href*="/user/getSelfInfo"],.right.header-user a[href*="/blog/"]'
    );
  const waitFor = async (predicate) => {
    while (Date.now() < deadline) {
      const value = predicate();
      if (value) return value;
      await sleep(200);
    }
    return null;
  };

  const initialState = await waitFor(() => {
    if (visible(findUserEntry())) return 'logged-in';
    if (visible(findLoginEntry())) return 'logged-out';
    return null;
  });
  if (initialState === 'logged-in') {
    return { ok: true, site: 'taoguba', status: 'already_logged_in' };
  }
  if (initialState !== 'logged-out') {
    return {
      ok: false,
      site: 'taoguba',
      error: {
        code: 'page_schema_changed',
        message: 'Taoguba login state could not be detected',
        hint: 'Inspect the current homepage DOM before retrying.'
      }
    };
  }

  findLoginEntry().click();
  const controls = await waitFor(() => {
    const accountTab = document.querySelector('#userLoginBtn');
    const panel = document.querySelector('#loginPanel');
    const submit = document.querySelector('#loginBtn');
    return visible(accountTab) && visible(panel) && visible(submit)
      ? { accountTab, panel }
      : null;
  });
  if (!controls) {
    return {
      ok: false,
      site: 'taoguba',
      error: {
        code: 'page_schema_changed',
        message: 'Taoguba account-login controls were not found',
        hint: 'Inspect the login modal selectors before retrying.'
      }
    };
  }

  controls.accountTab.click();
  const credentialsReady = await waitFor(() => {
    const identity = controls.panel.querySelector(
      'input[type="text"],input[placeholder*="手机号"],input[placeholder*="笔名"]'
    );
    const password = controls.panel.querySelector('input[type="password"]');
    return Boolean(identity && password && identity.value.length > 0 && password.value.length > 0);
  });
  if (!credentialsReady) {
    return {
      ok: false,
      site: 'taoguba',
      error: {
        code: 'credentials_not_autofilled',
        message: 'Chrome did not autofill both Taoguba account fields',
        hint: 'Save the credentials in Chrome, then rerun this command.'
      }
    };
  }
  return { ok: true, site: 'taoguba', status: 'ready_to_submit' };
})()
EOF
PREPARE_EXPR="${PREPARE_EXPR/TIMEOUT_MS/$((TIMEOUT_SECONDS * 1000))}"

if ! PREPARE_RESULT="$(cdp_eval "$TARGET" "$PREPARE_EXPR" 2>/dev/null)"; then
  emit_error \
    "browser_unavailable" \
    "Chrome could not complete the Taoguba login preparation" \
    "Confirm the CDP tab is reachable and retry."
  exit 4
fi
if ! jq -e 'type == "object" and has("ok")' >/dev/null <<<"$PREPARE_RESULT"; then
  emit_error \
    "invalid_browser_response" \
    "Taoguba login preparation returned an invalid response" \
    "Inspect the current page DOM and CDP connection."
  exit 1
fi
if [[ "$(jq -r '.ok' <<<"$PREPARE_RESULT")" != "true" ]]; then
  jq -c . <<<"$PREPARE_RESULT" >&2
  case "$(jq -r '.error.code // empty' <<<"$PREPARE_RESULT")" in
    credentials_not_autofilled) exit 4 ;;
    *) exit 1 ;;
  esac
fi
if [[ "$(jq -r '.status' <<<"$PREPARE_RESULT")" == "already_logged_in" ]]; then
  jq -c . <<<"$PREPARE_RESULT"
  exit 0
fi

if ! cdp click "$TARGET" "#loginBtn" >/dev/null 2>&1; then
  emit_error \
    "login_submit_failed" \
    "Chrome could not click the Taoguba login button" \
    "Inspect the login modal before retrying."
  exit 1
fi

read -r -d '' STATE_EXPR <<'EOF' || true
(() => {
  const visible = (element) =>
    Boolean(element && element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden');
  const userEntry = document.querySelector(
    '.right.header-user a[href*="/user/getSelfInfo"],.right.header-user a[href*="/blog/"]'
  );
  const text = document.body?.innerText || '';
  return {
    logged_in: visible(userEntry),
    verification_required: /验证码|安全验证|拖动滑块/.test(text)
  };
})()
EOF

DEADLINE=$((SECONDS + TIMEOUT_SECONDS))
STATE_SEEN=false
while (( SECONDS < DEADLINE )); do
  STATE="$(cdp_eval "$TARGET" "$STATE_EXPR" 2>/dev/null || true)"
  if jq -e 'type == "object" and has("logged_in")' >/dev/null 2>&1 <<<"$STATE"; then
    STATE_SEEN=true
  fi
  if jq -e '.logged_in == true' >/dev/null 2>&1 <<<"$STATE"; then
    printf '%s\n' '{"ok":true,"site":"taoguba","status":"logged_in"}'
    exit 0
  fi
  if jq -e '.verification_required == true' >/dev/null 2>&1 <<<"$STATE"; then
    emit_error \
      "verification_required" \
      "Taoguba requires interactive verification" \
      "Complete the verification in Chrome, then rerun this command."
    exit 4
  fi
  sleep 0.25
done

if [[ "$STATE_SEEN" != "true" ]]; then
  emit_error \
    "browser_unavailable" \
    "Chrome stopped returning Taoguba page state after login submission" \
    "Confirm the CDP tab is reachable and retry."
  exit 4
fi
emit_error \
  "login_not_confirmed" \
  "Taoguba did not confirm login after one submission" \
  "Inspect the visible login error or saved Chrome credentials before retrying."
exit 4
