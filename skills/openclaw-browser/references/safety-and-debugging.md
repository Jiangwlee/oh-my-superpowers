# OpenClaw Browser Safety And Debugging

Purpose: Explain the highest-risk failure modes in `openclaw browser` workflows and
         how to recover without guessing.
Input:   A browser task that is failing, drifting, or producing uncertain output.
Output:  Guardrails and recovery rules for ref safety, synchronization, tab targeting,
         JSON output, and controlled JS evaluation.
Sections: Ref Safety | Synchronization | Targeting | JSON Output | JS Evaluation | Recovery

## Ref Safety

- A `ref` is only valid for the snapshot that produced it.
- After navigation, form submission, filter changes, modal transitions, or major re-rendering, assume old refs are stale.
- If an action changes the page, re-run `snapshot` before the next ref-based command.
- Never guess a ref from memory or from a prior page state.

## Synchronization

Prefer explicit waiting signals:

1. `wait --load`
2. `wait --url`
3. `wait --text`
4. wait on a selector

Use `wait --time` only as a short supplement, not as the main proof of readiness.

## Targeting

- Use `tabs` when you are unsure which page is active.
- Use `focus <target-id>` before acting in multi-tab sessions.
- Use `--target-id <id>` for commands that must not depend on the current focus.
- Use named browser profiles when one task must not contaminate another.

## JSON Output

Prefer `--json` when:

- another tool or script will consume the result
- you need stable machine-readable output
- you want to avoid ambiguity in status or log parsing

Plain text is fine for quick manual inspection, but structured workflows should prefer JSON.

## JS Evaluation

`evaluate --fn` and `wait --fn` are powerful and risky.

Prefer not to use them when:

- snapshot already exposes what you need
- a visible text, selector, URL, or load state can express readiness
- the task is a normal form interaction or page read

Use them when:

- you need page-only data that no other command exposes
- the readiness condition is internal app state
- you can write a small, direct function with no unnecessary side effects

Keep the function short and inspect-only whenever possible.

## Recovery

If a workflow fails:

1. Confirm the browser is running with `status`
2. Confirm you are on the right tab with `tabs` and `focus`
3. Re-wait for a stable signal
4. Re-run `snapshot`
5. Retry the smallest safe action
6. If it still fails, collect `console`, `requests`, `errors`, or a `screenshot`

Do not escalate to complex JS or repeated blind clicks before collecting evidence.
