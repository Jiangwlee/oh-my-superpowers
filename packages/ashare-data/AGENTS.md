# Repository Guidelines

## Project Structure & Module Organization
`ashare-data` is a Python package for A-share data collection and preprocessing.

- `ashare_data/core/`: shared infrastructure (paths, HTTP client, cache, watchlist, scraper).
- `ashare_data/fetchers/`: source-specific collectors (news, funding, sentiment, broker, etc.).
- `ashare_data/*.py`: CLI entry modules such as `collect.py`, `diagnose.py`, and monitors/pipelines.
- `tests/`: unit tests for core modules, fetchers, and CLI flows (`test_*.py`).
- `README.md`: usage and operational background.
- `pyproject.toml`: package metadata, dependencies, and CLI script registration.

## Build, Test, and Development Commands
- `pip install -e .`: install in editable mode from this directory.
- `python -m unittest discover -s tests -p "test_*.py"`: run full test suite.
- `python -m unittest tests.test_funding_fetcher`: run one test module.
- `python -m py_compile ashare_data/core/http_client.py`: quick syntax check for a file.
- `ashare-collect --verbose`: run the main daily collection pipeline (after install).
- `ashare-wl-monitor --force`: run watchlist scanner without time/holiday gating (debug only).

## Coding Style & Naming Conventions
- Python 3.10+ only; use type hints (`str | None`, `list[dict[str, Any]]`).
- Import order: standard library, third-party, local modules.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_CASE`.
- Use `logging.getLogger(__name__)`; prefer `logger.exception(...)` in failure paths.
- Keep fetch functions resilient: catch exceptions and return empty collections where appropriate.
- Parse HTML with structured parsers/selectors; do not use regex for HTML extraction.

## Doc Style
- **NEVER** write document/comments for methods and functions in a Python file
- Every python file should only contains one document at the beginning of the file
- Python file document should follow rules from [File Header Spec](../../File-Header-Spec.md)

## Testing Guidelines
- Framework: `unittest` (run through Python module invocation).
- Test files must be named `test_*.py`; test methods should describe behavior (e.g., `test_fetch_returns_empty_on_timeout`).
- Add/update tests for every behavior change in `core/`, `fetchers/`, or CLI workflows.

## Commit & Pull Request Guidelines
- Follow Conventional Commit style seen in history: `feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`, optionally scoped (`fix(task-runner): ...`).
- Keep commits focused and atomic; separate refactor from behavior changes.
- PRs should include:
  - concise summary and motivation,
  - impacted modules/commands,
  - test evidence (exact command + result),
  - sample output when changing CLI behavior.

## Update Review
- Update `README.md` when new feature is added or refactoring happens