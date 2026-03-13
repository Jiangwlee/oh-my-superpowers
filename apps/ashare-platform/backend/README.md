# A-Share Platform Backend

Purpose: Host the platform backend for retained daily facts, task pipelines,
         and read-only HTTP APIs.
Audience: Developers extracting platform logic from `ashare-data` and future
          clients such as skills and frontend apps.
Sections: Scope | Layout | Entry Points | Local Run | Docker Run

## Scope

This backend will own:

- retained DB-backed daily facts
- task-based data production entrypoints
- read-only HTTP APIs for downstream consumers

## Layout

Core application code lives under `app/`.

## Entry Points

- FastAPI app: `app.main:app`
- CLI: `ashare-platform <command>`
- Health: `GET /health`

### CLI Commands

- `ashare-platform collect-ephemeral --date YYYY-MM-DD`
- `ashare-platform build-trend-pool --date YYYY-MM-DD`
- `ashare-platform build-theme-pool --date YYYY-MM-DD`
- `ashare-platform build-market-review --date YYYY-MM-DD`
- `ashare-platform cleanup-ephemeral-data --max-age-days N`

## Local Run

Use the project `.venv` from the repository root:

```bash
./.venv/bin/python -m pip install -e apps/ashare-platform/backend
./.venv/bin/uvicorn app.main:app --app-dir apps/ashare-platform/backend --host 127.0.0.1 --port 8000
```

Optional runtime env:

```bash
export ASHARE_PLATFORM_HOME=/tmp/ashare-platform-dev
```

Example task execution:

```bash
./.venv/bin/python -m app.cli build-trend-pool --date 2026-03-13
./.venv/bin/python -m app.cli build-theme-pool --date 2026-03-13
./.venv/bin/python -m app.cli build-market-review --date 2026-03-13
```

## Docker Run

Build from the repository root:

```bash
docker build -f apps/ashare-platform/backend/Dockerfile -t ashare-platform-backend .
```

Run:

```bash
docker run --rm -p 8000:8000 \
  -e ASHARE_PLATFORM_HOME=/data \
  ashare-platform-backend
```
