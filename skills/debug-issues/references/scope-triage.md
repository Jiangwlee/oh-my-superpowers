# Scope Triage

Phase 3 SOP. Narrow the suspect space along three axes before listing hypotheses.

## Three Discriminations

| Axis | Question | Tools |
|---|---|---|
| **Layer** | Browser render / network / API / business / data / 3rd-party / infra — which layer fails? | Stack trace, network panel, log component tags |
| **Ownership** | Our code or external (lib, 3rd-party service, OS, browser engine)? | `git log -p`, `git blame`, package vendor, version diff |
| **Side** | Frontend, backend, or cross-side? | Symptom location, request / response boundary |

## Decision Order

1. **Layer first** — symptom tells you where, not why.
2. **Ownership next** — if external, the fix shape changes (workaround / version pin / report upstream).
3. **Side last** — if cross-side, treat each side separately and verify the boundary contract.

## Output

Declare the scope before Phase 4:

```
suspect_layer: <e.g., frontend.network | backend.business | integration.3rdparty>
ownership:    <ours | vendor:<name> | infra>
side:         <frontend | backend | cross>
```

Phase 4 hypotheses must stay inside the declared scope. If a hypothesis requires breaking out, re-run scope triage first.

## Quick Patterns

| Symptom shape | Likely layer / side |
|---|---|
| 4xx / 5xx HTTP, network panel shows request | frontend ↔ backend boundary |
| JS console error before any network request | frontend only |
| Log shows entry, no log shows exit | backend, inside that function |
| Behavior differs across browsers / OS | environment / runtime |
| Worked yesterday, broken today, no code change | environment / data / external |
| New feature broken, old paths fine | recent diff scope |
| Local works, staging / prod fails | env config / network / data shape |
| First request slow, subsequent fast | cold start / cache / connection pool |

## Anti-patterns

- Do NOT skip triage and go straight to hypotheses — wide scope produces shotgun fixes.
- Do NOT declare ownership "ours" without checking recent diffs and dependency versions.
- Do NOT re-declare scope mid-investigation without re-listing hypotheses.
