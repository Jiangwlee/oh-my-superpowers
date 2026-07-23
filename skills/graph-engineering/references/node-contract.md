# Node Contract

Purpose: Give the orchestrator a conflict-free contract for each delegated node.
Sections: Required fields | Dispatch template | Completion report

## Required Fields

| Field | Requirement |
|---|---|
| Objective | One observable result. |
| Ownership | Exact files, modules, or external state. |
| Inputs | Upstream contracts or facts the node may rely on. |
| Outputs | Files, API contract, report, or test evidence produced. |
| Constraints | Architecture, safety, and non-overlap rules. |
| Verification | Exact command or observation proving completion. |
| Separation | Name the coding owner and a different review owner. |

## Dispatch Template

```text
Role: Coding subagent. Do not review your own change.
Own: src/example/ and its mirror tests.
Input: the approved EventEnvelope contract.
Output: implementation plus passing focused tests.
Do not edit: API routes, shared contracts, or docs owned by other nodes.
You are not alone in the codebase. Preserve concurrent edits and adapt to them.
Verify: pnpm exec vitest run src/example/__tests__/feature.test.ts
Report: changed files, verification output, assumptions, and blockers.
```

## Completion Report

Report only: output delivered, files changed, verification evidence, unresolved risks, and assumptions. Do not claim integration success unless the node owns integration. The orchestrator assigns a different subagent to review this output.
