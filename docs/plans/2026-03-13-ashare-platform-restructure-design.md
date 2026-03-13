# A-Share Platform Restructure Design

Purpose: Record the approved direction for refactoring the current A-share
         stack from skill-heavy workflows into a data-platform-first product.
Audience: Project maintainers designing `ashare-data`, `ashare-assistant`,
          and the future `apps/ashare-platform` subproject.
Usage:   Read before moving code, creating new modules, or introducing API/db
         boundaries; this document captures scope, constraints, and key choices.
Sections: Background | Current State | Goals | Decisions | Architecture
          | Storage | Repository Boundaries | Non-Goals | Open Items

**Date**: 2026-03-13
**Author**: Codex
**Status**: Drafted from approved brainstorming decisions
**Scope**: V1 refactor direction, not implementation detail

---

## 1. Background

The current stack has two main parts:

- `packages/ashare-data`: data collection, preprocessing, trend scanning, and
  several trading-oriented deterministic tools
- `skills/ashare-assistant`: LLM workflow orchestration for market review,
  stock picking, and trading-plan generation

After multiple refactors, the main pain point is no longer workflow design.
The primary problem is that the project does not yet expose a clean, reusable,
tool-first data platform. As a result:

- skills are forced to become heavy
- file outputs act as implicit APIs
- business logic, data processing, and workflow orchestration are entangled

The approved direction is to rebuild around a data platform first, then let
skills, apps, and future workbenches consume that platform as thin clients.

## 2. Current State Review

The current codebase already contains meaningful assets and should not be
treated as greenfield.

### 2.1 Mature areas to preserve

The following areas were identified as broadly mature and worth preserving:

1. Data collection
2. Data processing
3. Trend scoring

These are considered the strongest existing base and should be optimized, not
replaced wholesale.

### 2.2 Existing capabilities already present

`packages/ashare-data` already provides:

- multi-source collection for news, market sentiment, sector flow, East Money
  popularity ranking, Taoguba, JVQuant account data, and US market snapshots
- raw-to-consumable transformation logic
- deterministic trend scoring
- watchlist maintenance and stateful monitoring
- post-close decision pipeline and intraday monitoring prototypes
- batch metadata, retention, manifest, and degradation flags

`skills/ashare-assistant` already provides:

- daily market review workflow
- candidate generation workflow
- trading plan workflow
- deterministic risk checking, output validation, and decision logging

### 2.3 Structural problems

The current architecture has the following issues:

- `ashare-data` contains both reusable data capabilities and application-level
  business logic
- `ashare-assistant` consumes files rather than stable platform resources
- markdown outputs are acting as de facto APIs
- data products, trading logic, and workflow prompts are not cleanly separated

## 3. Refactor Goals

The approved V1 goals are:

1. Build a tool-first A-share data platform
2. Expose the platform primarily through HTTP API
3. Keep skills thin and downstream of the platform
4. Strengthen data processing before revisiting trading decision logic

This refactor explicitly prioritizes:

- data collection quality
- data processing quality
- trend scoring quality

The user explicitly wants to defer “trading decision system” work until the
foundation is stronger.

## 4. Approved Decisions

### 4.1 Product direction

The platform direction is:

`A-share data platform -> HTTP API -> Skill/App/Workbench`

Skills are not the center of the architecture. They are consumers.

### 4.2 Primary interface

The primary interface for the platform will be:

- `HTTP API`

This was preferred over Python-only API and CLI-first design because it best
supports future Docker deployment, frontend/backend separation, skills, and
other orchestration layers.

### 4.3 First refactor focus

The first refactor focus will be:

- `data processing layer`

Reason:

- it sits between collection and future API
- it determines which data is worth retaining
- it shapes the platform’s long-term resource model
- it is where signal quality can improve without prematurely rebuilding
  decision logic

### 4.4 Theme discovery scope

The project will **not** start with automatic discovery of new themes.

The approved initial interpretation is:

- use existing hot themes/hot sectors as they appear from existing sources,
  especially Tonghuashun-style theme information
- use community sentiment only to assess attitude, strength, and stage
- focus on main themes and their strong stages
- avoid trading late-stage or exhausted themes

This is explicitly narrower than “discover new themes from news/social media”.

### 4.5 Preserve-and-improve areas

The current mature areas should be improved through:

1. Better abstraction
   - reduce duplication
   - improve maintainability
   - improve observability
2. Better source trimming
   - reduce noisy sources
   - prefer high-quality sources such as curated Taoguba content
3. Better prompts
   - improve LLM analysis prompts after the data processing inputs are improved

### 4.6 Deterministic vs LLM responsibility

The approved implementation principle is:

`Facts are produced by code. Interpretations are produced by LLMs.`

More explicitly:

- anything that can be computed directly and stably from numeric or structured
  data should be implemented in code
- anything that requires semantic understanding, summarization, attitude
  judgment, or stage interpretation may be generated by LLMs

#### Code should own

- data collection
- cleaning, normalization, and deduplication
- trend scoring
- ranking, thresholds, and statistics
- pool inclusion/exclusion rules
- structured fact extraction
- run status, lineage, retention, and cleanup

#### LLMs should own

- sentiment and attitude summaries from curated high-quality text
- semantic explanation of theme strength
- semantic stage judgment and narrative interpretation
- daily review summarization
- multi-source evidence synthesis when language understanding is required

This boundary is intended to prevent a return to mixed logic where prompts,
scripts, and workflow files all try to compensate for one another.

## 5. Data Processing Architecture

### 5.1 Core role

The data processing layer should not be understood as “JSON to markdown”.

Its real role is to:

- standardize data
- remove noise
- refine evidence
- create stable datasets that can later be exposed through HTTP API

### 5.2 Recommended processing model

The approved conceptual model is:

`raw source data -> normalized datasets -> curated analytical datasets -> optional LLM-ready views`

Interpretation:

- `raw`: source dumps and temporary capture artifacts
- `normalized`: unified schema, codes, timestamps, source tags
- `curated`: high-value datasets for platform use
- `views`: consumer-specific derived views such as markdown or presentation

The key platform asset is the `curated` layer, not the markdown layer.

### 5.3 Initial high-value long-term outputs

The following were identified as the most valuable long-term structured
outputs:

- trend stock pool
- theme stock pool
- daily market review report

These should become first-class long-term data assets.

## 6. Storage Strategy

The approved storage strategy is a two-tier model.

### 6.1 Ephemeral data: files

News, forum posts, and similar highly time-sensitive material are considered
short-lived evidence. They should:

- live in files
- be subject to regular cleanup
- not be retained indefinitely

These are not core long-term assets.

### 6.2 Retained data: database

Structured outputs with recurring strategic value should go into a database.

Examples:

- trend pools
- theme pools
- market review reports
- run metadata and batch history

This creates a clear split:

- temporary evidence layer -> files
- retained analytical assets -> database

### 6.3 Database need

The user explicitly considers a database necessary for the retained layer.
This is approved as part of the V1 direction.

## 7. Framework and Dependency Decisions

### 7.1 Pipeline framework

No heavy pipeline orchestration framework will be introduced in V1.

Specifically:

- do not introduce Prefect now
- do not introduce Dagster or Airflow now

Reason:

- current complexity does not justify them
- the hard problem is still data modeling and boundary design
- a custom lightweight pipeline will keep the first refactor simpler

### 7.2 Approved technical posture

The agreed technical stance is:

- introduce dependencies early when they support the long-term architecture
- avoid premature heavy orchestration

The recommended V1 posture discussed was:

- FastAPI
- Pydantic
- SQLAlchemy or SQLModel
- SQLite first
- Alembic when database schema migration becomes real

The concrete package decision remains open, but the architectural direction is
approved.

## 8. Repository and Module Boundaries

### 8.1 New subproject location

The future platform should **not** remain coupled to `packages/`.

Approved location:

```text
apps/
  ashare-platform/
    backend/
    frontend/
```

This reflects the fact that the future platform is an application product, not
just a reusable library.

### 8.2 What stays in `packages/ashare-data`

`packages/ashare-data` should remain a reusable base library and keep:

- source connectors/fetchers
- shared HTTP, cache, parsing, config, and utility code
- standardization helpers
- core trend-scoring capability

It should increasingly represent “reusable capability”, not “platform product”.

### 8.3 What moves to `apps/ashare-platform/backend`

The future backend should own:

- data processing pipelines
- trend pool generation
- theme pool generation
- market review generation and persistence
- database models and repositories
- HTTP API
- retention policy for platform-specific temporary data
- task entrypoints and future service-facing interfaces

### 8.4 Modules likely to migrate out of `ashare-data`

The following existing modules were identified as likely platform-level rather
than base-library-level:

- `collect.py`
- `filter_to_markdown.py`
- `post_close_decision_pipeline.py`
- `watchlist_monitor.py`
- `diagnose.py`
- likely `core/watchlist.py`

These are candidates for migration or splitting during implementation.

### 8.5 Module treatment strategy

The current `ashare-data` modules should be treated in three groups during the
refactor.

#### Reuse directly

These are good candidates to remain in `packages/ashare-data` with only light
cleanup or interface polishing:

- `fetchers/market_sentiment.py`
- `fetchers/market_overview.py`
- `fetchers/taoguba.py`
- `core/http_client.py`
- `core/cache.py`
- `core/scraper.py`
- `core/utils.py`

#### Keep core value but split responsibilities

These contain valuable logic but currently mix too many concerns:

- `fetchers/trend_scanner.py`
- `collect_sentiment.py`
- `filter_to_markdown.py`

Their reusable logic should stay available, but product-facing pipeline,
presentation, and orchestration concerns should move upward.

#### Migrate to platform backend

These are application-level modules and should be migrated, replaced, or
restructured inside `apps/ashare-platform/backend`:

- `collect.py`
- `post_close_decision_pipeline.py`
- `watchlist_monitor.py`
- `diagnose.py`
- `core/watchlist.py`

## 9. Proposed Backend Layout

The approved high-level backend structure is:

```text
apps/
  ashare-platform/
    backend/
      app/
        api/
          routes/
        core/
        db/
        models/
        services/
        pipelines/
        repositories/
        schemas/
        tasks/
        main.py
      tests/
      alembic/
      pyproject.toml
      README.md
      Dockerfile
```

Important emphasis:

- `pipelines` are first-class
- the backend is not API-first in spirit; it is pipeline-first with API as a
  serving layer

## 10. Non-Goals for This Phase

The following are explicitly out of scope for the current phase:

- rebuilding the skill as the center of the architecture
- designing a full trading decision system first
- automatic discovery/naming/merging of brand-new themes
- introducing a heavy workflow orchestration framework
- optimizing for frontend/workbench before the data foundation is stable

## 11. Immediate Next Design Topics

The next design topics, in order, should be:

1. core retained data objects
   - `trend_pool`
   - `theme_pool`
   - `market_review`
2. database table design for those objects
3. precise split between file-based ephemeral data and DB-retained data
4. pipeline module boundaries inside `apps/ashare-platform/backend`

## 12. Open Items

The following items remain intentionally open:

- final database toolkit choice: `SQLAlchemy` vs `SQLModel`
- exact schema for trend/theme/review tables
- exact retention period for ephemeral data
- exact API resource design
- prompt redesign strategy after data processing inputs are improved

## 13. Summary

This refactor is not a skill rewrite. It is a platform extraction.

The approved direction is:

- keep and strengthen collection, processing, and trend scoring
- make data processing the first refactor target
- retain temporary evidence in files
- store long-term analytical assets in a database
- move toward `apps/ashare-platform` as a separate product
- expose the platform through HTTP API
- keep orchestration lightweight for now
