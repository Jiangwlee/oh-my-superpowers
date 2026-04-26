# Feishu Admin Workflows

The `feishu` command group operates the Feishu admin backend
(`feishu.cn/approval/admin`) by calling its internal HTTP APIs from inside the
Chrome tab (cookies + CSRF carried automatically). The Feishu open platform
does not offer an approval-data export API, so the admin backend is the only
path for bulk historical exports.

## Pre-requisites

1. Chrome remote debugging is enabled.
2. The user is signed in to `https://www.feishu.cn/approval/admin` as an
   administrator. Any tab on `feishu.cn` is enough — no specific page is
   required.

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
