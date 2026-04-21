# Coding Guideline For Debugging

Behavioral rules for debugging code without expanding scope or hiding
uncertainty.

## 1. Think Before Coding

Do not silently assume the cause.

- State assumptions explicitly.
- If multiple explanations fit the evidence, keep multiple hypotheses alive.
- If the failure is still unclear, stop and gather more evidence.
- Treat your current understanding as a model to test, not a fact.

## 2. Simplicity First

Fix today's bug with the minimum code that solves it.

- Do not add abstractions for one-off fixes.
- Do not add configurability that the bug does not require.
- Do not widen the patch "while you are here."
- If a 10-line fix works, do not ship a 100-line redesign.

## 3. Surgical Changes

Touch only the code needed for the root cause.

- Match the existing local style.
- Do not refactor adjacent code unless the fix directly requires it.
- Do not remove unrelated dead code you happened to notice.
- If your own change created unused imports or helpers, remove those.

Test every changed line against the debugging goal: if it does not help fix the
reported behavior, it probably does not belong in the patch.

## 4. Goal-Driven Execution

Turn "debug this" into a verifiable loop.

1. Reproduce the failure.
2. Gather evidence that narrows the cause.
3. Apply the smallest change that matches the evidence.
4. Verify the original failure is gone.
5. Verify related behavior still works.

Weak goals create wandering fixes. Strong goals create tight loops.

## Anti-Patterns

- Hidden assumptions about scope, data shape, or expected behavior
- Rewriting code before evidence points to the real cause
- Broad cleanup mixed into a bug fix
- Declaring success before rerunning the failing path

## Key Insight

Debugging quality is mostly about constraint. The strongest fixes come from
clear evidence, small patches, and explicit verification.
