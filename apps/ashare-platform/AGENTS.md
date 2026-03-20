# Repository Guidelines

## Project Structure & Module Organization
```text
apps/ashare-platform/
├── AGENTS.md
└── backend/
    ├── app/
    │   ├── api/routes/        # Read-only FastAPI endpoints
    │   ├── tasks/             # Task entrypoints and run logging
    │   ├── pipelines/         # Daily data-building pipelines
    │   ├── services/          # Semantic enrichment and retention logic
    │   ├── repositories/      # Database access layer
    │   ├── models/            # SQLAlchemy models
    │   ├── schemas/           # API schemas
    │   ├── core/              # Config and runtime helpers
    │   ├── cli.py             # `ashare-platform` CLI
    │   └── main.py            # FastAPI app entrypoint
    ├── tests/                 # Pytest suite
    ├── data/
    │   ├── ephemeral/         # Generated snapshots and short-lived inputs
    │   └── retained/          # Retained SQLite data
    ├── README.md
    ├── pyproject.toml
    └── Dockerfile
```

Treat `backend/data/` as generated runtime output, not hand-edited source.

## Build, Test, and Development Commands
Use the repository root virtualenv.

```bash
./.venv/bin/python -m pip install -e apps/ashare-platform/backend
./.venv/bin/uvicorn app.main:app --app-dir apps/ashare-platform/backend --host 127.0.0.1 --port 8000
./.venv/bin/python -m pytest apps/ashare-platform/backend/tests/ -v
./.venv/bin/python -m py_compile apps/ashare-platform/backend/app/<file>.py
./.venv/bin/python -m app.cli build-theme-pool --date 2026-03-13
```

The editable install exposes the `ashare-platform` CLI. Run task commands from `backend/app/cli.py` for pipeline verification.

## Coding Style & Naming Conventions
Target Python 3.10+. Use 4-space indentation, explicit type hints, and Google-style docstrings for public functions. Keep imports grouped as standard library, third-party, then local modules. Follow existing naming: modules and functions in `snake_case`, classes in `PascalCase`, constants in `UPPER_SNAKE_CASE`. Prefer deterministic pipeline code over compatibility layers; do not add fallback code paths just to preserve older behavior.

## Testing Guidelines
Tests use `pytest`. Name files `test_*.py` and keep new coverage close to the changed behavior, especially for API routes, task orchestration, and semantic enrichment boundaries. Before submitting, run the full backend test suite and a syntax check on changed Python files. If you touch CLI or README-visible commands, add or update tests like `backend/tests/test_cli.py` or `backend/tests/test_readme_commands.py`.

## Commit & Pull Request Guidelines
Recent history uses Conventional Commit prefixes such as `feat:`, `fix:`, and `docs:`; keep that format, optionally scoping when useful, for example `fix(api): guard empty review payload`. Each PR should cover one coherent change, explain the behavioral impact, list the commands used for validation, and include sample request/response details when API behavior changes.

## Security & Configuration Tips
Do not commit secrets or hardcode API keys. Use environment variables such as `ASHARE_PLATFORM_HOME`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, and `OPENAI_API_KEY` for runtime configuration. Keep generated databases and ephemeral snapshots out of manual edits.
