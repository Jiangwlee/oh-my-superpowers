---
name: graph-engineering
description: >-
  Use only when the user explicitly invokes /graph-engineering or explicitly names
  graph-engineering. Turn an approved, multi-part delivery into a dependency graph
  with owned nodes, independent implementation/review, integration verification,
  and an orchestrator handoff. Do NOT trigger from ordinary requests for coding,
  planning, delegation, or review.
---
# Graph Engineering

Purpose: Act as the orchestrator for approved multi-part work through an explicit dependency graph.
Input: An approved objective, boundaries, and success criteria.
Output: Verified integrated change, independent review, E2E result, and handoff.
Sections: Hard Gate | Workflow | References

## Hard Gate

| Condition | Action |
|---|---|
| Role | Act as the orchestrator: define the graph, assign ownership, coordinate dependencies, integrate, run final verification, and hand off. Do not absorb independently executable implementation nodes. |
| The user did not explicitly invoke this skill | Do not use it. |
| Objective, authority, or success criteria are unknown | Clarify one material gap before drawing the graph. |
| The work is a localized change with one owner and no independent branch | Do not build a graph; execute directly. |
| Two nodes write the same file, schema, or mutable external record | Add a dependency or assign one owner. Never run them in parallel. |
| A node cannot name its input, output, owner, and verification | Split or remove the node. |
| A node needs implementation | Dispatch an independent coding subagent with exclusive file/module ownership. |
| A completed implementation has no independent reviewer | Do not merge or hand off. Dispatch a reviewer who did not author that node. |
| No independent reviewer is available | State that review is not independent before implementation starts. |
| A node deploys, sends messages, changes third-party data, or mutates infrastructure outside the user-scoped workspace | Stop at the approval gate unless the user explicitly authorized that target and action. |

## Workflow

1. Frame the delivery: record objective, scope, constraints, authority, success criteria, and stop condition. Done: a reader can decide whether the work is complete without inference.
2. Draw the dependency graph. Read `references/task-graph.md`. Remove fake edges; serialize shared writes; assign one owner per node. Done: every node has explicit predecessors and no parallel write conflict.
3. Define node contracts. Read `references/node-contract.md`. Assign implementation, review, integration, and release nodes separately. Done: every node has a checkable output and verification command.
4. Dispatch ready nodes. Keep the orchestrator out of independent coding work. Give each coding subagent only its owned files and contract; reserve a different subagent for review; tell every worker that others edit concurrently. Done: every implementation node has one coding owner, one separate reviewer, and a completion report channel.
5. Integrate in topological order. Resolve interface conflicts at the orchestrator layer; do not ask workers to merge unrelated branches. Done: the combined change passes contract-level checks.
6. Run independent review. Give the reviewer the change, user goal, and review criteria; do not provide the orchestrator's expected findings. Done: every blocking finding is fixed and re-reviewed.
7. Run the final gate. Read `references/final-gate.md`. Execute required tests, type checks, lint, build, and user-authorized E2E against the integrated result. Done: every success criterion has evidence or an explicit blocker.
8. Hand off. Summarize outcome, evidence, remaining risks, and commit only after the final gate passes. Done: the user can verify the result from the handoff alone.

## References

| File | Use | When |
|---|---|---|
| `references/task-graph.md` | Graph construction and edge rules | Step 2 |
| `references/node-contract.md` | Node ownership and dispatch contract | Steps 3–4 |
| `references/final-gate.md` | Integration, review, E2E, and handoff checklist | Steps 5–8 |
