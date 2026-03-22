# A-Share Platform Backend

Purpose: Host retained daily facts, production pipelines, and read-only HTTP APIs.
Audience: Developers building data pipelines, skills, and frontend consumers.
Sections: Scope | Entry Points | CLI | APIs | Local Run | Docker | LLM | Theme Tuning

## Scope

This backend owns:

- retained DB-backed daily facts
- daily production pipelines
- read-only HTTP APIs for downstream clients
- scheduled collection inside the container image

Core application code lives under `app/`.

## Entry Points

- FastAPI app: `app.main:app`
- CLI: `ashare-platform <command>`
- Health: `GET /health`
- OpenAPI docs: `GET /docs`

## CLI

Single-purpose commands:

- `ashare-platform collect-ephemeral --date YYYY-MM-DD`
- `ashare-platform build-emotion-facts --date YYYY-MM-DD`
- `ashare-platform build-trend-pool --date YYYY-MM-DD`
- `ashare-platform build-theme-pool --date YYYY-MM-DD`
- `ashare-platform build-market-review --date YYYY-MM-DD`
- `ashare-platform cleanup-ephemeral-data --max-age-days N`

High-level commands:

- `ashare-platform collect-all`
- `ashare-platform collect-all --date YYYY-MM-DD`
- `ashare-platform init-data --days 30`
- `ashare-platform init-data --date YYYY-MM-DD --days 30`

Command semantics:

- `collect-all` is the daily production entrypoint. It only processes one trading day and includes analysis steps.
- `init-data` is the historical bootstrap entrypoint. It backfills the last `N` trading days of retained market emotion facts and does not run trend/theme/review analysis.

## HTTP APIs

Core endpoints:

- `GET /health`
- `GET /market-emotion/daily/{trade_date}`
- `GET /market-emotion/history`
- `GET /theme-emotion/daily`
- `GET /theme-emotion/themes/{theme_name}/history`
- `GET /trend-pool/daily`
- `GET /theme-pool/daily`
- `GET /market-reviews/daily/{trade_date}`

Market emotion now includes:

- `advance_count`
- `decline_count`
- `flat_count`
- `seal_rate`
- `promotion_2to3_total`
- `promotion_2to3_success`
- `promotion_3to4_total`
- `promotion_3to4_success`
- `market_volume`

## Local Run

Use the project `.venv` from the repository root:

```bash
./.venv/bin/python -m pip install -e packages/ashare-data
./.venv/bin/python -m pip install -e apps/ashare-platform/backend
./.venv/bin/uvicorn app.main:app --app-dir apps/ashare-platform/backend --host 127.0.0.1 --port 8000
```

Optional runtime env:

```bash
export ASHARE_PLATFORM_HOME=/tmp/ashare-platform-dev
export TZ=Asia/Shanghai
```

Example task execution:

```bash
./.venv/bin/python -m app.cli init-data --days 30
./.venv/bin/python -m app.cli collect-all --date 2026-03-20
./.venv/bin/python -m app.cli build-theme-pool --date 2026-03-20
```

## Docker

Compose file:

- `deployment/docker/ashare-platform/docker-compose.yml`

The current compose setup uses `network_mode: host`, so the backend is reachable from the host at:

```bash
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

Build and start:

```bash
bash deployment/docker/ashare-platform/install.sh
docker compose -f deployment/docker/ashare-platform/docker-compose.yml build
docker compose -f deployment/docker/ashare-platform/docker-compose.yml up -d
```

Optional bootstrap:

```bash
bash deployment/docker/ashare-platform/install.sh --with-init-data --init-days 30
```

Runtime notes:

- The image runs `supervisord` as PID 1.
- `uvicorn` and `cron` are both managed inside the same container.
- The image is configured for `TZ=Asia/Shanghai`.
- A cron job runs `collect-all` at `15:30` on weekdays and skips non-trading days.

## Data Sources

Current market emotion inputs:

- THS `limit_up_pool`: limit-up/limit-down counts, seal rate, promotion stats
- THS `turnover_day`: market turnover
- Sohu `zdt.shtml`: historical advance/decline/flat breadth
- THS `indexflash`: latest breadth snapshot, with CDP fallback when direct HTTP is blocked

## Chrome CDP Fallback

Some THS endpoints require a real browser session context. The backend relies on the shared `ashare-data` CDP client for those cases.

Expected Chrome DevTools endpoint:

```bash
http://127.0.0.1:9222
```

Container access works because the current compose setup uses host networking.

## Semantic Enrichment

Theme and market-review semantics are optional and disabled unless explicitly enabled.

Enable them with an OpenAI-compatible endpoint:

```bash
export ASHARE_THEME_SEMANTIC_ENRICH_ENABLED=1
export ASHARE_MARKET_REVIEW_SEMANTIC_ENRICH_ENABLED=1
export OPENAI_BASE_URL=http://127.0.0.1:10000/v1
export OPENAI_MODEL=qwen3.5-27b
export OPENAI_API_KEY=sk-placeholder
```

When enabled, the backend may fill:

- `theme_pool_daily.market_attitude`
- `theme_pool_daily.theme_stage`
- `theme_pool_daily.summary`
- `theme_stock_daily.comment`
- `market_review_daily.summary`
- `market_review_daily.report_markdown`

Deterministic fields remain protected:

- `theme_strength`
- `theme_score`
- `trend_stock_count`
- `core_trend_stock_count`
- stock trend scores and ranks

## Theme Tuning

`theme_pool` is ranked by deterministic factors before any LLM enrichment.

Preset profiles:

```bash
export ASHARE_THEME_POOL_PROFILE=default
export ASHARE_THEME_POOL_PROFILE=mainline_strict
```

`default` keeps broader candidate coverage. `mainline_strict` requires core trend confirmation and is closer to a "mainline only" trading style.

Available env vars:

```bash
export ASHARE_THEME_POOL_MIN_TREND_STOCK_COUNT=1
export ASHARE_THEME_POOL_MIN_CORE_TREND_STOCK_COUNT=0
export ASHARE_THEME_POOL_WEIGHT_THEME_STRENGTH=1.0
export ASHARE_THEME_POOL_WEIGHT_TREND_STOCK_COUNT=2.0
export ASHARE_THEME_POOL_WEIGHT_CORE_TREND_STOCK_COUNT=3.0
export ASHARE_THEME_POOL_WEIGHT_STRONGEST_TREND_SCORE=0.05
```
