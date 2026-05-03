# Feishu Admin Workflows

The `feishu` command group operates the Feishu admin backend by calling its
internal HTTP APIs from inside a Chrome tab (cookies + CSRF carried
automatically). Both `approval` (审批后台, host `www.feishu.cn`) and
`attendance` (考勤后台, host `oa.feishu.cn`) are supported. The Feishu open
platform does not offer an approval-data export API, and its attendance
OpenAPI requires a separately approved app scope, so the admin backend is the
practical path for bulk historical exports.

## Pre-requisites

1. Chrome remote debugging is enabled.
2. **For `approval`**: signed in to `https://www.feishu.cn/approval/admin` as
   an administrator. Any tab on `feishu.cn` is enough.
3. **For `attendance`**: signed in to `https://oa.feishu.cn/attendance/manage/`
   as an attendance administrator. The CLI reuses an existing `oa.feishu.cn`
   tab or opens one to `attendance/manage/statistics/report/view/102`.

## `omp web-operator feishu approval export`

Export approval data for a Submit-time window to ZIP/Excel.

### Usage

```
omp web-operator feishu approval export \
    --start <YYYY-MM-DD> \
    --end   <YYYY-MM-DD> \
    [--extract-to <dir>] \
    [--target <prefix>] \
    [--timeout <seconds>]
```

### Output (JSON to stdout)

```json
{
  "zip": "/home/bruce/Downloads/<original-filename>.zip",
  "extract_dir": "/home/bruce/Downloads/<zip-basename>/",
  "files": ["Reimbursement_All_<ts>.xlsx", "..."],
  "summary": {
    "files": 8,
    "types": 8,
    "total_requests": 26,
    "start": "2026-04-01",
    "end": "2026-04-26"
  },
  "per_file": [{"name": "...xlsx", "total_requests": 9}, ...]
}
```

`total_requests` aggregates the de-duplicated request counts from every
Excel's `Filter: ... Total: N request(s)` header row.

### Limits

- **90-day window**: the Feishu admin backend caps any export at a 90-day
  Submit-time span. The CLI rejects wider windows up-front.
- **~30–60 s per export**: the CLI submits a `batchExport` task and polls the
  export-history list until the new task reaches `status=3, progress=100`.
  Default `--timeout 300` is conservative.
- **Data granularity**: each Excel row is an approval node record (one row per
  approver step), not the full approval instance. The same `Request No.` may
  appear multiple times in the raw sheet; `total_requests` reflects the
  de-duplicated count from the page header.
- **Filename and download location**: the ZIP is saved to `~/Downloads/` with
  the original Feishu-assigned filename. `--extract-to` controls only the
  unzip target (defaults to a same-name sibling directory next to the ZIP).

### Common errors

| Error | Cause / fix |
|-------|-------------|
| `feishu: _csrf_token cookie not found` | No active Feishu session in this tab. Sign in to `feishu.cn/approval/admin`, then retry. |
| `feishu API error ... code: 99991641` | Session expired or wrong account. Refresh the tab and re-login. |
| `feishu: timed out waiting for export task to complete` | Backend slow. Re-run with a larger `--timeout`. |

## `omp web-operator feishu attendance export`

Export the Monthly-report (月度汇总, view `102`) attendance data to xlsx.
Locked to that single view per current scope; daily reports and custom views
are not supported.

### Usage

```
omp web-operator feishu attendance export \
    --start <YYYY-MM-DD> \
    --end   <YYYY-MM-DD> \
    [--out-dir <dir>] \
    [--target <prefix>] \
    [--timeout <seconds>]
```

### Output (JSON to stdout)

```json
{
  "xlsx": "/home/bruce/Downloads/Monthly reports_20260401_20260427.xlsx",
  "size_bytes": 9753,
  "start": "2026-04-01",
  "end": "2026-04-27"
}
```

### Limits

- **31-day window**: the attendance backend caps any export at 31 days. Wider
  windows return server error `1000020411`. The CLI rejects them up-front; the
  caller is responsible for splitting larger ranges and stitching results.
- **Single xlsx**: the artifact is one xlsx file, not a zip. No unzip step.
- **Filename language**: filename comes from the server (e.g. `Monthly
  reports_<start>_<end>.xlsx`). Headers force `Accept-Language: en-US` so the
  filename and column headers stay in English.
- **`x-attendance-version`**: pinned to the value observed during reverse
  engineering (`5.34.0`). If Feishu invalidates that version in a future
  release the call will fail; bump the constant in the script.

### Common errors

| Error | Cause / fix |
|-------|-------------|
| `feishu: _csrf_token cookie not found` | No active oa.feishu.cn session in this tab. Sign in to `oa.feishu.cn/attendance/manage/`, then retry. |
| `feishu API error ... code: 1000020411` | Date span exceeds 31 days. Should be caught by the CLI; if not, narrow the range. |
| `feishu: timed out waiting for attendance export task to complete` | Backend slow. Re-run with a larger `--timeout`. |
