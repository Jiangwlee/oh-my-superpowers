# n8n Workflows for Ashare-Data

This directory contains n8n workflow JSON files for automating ashare-data operations.

## Quick Start

### 1. Import Workflow

1. Open n8n UI: http://localhost:10003
2. Click **Settings** → **Import from File**
3. Select `ashare-daily-simple.json` (recommended) or `ashare-daily-collect.json`
4. Click **Import**

For detailed deployment instructions, see [FINAL_DEPLOYMENT.md](FINAL_DEPLOYMENT.md).

### 2. Verify Connections

Before activating the workflow, ensure:

- ✅ `task_runner` container is running
- ✅ Network connectivity: `curl http://task_runner:8000/health`
- ✅ Data directory permissions: `ls -la ~/.ashare-assistant`

### 3. Activate Workflow

- Toggle the workflow switch to **ON**
- Watch the execution log for first run

## Workflow Description

### A 股每日数据采集 (ashare-daily-collect)

**Purpose**: Daily A-share data collection at 22:00 Beijing time (Mon-Fri)

**Flow**:
1. **Cron Trigger**: Runs at 22:00 on weekdays (Beijing time)
2. **HTTP Request**: Calls `POST /ashare/collect` on task-runner
3. **If Node**: Checks response `status` (success/failed)
4. **Success Branch**: Writes `success_{date}.flag` file
5. **Error Branch**: Writes `error_YYYYMMDD.log` file, waits 5min, retries (max 3 times)

**Configuration**:
- **URL**: `http://task_runner:8000/ashare/collect`
- **Timeout**: 600000ms (10 minutes)
- **Retry**: 3 attempts, 5 minutes apart
- **Cron**: Weekdays 22:00-22:59 Beijing time (UTC+8)

## Testing

### Manual Trigger

Use n8n's **Execute Workflow** button:

```bash
# Or via API (admin credentials required)
curl -X POST http://localhost:10003/rest/workflows/WORKFLOW_ID/executions \
  -H "Content-Type: application/json"
```

### Debug HTTP Requests

```bash
# Test task-runner endpoint directly
curl -X POST http://task_runner:8000/ashare/collect \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-03-04","skip_collect":true,"skip_filter":true}'

# Expected response:
# {"task_id":"...","status":"success","result":{...},"error":null}
```

### Monitor Execution

```bash
# Check task-runner logs
docker logs task_runner -f --tail 50

# Check n8n execution logs
# In n8n UI: Settings → Execution Logs
```

## Troubleshooting

### Problem: HTTP Request fails

**Check**:
1. Container connectivity: `docker exec n8n_app wget -qO- http://task_runner:8000/health`
2. task-runner status: `docker ps --filter name=task_runner`
3. n8n credentials: Check if any API credentials are needed

### Problem: Data not appearing in `~/.ashare-assistant`

**Check**:
1. Volume mount: `docker inspect n8n_app | grep ashare-assistant`
2. File permissions: `ls -la ~/.ashare-assistant/data/$(date +%Y-%m-%d)`
3. task-runner logs: `docker logs task_runner --tail 100`

### Problem: Workflow triggers too often

**Fix**:
- Adjust Cron Trigger settings in n8n UI
- Verify timezone: `n8n` should be set to `Asia/Shanghai` (see `docker-compose.yml`)

## Future Workflows

Planned additional workflows:

1. **ashare-diagnose-daily**: Run `ashare-diagnose` daily for T+1/T+5 analysis
2. **ashare-watchlist-scan**: Trigger watchlist scan (currently manual via `/ashare/watchlist`)
3. **alert-on-failure**: Send alerts when collection fails (email/Slack/DingTalk)

## Credits

- Workflow design based on `n8n-workflows` best practices
- Reference: https://github.com/Zie619/n8n-workflows
