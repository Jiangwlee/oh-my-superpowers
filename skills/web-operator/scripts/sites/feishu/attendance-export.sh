#!/usr/bin/env bash
# Drive the Feishu admin attendance Monthly-report data export workflow.
# Input: --start, --end (required), optional --out-dir, --target, --timeout.
# Output: a JSON object with xlsx path, size, and the requested date range.
# Public interface: attendance-export.sh --start <YYYY-MM-DD> --end <YYYY-MM-DD> [...]
#
# Implementation: invokes the Feishu admin attendance internal HTTP APIs from
# inside an oa.feishu.cn Chrome tab via cdp eval (cookies + CSRF carried
# automatically). The browser is used purely as a session-bearing fetch client;
# no UI interaction. Locked to report_id=102 (Monthly reports) per current scope.

set -euo pipefail

FEISHU_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${FEISHU_DIR}/common.sh"

require_cmd jq
require_cmd base64

DOWNLOADS_DIR="${HOME}/Downloads"
ATTENDANCE_VIEW_URL="https://oa.feishu.cn/attendance/manage/statistics/report/view/102"

START=""
END=""
OUT_DIR=""
TARGET=""
TIMEOUT_SEC="300"

usage() {
  cat >&2 <<USAGE
usage: $(basename "$0") --start YYYY-MM-DD --end YYYY-MM-DD [--out-dir DIR] [--target PREFIX] [--timeout SECONDS]

Pre-requisite: signed in to oa.feishu.cn as an attendance administrator on any
Chrome tab (the script will reuse an oa.feishu.cn tab or open one). The export
window must be <= 31 days; callers split larger ranges themselves.
USAGE
  exit 1
}

while (( $# > 0 )); do
  case "$1" in
    --start)    START="${2:-}"; shift 2 ;;
    --end)      END="${2:-}"; shift 2 ;;
    --out-dir)  OUT_DIR="${2:-}"; shift 2 ;;
    --target)   TARGET="${2:-}"; shift 2 ;;
    --timeout)  TIMEOUT_SEC="${2:-}"; shift 2 ;;
    -h|--help)  usage ;;
    *)          printf 'unknown argument: %s\n' "$1" >&2; usage ;;
  esac
done

[[ -n "$START" && -n "$END" ]] || usage
[[ "$START" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { printf '%s\n' '--start must be YYYY-MM-DD' >&2; exit 1; }
[[ "$END"   =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { printf '%s\n' '--end must be YYYY-MM-DD' >&2; exit 1; }
[[ "$TIMEOUT_SEC" =~ ^[0-9]+$ ]] || { printf '%s\n' '--timeout must be an integer (seconds)' >&2; exit 1; }

START_INT="${START//-/}"
END_INT="${END//-/}"
START_EPOCH="$(date -d "$START" +%s)"
END_EPOCH="$(date -d "$END" +%s)"
SPAN_DAYS=$(( (END_EPOCH - START_EPOCH) / 86400 ))
(( SPAN_DAYS >= 0 )) || { printf '%s\n' '--end must not be earlier than --start' >&2; exit 1; }
(( SPAN_DAYS <= 31 )) || { printf '%s\n' '--start..--end span exceeds Feishu attendance 31-day limit; split the range and call again' >&2; exit 1; }

OUT_DIR="${OUT_DIR:-$DOWNLOADS_DIR}"
[[ -d "$OUT_DIR" ]] || mkdir -p "$OUT_DIR"

if [[ -z "$TARGET" ]]; then
  TARGET="$(find_or_create_tab "$ATTENDANCE_VIEW_URL" "oa.feishu.cn")"
fi
[[ -n "$TARGET" ]] || { printf 'no usable oa.feishu.cn tab found\n' >&2; exit 1; }

TIMEOUT_MS=$(( TIMEOUT_SEC * 1000 ))

read -r -d '' BROWSER_SCRIPT <<'JSEOF' || true
(async () => {
  const csrfCookie = document.cookie.split('; ').find(c => c.startsWith('_csrf_token='));
  if (!csrfCookie) throw new Error('feishu: _csrf_token cookie not found; sign in to oa.feishu.cn first');
  const csrf = csrfCookie.split('=')[1];
  const headers = {
    'Content-type': 'application/json',
    'X-Csrftoken': csrf,
    'time-zone': 'Asia/Shanghai',
    'Accept-Language': 'en-US',
    'Page-Language': 'en-US',
    'locale': 'en-US',
    'timezone': -480,
    'x-attendance-version': '5.34.0'
  };
  const startDate = __START_INT__;
  const endDate = __END_INT__;
  const timeoutMs = __TIMEOUT_MS__;

  const callJson = async (path, body) => {
    const r = await fetch('https://oa.feishu.cn' + path, {
      method: 'POST', credentials: 'same-origin', headers,
      body: JSON.stringify(body)
    });
    const j = await r.json();
    if (j.code !== 0) throw new Error('feishu API error ' + path + ': ' + JSON.stringify(j));
    return j.data;
  };

  const initiate = await callJson('/attendance/v2/admin/datacenter/custom_report/download', {
    query_filter: {
      start_date: startDate,
      end_date: endDate,
      report_id: '102',
      sort_unit_list: [],
      filter_ids: [
        {option_type: 1, option_values: []},
        {option_type: 3, option_values: []}
      ],
      use_cache: false,
      use_backend_date: false,
      only_save_option: false
    }
  });
  const taskKey = initiate.task_key;
  if (!taskKey) throw new Error('feishu: no task_key returned from download initiate');

  const deadline = Date.now() + timeoutMs;
  let task = null;
  while (Date.now() < deadline) {
    await new Promise(r => setTimeout(r, 2000));
    const list = await callJson('/attendance/v2/admin/datacenter/list_export_file_task', {});
    const candidate = (list.export_file_task_list || []).find(x => x.file_key === taskKey);
    if (candidate && candidate.status === 1 && candidate.progress === 100) {
      task = candidate;
      break;
    }
  }
  if (!task) throw new Error('feishu: timed out waiting for attendance export task to complete');

  const dlR = await fetch(
    'https://oa.feishu.cn/attendance/v2/admin/datacenter/download_excel?file_key=' + encodeURIComponent(task.file_key),
    {method: 'GET', credentials: 'same-origin', headers: {'X-Csrftoken': csrf}}
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

  return JSON.stringify({fileKey: task.file_key, fileName: task.file_name, size: bytes.length, b64});
})()
JSEOF

BROWSER_SCRIPT="${BROWSER_SCRIPT//__START_INT__/${START_INT}}"
BROWSER_SCRIPT="${BROWSER_SCRIPT//__END_INT__/${END_INT}}"
BROWSER_SCRIPT="${BROWSER_SCRIPT//__TIMEOUT_MS__/${TIMEOUT_MS}}"

RESULT="$(cdp_eval "$TARGET" "$BROWSER_SCRIPT")"
[[ -n "$RESULT" ]] || { printf 'feishu: empty response from browser\n' >&2; exit 1; }

FILE_NAME="$(printf '%s' "$RESULT" | jq -r '.fileName // empty')"
[[ -n "$FILE_NAME" ]] || { printf 'feishu: missing fileName in browser response: %s\n' "$RESULT" >&2; exit 1; }
FILE_NAME="${FILE_NAME//\//_}"

XLSX_PATH="${OUT_DIR}/${FILE_NAME}"
printf '%s' "$RESULT" | jq -r '.b64' | base64 -d > "$XLSX_PATH"

SIZE_BYTES="$(printf '%s' "$RESULT" | jq -r '.size')"

jq -n \
  --arg xlsx "$XLSX_PATH" \
  --arg start "$START" \
  --arg end "$END" \
  --argjson size "$SIZE_BYTES" \
  '{xlsx: $xlsx, size_bytes: $size, start: $start, end: $end}'
