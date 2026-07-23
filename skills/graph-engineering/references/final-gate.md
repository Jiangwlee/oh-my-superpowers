# Final Gate

Purpose: Prevent locally correct graph nodes from shipping an incorrect integrated result.
Sections: Integration | Independent review | Verification | Handoff

## Integration

- Reconcile contracts and imports in topological order.
- Run a diff check before tests.
- Reject duplicate ownership, compatibility shims, and unreviewed cross-node changes.

## Independent Review

- The orchestrator assigns a reviewer that did not implement the reviewed node.
- Give it the user objective, changed files, and applicable project rules.
- Fix every blocking finding; re-run review on the fix.

## Verification

| Level | Required evidence |
|---|---|
| Node | Focused tests and static checks named in its contract. |
| Integration | Affected suite, type check, lint, and diff check. |
| Release | Build and user-authorized real-path E2E when user-visible behavior changed. |

Do not substitute unit tests for a user-authorized E2E. Do not claim an E2E passed when the target service, credential, or external dependency was unavailable.

## Handoff

State the outcome first. List commit, evidence, remaining risks, and any blocked verification. Keep the final answer self-contained.
