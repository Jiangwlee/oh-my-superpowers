# Story: fake

> Design: /docs/brainstorming/specs/2026-04-19-fake.md

## Goal

Fixture story used to validate brainstorming → coding-orchestrator handoff contract. Not a real story.

## Scope

Two waves. Wave 1 has one task (spec written). Wave 2 has one task (spec null, awaiting JIT write by orchestrator).

## Acceptance Criteria

- Orchestrator can dispatch wave 1 without manual intervention.
- Orchestrator cannot dispatch wave 2 until its spec is written.
