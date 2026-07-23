# Task Graph

Purpose: Convert approved work into a minimal executable dependency graph.
Sections: Node test | Edge test | Graph template

## Node Test

Create a node only when it has one owner, a concrete output, and an independent verification. Keep exploration, implementation, review, integration, and E2E as separate nodes when they can proceed independently.

## Edge Test

Draw `A → B` only when B needs A's output, A and B write the same target, or A changes the contract B consumes. Do not draw an edge because tasks merely sound sequential.

| Condition | Graph action |
|---|---|
| Independent inputs and disjoint writes | Run in parallel. |
| Shared writable file, schema, or mutable external record | Serialize through one owner. |
| Shared working tree or branch with disjoint owned files | Run in parallel; preserve concurrent edits. |
| Implementation needs a settled contract | Contract node precedes implementation. |
| Review evaluates an implementation | Implementation precedes independent review. |
| E2E needs all integrated behavior | All integration nodes precede E2E. |

## Graph Template

```text
contract ─┬─ implementation A ─┐
          ├─ implementation B ─┼─ integration ─ review ─ final gate
          └─ implementation C ─┘
```

Add only real nodes and edges. Prefer the smallest graph that preserves correctness.
