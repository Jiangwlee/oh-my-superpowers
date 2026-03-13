# A-Share Platform Restructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract a new `apps/ashare-platform/backend` subproject, keep `packages/ashare-data` as the reusable base library, and deliver the first platform slice with file-based ephemeral data, DB-backed retained assets, task-based execution, and read-only HTTP APIs.

**Architecture:** The implementation keeps existing mature collection and trend-scoring logic, but moves platform concerns upward into a backend app. The backend owns pipelines, storage, API, and task entrypoints. `packages/ashare-data` remains focused on reusable source fetchers, shared infrastructure, and deterministic scoring capability.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic, SQLAlchemy or SQLModel, SQLite, Alembic, pytest, existing `ashare-data` helpers.

---

### Task 1: Create the backend project skeleton

**Files:**
- Create: `apps/ashare-platform/backend/pyproject.toml`
- Create: `apps/ashare-platform/backend/README.md`
- Create: `apps/ashare-platform/backend/app/__init__.py`
- Create: `apps/ashare-platform/backend/app/main.py`
- Create: `apps/ashare-platform/backend/app/api/__init__.py`
- Create: `apps/ashare-platform/backend/app/api/routes/__init__.py`
- Create: `apps/ashare-platform/backend/app/core/__init__.py`
- Create: `apps/ashare-platform/backend/app/db/__init__.py`
- Create: `apps/ashare-platform/backend/app/models/__init__.py`
- Create: `apps/ashare-platform/backend/app/pipelines/__init__.py`
- Create: `apps/ashare-platform/backend/app/repositories/__init__.py`
- Create: `apps/ashare-platform/backend/app/schemas/__init__.py`
- Create: `apps/ashare-platform/backend/app/services/__init__.py`
- Create: `apps/ashare-platform/backend/app/tasks/__init__.py`
- Test: `apps/ashare-platform/backend/tests/test_app_import.py`

**Step 1: Write the failing test**

```python
def test_backend_app_importable():
    from app.main import app

    assert app is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/ashare-platform/backend/tests/test_app_import.py -v`
Expected: FAIL with import or module-not-found error

**Step 3: Write minimal implementation**

- Create the package skeleton
- Add a minimal FastAPI app in `app/main.py`
- Add backend metadata and dependencies to `pyproject.toml`

**Step 4: Run test to verify it passes**

Run: `pytest apps/ashare-platform/backend/tests/test_app_import.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/ashare-platform/backend
git commit -m "feat: scaffold ashare platform backend"
```

### Task 2: Add backend config, run ID, and ephemeral/retained path policy

**Files:**
- Create: `apps/ashare-platform/backend/app/core/config.py`
- Create: `apps/ashare-platform/backend/app/core/runtime.py`
- Test: `apps/ashare-platform/backend/tests/test_config.py`

**Step 1: Write the failing test**

```python
def test_runtime_paths_are_resolved(tmp_path, monkeypatch):
    monkeypatch.setenv("ASHARE_PLATFORM_HOME", str(tmp_path))

    from app.core.config import settings

    assert settings.ephemeral_dir.exists()
    assert settings.database_path.name.endswith(".db")
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/ashare-platform/backend/tests/test_config.py -v`
Expected: FAIL because settings/runtime module is missing

**Step 3: Write minimal implementation**

- Define backend settings
- Resolve ephemeral file root and retained DB path
- Add run ID helper and trade-date helper

**Step 4: Run test to verify it passes**

Run: `pytest apps/ashare-platform/backend/tests/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/ashare-platform/backend/app/core apps/ashare-platform/backend/tests/test_config.py
git commit -m "feat: add backend runtime config"
```

### Task 3: Define retained DB schema for V1 daily facts

**Files:**
- Create: `apps/ashare-platform/backend/app/db/session.py`
- Create: `apps/ashare-platform/backend/app/models/run.py`
- Create: `apps/ashare-platform/backend/app/models/trend_pool_daily.py`
- Create: `apps/ashare-platform/backend/app/models/theme_pool_daily.py`
- Create: `apps/ashare-platform/backend/app/models/theme_stock_daily.py`
- Create: `apps/ashare-platform/backend/app/models/market_review_daily.py`
- Create: `apps/ashare-platform/backend/alembic.ini`
- Create: `apps/ashare-platform/backend/alembic/env.py`
- Test: `apps/ashare-platform/backend/tests/test_models.py`

**Step 1: Write the failing test**

```python
def test_daily_fact_models_have_unique_keys():
    from app.models.trend_pool_daily import TrendPoolDaily

    assert any("trade_date" in str(c) for c in TrendPoolDaily.__table__.constraints)
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/ashare-platform/backend/tests/test_models.py -v`
Expected: FAIL because models are missing

**Step 3: Write minimal implementation**

- Create SQLAlchemy or SQLModel models
- Encode the approved unique-key constraints
- Add DB session/bootstrap code

**Step 4: Run test to verify it passes**

Run: `pytest apps/ashare-platform/backend/tests/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/ashare-platform/backend/app/db apps/ashare-platform/backend/app/models apps/ashare-platform/backend/alembic*
git commit -m "feat: add platform daily fact models"
```

### Task 4: Extract reusable trend-scoring interface from `ashare-data`

**Files:**
- Modify: `packages/ashare-data/ashare_data/fetchers/trend_scanner.py`
- Create: `packages/ashare-data/tests/test_trend_scanner_public_api.py`

**Step 1: Write the failing test**

```python
def test_trend_scanner_exposes_reusable_scan_api():
    from ashare_data.fetchers.trend_scanner import scan_all

    assert callable(scan_all)
```

**Step 2: Run test to verify it fails or reveals API instability**

Run: `pytest packages/ashare-data/tests/test_trend_scanner_public_api.py -v`
Expected: FAIL or expose missing/stable-import problems

**Step 3: Write minimal implementation**

- Keep the deterministic scanning entrypoint importable
- Isolate platform/presentation coupling if present
- Update module header/comments if needed

**Step 4: Run test to verify it passes**

Run: `pytest packages/ashare-data/tests/test_trend_scanner_public_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/ashare-data/ashare_data/fetchers/trend_scanner.py packages/ashare-data/tests/test_trend_scanner_public_api.py
git commit -m "refactor: stabilize trend scanner public api"
```

### Task 5: Create ephemeral collection task in backend

**Files:**
- Create: `apps/ashare-platform/backend/app/tasks/collect_ephemeral.py`
- Create: `apps/ashare-platform/backend/app/pipelines/collect_ephemeral.py`
- Test: `apps/ashare-platform/backend/tests/test_collect_ephemeral_task.py`

**Step 1: Write the failing test**

```python
def test_collect_ephemeral_returns_run_summary(monkeypatch):
    from app.tasks.collect_ephemeral import run

    result = run(trade_date="2026-03-13")
    assert "run_id" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/ashare-platform/backend/tests/test_collect_ephemeral_task.py -v`
Expected: FAIL because task is missing

**Step 3: Write minimal implementation**

- Build a backend task wrapper around ephemeral collection
- Write files into ephemeral storage, not retained DB
- Return structured run summary

**Step 4: Run test to verify it passes**

Run: `pytest apps/ashare-platform/backend/tests/test_collect_ephemeral_task.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/ashare-platform/backend/app/tasks/collect_ephemeral.py apps/ashare-platform/backend/app/pipelines/collect_ephemeral.py apps/ashare-platform/backend/tests/test_collect_ephemeral_task.py
git commit -m "feat: add ephemeral collection task"
```

### Task 6: Build and persist `trend_pool_daily`

**Files:**
- Create: `apps/ashare-platform/backend/app/pipelines/build_trend_pool.py`
- Create: `apps/ashare-platform/backend/app/tasks/build_trend_pool.py`
- Create: `apps/ashare-platform/backend/app/repositories/trend_pool_repository.py`
- Test: `apps/ashare-platform/backend/tests/test_build_trend_pool.py`

**Step 1: Write the failing test**

```python
def test_build_trend_pool_persists_daily_rows(session):
    from app.tasks.build_trend_pool import run

    result = run(trade_date="2026-03-13")
    assert result["rows_written"] >= 0
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/ashare-platform/backend/tests/test_build_trend_pool.py -v`
Expected: FAIL because task/repository is missing

**Step 3: Write minimal implementation**

- Read deterministic scan output
- Map rows into `trend_pool_daily`
- Persist through repository layer
- Attach `run_id` lineage

**Step 4: Run test to verify it passes**

Run: `pytest apps/ashare-platform/backend/tests/test_build_trend_pool.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/ashare-platform/backend/app/pipelines/build_trend_pool.py apps/ashare-platform/backend/app/tasks/build_trend_pool.py apps/ashare-platform/backend/app/repositories/trend_pool_repository.py apps/ashare-platform/backend/tests/test_build_trend_pool.py
git commit -m "feat: persist trend pool daily facts"
```

### Task 7: Build and persist `theme_pool_daily` and `theme_stock_daily`

**Files:**
- Create: `apps/ashare-platform/backend/app/pipelines/build_theme_pool.py`
- Create: `apps/ashare-platform/backend/app/tasks/build_theme_pool.py`
- Create: `apps/ashare-platform/backend/app/repositories/theme_pool_repository.py`
- Test: `apps/ashare-platform/backend/tests/test_build_theme_pool.py`

**Step 1: Write the failing test**

```python
def test_build_theme_pool_writes_theme_and_stock_rows(session):
    from app.tasks.build_theme_pool import run

    result = run(trade_date="2026-03-13")
    assert "themes_written" in result
    assert "stocks_written" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/ashare-platform/backend/tests/test_build_theme_pool.py -v`
Expected: FAIL because task/repository is missing

**Step 3: Write minimal implementation**

- Build theme daily facts from approved high-quality sources
- Keep numeric facts deterministic
- Leave LLM-only semantic fields nullable or fill through dedicated enrichment step

**Step 4: Run test to verify it passes**

Run: `pytest apps/ashare-platform/backend/tests/test_build_theme_pool.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/ashare-platform/backend/app/pipelines/build_theme_pool.py apps/ashare-platform/backend/app/tasks/build_theme_pool.py apps/ashare-platform/backend/app/repositories/theme_pool_repository.py apps/ashare-platform/backend/tests/test_build_theme_pool.py
git commit -m "feat: persist theme pool daily facts"
```

### Task 8: Add LLM enrichment step for semantic fields

**Files:**
- Create: `apps/ashare-platform/backend/app/pipelines/enrich_theme_semantics.py`
- Modify: `apps/ashare-platform/backend/app/tasks/build_theme_pool.py`
- Test: `apps/ashare-platform/backend/tests/test_theme_semantic_boundary.py`

**Step 1: Write the failing test**

```python
def test_theme_semantics_do_not_replace_deterministic_fields():
    enriched = {
        "theme_stage": "middle",
        "summary": "..."
    }

    assert enriched["theme_stage"] == "middle"
```

**Step 2: Run test to verify it fails or exposes missing enrichment boundary**

Run: `pytest apps/ashare-platform/backend/tests/test_theme_semantic_boundary.py -v`
Expected: FAIL because enrichment module is missing

**Step 3: Write minimal implementation**

- Add enrichment pipeline for semantic fields only
- Keep deterministic facts untouched
- Document the boundary in code comments and task flow

**Step 4: Run test to verify it passes**

Run: `pytest apps/ashare-platform/backend/tests/test_theme_semantic_boundary.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/ashare-platform/backend/app/pipelines/enrich_theme_semantics.py apps/ashare-platform/backend/app/tasks/build_theme_pool.py apps/ashare-platform/backend/tests/test_theme_semantic_boundary.py
git commit -m "feat: add llm semantic enrichment for theme pool"
```

### Task 9: Build and persist `market_review_daily`

**Files:**
- Create: `apps/ashare-platform/backend/app/pipelines/build_market_review.py`
- Create: `apps/ashare-platform/backend/app/tasks/build_market_review.py`
- Create: `apps/ashare-platform/backend/app/repositories/market_review_repository.py`
- Test: `apps/ashare-platform/backend/tests/test_build_market_review.py`

**Step 1: Write the failing test**

```python
def test_build_market_review_persists_report(session):
    from app.tasks.build_market_review import run

    result = run(trade_date="2026-03-13")
    assert result["stored"] is True
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/ashare-platform/backend/tests/test_build_market_review.py -v`
Expected: FAIL because pipeline is missing

**Step 3: Write minimal implementation**

- Build review from retained facts
- Keep structured fields plus markdown report
- Persist one row per trade date

**Step 4: Run test to verify it passes**

Run: `pytest apps/ashare-platform/backend/tests/test_build_market_review.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/ashare-platform/backend/app/pipelines/build_market_review.py apps/ashare-platform/backend/app/tasks/build_market_review.py apps/ashare-platform/backend/app/repositories/market_review_repository.py apps/ashare-platform/backend/tests/test_build_market_review.py
git commit -m "feat: persist market review daily reports"
```

### Task 10: Add read-only GET APIs

**Files:**
- Create: `apps/ashare-platform/backend/app/api/routes/runs.py`
- Create: `apps/ashare-platform/backend/app/api/routes/trend_pool.py`
- Create: `apps/ashare-platform/backend/app/api/routes/theme_pool.py`
- Create: `apps/ashare-platform/backend/app/api/routes/market_reviews.py`
- Create: `apps/ashare-platform/backend/app/schemas/api.py`
- Test: `apps/ashare-platform/backend/tests/test_api_routes.py`

**Step 1: Write the failing test**

```python
def test_trend_pool_daily_route_exists(client):
    response = client.get("/trend-pool/daily", params={"trade_date": "2026-03-13"})
    assert response.status_code in {200, 404}
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/ashare-platform/backend/tests/test_api_routes.py -v`
Expected: FAIL because route modules are missing

**Step 3: Write minimal implementation**

- Add GET-only routes for the approved resources
- Return shaped response schemas, not raw ORM objects
- Keep task execution out of HTTP API

**Step 4: Run test to verify it passes**

Run: `pytest apps/ashare-platform/backend/tests/test_api_routes.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/ashare-platform/backend/app/api apps/ashare-platform/backend/app/schemas/api.py apps/ashare-platform/backend/tests/test_api_routes.py
git commit -m "feat: add read-only platform api routes"
```

### Task 11: Add cleanup task for ephemeral data

**Files:**
- Create: `apps/ashare-platform/backend/app/tasks/cleanup_ephemeral_data.py`
- Create: `apps/ashare-platform/backend/app/services/retention_service.py`
- Test: `apps/ashare-platform/backend/tests/test_cleanup_ephemeral_data.py`

**Step 1: Write the failing test**

```python
def test_cleanup_ephemeral_removes_expired_files(tmp_path):
    from app.services.retention_service import cleanup_ephemeral

    removed = cleanup_ephemeral(tmp_path, max_age_days=0)
    assert isinstance(removed, int)
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/ashare-platform/backend/tests/test_cleanup_ephemeral_data.py -v`
Expected: FAIL because retention service is missing

**Step 3: Write minimal implementation**

- Implement file cleanup for ephemeral data
- Report removed files/bytes
- Keep retained DB assets untouched

**Step 4: Run test to verify it passes**

Run: `pytest apps/ashare-platform/backend/tests/test_cleanup_ephemeral_data.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/ashare-platform/backend/app/tasks/cleanup_ephemeral_data.py apps/ashare-platform/backend/app/services/retention_service.py apps/ashare-platform/backend/tests/test_cleanup_ephemeral_data.py
git commit -m "feat: add ephemeral retention cleanup task"
```

### Task 12: Update docs and developer entrypoints

**Files:**
- Modify: `docs/plans/2026-03-13-ashare-platform-restructure-design.md`
- Modify: `skills/ashare-assistant/SKILL.md`
- Modify: `skills/ashare-assistant/README.md`
- Modify: `packages/ashare-data/README.md`
- Create: `apps/ashare-platform/backend/tests/test_readme_commands.py`

**Step 1: Write the failing test**

```python
def test_docs_reference_platform_backend_paths():
    content = Path("skills/ashare-assistant/README.md").read_text(encoding="utf-8")
    assert "apps/ashare-platform" in content
```

**Step 2: Run test to verify it fails**

Run: `pytest apps/ashare-platform/backend/tests/test_readme_commands.py -v`
Expected: FAIL because docs are not updated

**Step 3: Write minimal implementation**

- Update docs to reflect new ownership boundaries
- Mark skill as downstream consumer of the platform API
- Update base package docs to describe reusable-library role

**Step 4: Run test to verify it passes**

Run: `pytest apps/ashare-platform/backend/tests/test_readme_commands.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add docs/plans/2026-03-13-ashare-platform-restructure-design.md skills/ashare-assistant/SKILL.md skills/ashare-assistant/README.md packages/ashare-data/README.md apps/ashare-platform/backend/tests/test_readme_commands.py
git commit -m "docs: align project docs with platform architecture"
```

### Task 13: Run verification suite

**Files:**
- Test: `packages/ashare-data/tests/test_trend_scanner_public_api.py`
- Test: `apps/ashare-platform/backend/tests/`

**Step 1: Run focused backend tests**

Run: `pytest apps/ashare-platform/backend/tests -v`
Expected: PASS

**Step 2: Run preserved ashare-data tests**

Run: `pytest packages/ashare-data/tests/test_trend_scanner_public_api.py -v`
Expected: PASS

**Step 3: Run syntax validation**

Run: `python -m py_compile $(find apps/ashare-platform/backend/app -name '*.py')`
Expected: no output

**Step 4: Review git diff**

Run: `git status --short`
Expected: only intended files modified

**Step 5: Commit**

```bash
git add -A
git commit -m "test: verify ashare platform backend slice"
```
