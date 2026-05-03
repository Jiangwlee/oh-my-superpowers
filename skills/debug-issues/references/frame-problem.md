# Frame the Problem

Phase 1 SOP. Capture the failure as observable facts before any hypothesis or repro work.

## Hard Gate

<HARD-GATE>
Skip questioning entirely if the report already contains:
- Symptom (what is wrong, observable)
- Reproduction steps (how to trigger)
- Expected vs actual behavior
- Environment (where it happens)
- Recency (when it started, what changed)

If complete, write the frame summary directly and proceed to Phase 2.
</HARD-GATE>

## Question Set

Ask up to 5 focused questions in one batch. Stop once the frame can be written.

| Dimension | Question template | Skip when |
|---|---|---|
| Symptom | What exactly fails? Error message, stack trace, exit code, visible behavior? | Stack trace already provided |
| Reproduction | What command, action, or URL triggers it? Smallest sequence? | Repro steps already provided |
| Expected vs actual | What should happen vs what does happen? | Already implied by symptom |
| Environment | Local / staging / prod? OS, browser, branch, version? | Already specified |
| Recency | When did it start? What changed recently (code, config, data, dependency)? | Already specified |
| Scope | Reproducible every time, or intermittent? Specific user / config / data? | Already specified |

## Output

Write the frame as a one-block summary, then proceed to Phase 2:

```
Symptom: <one line, observable>
Repro:   <smallest sequence>
Expected: <one line>
Actual:   <one line>
Env:     <branch / version / host / browser>
Recency: <since when, what changed>
Scope:   <every time | intermittent | conditional>
```

## Anti-patterns

- Do NOT ask "what do you think the cause is?" — Phase 1 captures observation, not theory.
- Do NOT exceed 5 questions per batch.
- Do NOT re-ask facts already in the report.
- Do NOT proceed to Phase 2 without a one-line symptom.
- Do NOT pad with theoretical follow-ups; defer those to Phase 4.
