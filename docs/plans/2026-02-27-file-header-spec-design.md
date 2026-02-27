# File Header Spec Design

Purpose: Design record for the File Header Spec convention.
Audience: Project maintainers.
Sections: Context | Decision | Deliverables

## Context

The project has 52 Python files and ~20 markdown files across 7 skills.
93% of scripts already have module-level docstrings, but content and
structure vary. No formal spec existed for what the first 20 lines
should contain. AI agents waste context loading files they don't need.

## Decision

Adopt a structured file header convention (File-Header-Spec.md) with:

- **20-Line Rule**: first 20 lines must convey Purpose, I/O, Public API
- **English-first**: headers in English; Chinese only for trigger phrases
- **Sync-or-delete**: stale headers must be updated or removed
- **Three Python templates**: script, library module, test
- **Three Markdown templates**: SKILL.md, reference doc, project-level doc
- **Writing rules**: verb-first Purpose, concrete formats, behavior-not-name
- **Sync trigger table**: maps code changes to header fields

## Deliverables

- `File-Header-Spec.md` — standalone spec at project root
- `AGENTS.md` — added reference link in 规范参考 section
