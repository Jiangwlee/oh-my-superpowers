#!/usr/bin/env bash
# Drive the Feishu admin approval data export workflow.
# Input: --start, --end (required), optional --extract-to, --target, --timeout.
# Output: a JSON object with zip path, extract dir, file list, and summary.
# Public interface: approval-export.sh --start <YYYY-MM-DD> --end <YYYY-MM-DD> [...]
#
# Implementation: invokes the Feishu admin internal HTTP APIs from inside the
# Chrome tab via cdp eval (cookies + CSRF carried automatically). The browser
# is used purely as a session-bearing fetch client; no UI interaction.

set -euo pipefail

FEISHU_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${FEISHU_DIR}/common.sh"

require_cmd jq
require_cmd unzip
require_cmd base64

DOWNLOADS_DIR="${HOME}/Downloads"

START=""
END=""
EXTRACT_TO=""
TARGET=""
TIMEOUT_SEC="300"

usage() {
  cat >&2 <<USAGE
usage: $(basename "$0") --start YYYY-MM-DD --end YYYY-MM-DD [--extract-to DIR] [--target PREFIX] [--timeout SECONDS]

Pre-requisite: open https://www.feishu.cn/approval/admin in Chrome and sign in
as administrator. The script runs entirely against the admin internal HTTP
APIs and does not interact with any UI element.
USAGE
  exit 1
}

while (( $# > 0 )); do
  case "$1" in
    --start)        START="${2:-}"; shift 2 ;;
    --end)          END="${2:-}"; shift 2 ;;
    --extract-to)   EXTRACT_TO="${2:-}"; shift 2 ;;
    --target)       TARGET="${2:-}"; shift 2 ;;
    --timeout)      TIMEOUT_SEC="${2:-}"; shift 2 ;;
    -h|--help)      usage ;;
    *)              printf 'unknown argument: %s\n' "$1" >&2; usage ;;
  esac
done

[[ -n "$START" && -n "$END" ]] || usage
[[ "$START" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { printf '%s\n' '--start must be YYYY-MM-DD' >&2; exit 1; }
[[ "$END"   =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { printf '%s\n' '--end must be YYYY-MM-DD' >&2; exit 1; }
[[ "$TIMEOUT_SEC" =~ ^[0-9]+$ ]] || { printf '%s\n' '--timeout must be an integer (seconds)' >&2; exit 1; }

START_MS="$(date -d "${START} 00:00:00 +0800" +%s%3N)"
END_MS="$(date -d "${END} 23:59:59.999 +0800" +%s%3N)"
SPAN_DAYS=$(( (END_MS - START_MS) / 86400000 ))
(( SPAN_DAYS >= 0 )) || { printf '%s\n' '--end must not be earlier than --start' >&2; exit 1; }
(( SPAN_DAYS <= 90 )) || { printf '%s\n' '--start..--end span exceeds Feishu 90-day limit' >&2; exit 1; }

[[ -d "$DOWNLOADS_DIR" ]] || mkdir -p "$DOWNLOADS_DIR"

TARGET="$(feishu_find_target "$TARGET")"
[[ -n "$TARGET" ]] || { printf 'no usable feishu admin tab found\n' >&2; exit 1; }

TIMEOUT_MS=$(( TIMEOUT_SEC * 1000 ))

read -r -d '' BROWSER_SCRIPT <<'JSEOF' || true
(async () => {
  const csrfCookie = document.cookie.split('; ').find(c => c.startsWith('_csrf_token='));
  if (!csrfCookie) throw new Error('feishu: _csrf_token cookie not found; sign in to feishu admin first');
  const csrf = csrfCookie.split('=')[1];
  const headers = {
    'Content-Type': 'application/json',
    'X-Larkgw-Use-Lark-Session': '1',
    'X-Csrftoken': csrf
  };
  const startFrom = __START_MS__;
  const startTo = __END_MS__;
  const timeoutMs = __TIMEOUT_MS__;

  const callJson = async (path, body) => {
    const r = await fetch('https://www.feishu.cn' + path, {
      method: 'POST', credentials: 'same-origin', headers,
      body: JSON.stringify(body)
    });
    const j = await r.json();
    if (j.code !== 0) throw new Error('feishu API error ' + path + ': ' + JSON.stringify(j));
    return j.data;
  };

  const before = await callJson('/approval/admin/api/export/queryList?locale=en_us', {offset: 0, limit: 50});
  const beforeIds = new Set((before.items || []).map(x => x.id));

  await callJson('/approval/admin/api/v2/export/batchExport?locale=en_us', {
    approvalStatus: 255,
    startFrom, startTo,
    lang: 'en_us',
    timezoneOffset: -480,
    isSingleLine: false,
    departmentPath: 1
  });

  const deadline = Date.now() + timeoutMs;
  let task = null;
  while (Date.now() < deadline) {
    await new Promise(r => setTimeout(r, 2000));
    const hist = await callJson('/approval/admin/api/export/queryList?locale=en_us', {offset: 0, limit: 50});
    const candidate = (hist.items || []).find(x => !beforeIds.has(x.id));
    if (candidate && candidate.status === 3 && candidate.progress === 100) {
      task = candidate;
      break;
    }
  }
  if (!task) throw new Error('feishu: timed out waiting for export task to complete');

  const dlR = await fetch(
    'https://www.feishu.cn/approval/admin/api/export/download?locale=en_us&exportId=' + encodeURIComponent(task.id),
    {method: 'GET', credentials: 'same-origin', headers: {'X-Larkgw-Use-Lark-Session': '1', 'X-Csrftoken': csrf}}
  );
  if (!dlR.ok) throw new Error('feishu: download failed: HTTP ' + dlR.status);
  const buf = await dlR.arrayBuffer();
  const bytes = new Uint8Array(buf);

  let bin = '';
  const chunk = 8192;
  for (let i = 0; i < bytes.length; i += chunk) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, Math.min(i + chunk, bytes.length)));
  }
  const b64 = btoa(bin);

  return JSON.stringify({taskId: task.id, fileName: task.fileName, size: bytes.length, b64});
})()
JSEOF

BROWSER_SCRIPT="${BROWSER_SCRIPT//__START_MS__/${START_MS}}"
BROWSER_SCRIPT="${BROWSER_SCRIPT//__END_MS__/${END_MS}}"
BROWSER_SCRIPT="${BROWSER_SCRIPT//__TIMEOUT_MS__/${TIMEOUT_MS}}"

RESULT="$(cdp_eval "$TARGET" "$BROWSER_SCRIPT")"
[[ -n "$RESULT" ]] || { printf 'feishu: empty response from browser\n' >&2; exit 1; }

FILE_NAME="$(printf '%s' "$RESULT" | jq -r '.fileName // empty')"
[[ -n "$FILE_NAME" ]] || { printf 'feishu: missing fileName in browser response: %s\n' "$RESULT" >&2; exit 1; }
FILE_NAME="${FILE_NAME//\//_}"

ZIP_PATH="${DOWNLOADS_DIR}/${FILE_NAME}"
printf '%s' "$RESULT" | jq -r '.b64' | base64 -d > "$ZIP_PATH"

if [[ -z "$EXTRACT_TO" ]]; then
  ZIP_BASENAME="$(basename "$ZIP_PATH" .zip)"
  EXTRACT_TO="${DOWNLOADS_DIR}/${ZIP_BASENAME}"
fi
mkdir -p "$EXTRACT_TO"
unzip -o -q "$ZIP_PATH" -d "$EXTRACT_TO"

SUMMARY_JSON="$("${FEISHU_DIR}/_summarize_export.py" "$EXTRACT_TO")"

jq -n \
  --arg zip "$ZIP_PATH" \
  --arg extract_dir "$EXTRACT_TO" \
  --arg start "$START" \
  --arg end "$END" \
  --argjson summary "$SUMMARY_JSON" \
  '{
    zip: $zip,
    extract_dir: $extract_dir,
    files: $summary.files,
    summary: {
      files: ($summary.files | length),
      types: $summary.types,
      total_requests: $summary.total_requests,
      start: $start,
      end: $end
    },
    per_file: $summary.per_file
  }'
