# A-Share Platform Backend

Purpose: Host the platform backend for retained daily facts, task pipelines,
         and read-only HTTP APIs.
Audience: Developers extracting platform logic from `ashare-data` and future
          clients such as skills and frontend apps.
Sections: Scope | Layout | Entry Points | Local Run | Theme Tuning | Docker Run

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

## Theme Tuning

`theme_pool` is ranked by deterministic factors before any LLM enrichment.

Preset profiles:

```bash
export ASHARE_THEME_POOL_PROFILE=default
export ASHARE_THEME_POOL_PROFILE=mainline_strict
```

`default` keeps broader candidate coverage. `mainline_strict` requires core
trend confirmation and is closer to a "mainline only" trading style.

Available env vars:

```bash
export ASHARE_THEME_POOL_MIN_TREND_STOCK_COUNT=1
export ASHARE_THEME_POOL_MIN_CORE_TREND_STOCK_COUNT=0
export ASHARE_THEME_POOL_WEIGHT_THEME_STRENGTH=1.0
export ASHARE_THEME_POOL_WEIGHT_TREND_STOCK_COUNT=2.0
export ASHARE_THEME_POOL_WEIGHT_CORE_TREND_STOCK_COUNT=3.0
export ASHARE_THEME_POOL_WEIGHT_STRONGEST_TREND_SCORE=0.05
```

Meaning:

- `MIN_TREND_STOCK_COUNT`: minimum number of trend stocks required for a theme to enter the pool
- `MIN_CORE_TREND_STOCK_COUNT`: minimum number of core stocks that must also be trend stocks
- `WEIGHT_THEME_STRENGTH`: weight of THS theme strength
- `WEIGHT_TREND_STOCK_COUNT`: weight of trend stock breadth inside the theme
- `WEIGHT_CORE_TREND_STOCK_COUNT`: weight of core-stock confirmation
- `WEIGHT_STRONGEST_TREND_SCORE`: weight of the strongest trend stock quality

A more "mainline-first" profile can be enabled directly:

```bash
export ASHARE_THEME_POOL_PROFILE=mainline_strict
```

Or overridden manually:

```bash
export ASHARE_THEME_POOL_MIN_TREND_STOCK_COUNT=2
export ASHARE_THEME_POOL_MIN_CORE_TREND_STOCK_COUNT=1
export ASHARE_THEME_POOL_WEIGHT_THEME_STRENGTH=0.8
export ASHARE_THEME_POOL_WEIGHT_TREND_STOCK_COUNT=2.5
export ASHARE_THEME_POOL_WEIGHT_CORE_TREND_STOCK_COUNT=5.0
export ASHARE_THEME_POOL_WEIGHT_STRONGEST_TREND_SCORE=0.04
```

This profile de-emphasizes raw heat and rewards themes whose core names already
show trend confirmation.

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
