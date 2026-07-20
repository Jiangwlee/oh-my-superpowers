---
name: code-review
description: >-
  Review and improve local code changes: uncommitted work (staged, unstaged,
  or untracked) or recent commits (latest one by default, or a user-selected
  count). Use when code needs independent review, verification, and iterative
  fixes until no new confirmed issues remain.
  Do NOT use for PR review or branch comparison.
---

## Review Flow

Create a run-scoped temporary directory, set `review_round` to `1`, then track each step and complete them in order. A review round may use one or more batches and counts once only after the entire review target has been covered and all batch results have been collected. The executor may be a subagent or the inline fallback.

```bash
review_run_dir=$(mktemp -d /tmp/code-review.XXXXXX)
```

1. **Get diff** — determine review target, inventory every changed path, and collect changes
2. **Assess risk and scope** — identify relevant review dimensions and decide whether the diff needs batching
3. **Gather context** — collect project instructions, module contracts, original requirements, and results from the previous validation cycle
4. **Load checklist** — always read the core checklist; load the extended checklist when the change or its risks require it
5. **Load output format** — read `references/output-format.md`
6. **Assemble review prompts** — number the round's batches from `1`; use batch `1` when no split is needed. For each batch, set `review_prompt_file="$review_run_dir/prompt-round-${review_round}-batch-${review_batch}.md"`, then fill `assets/review-prompt-template.md` with `{context}`, that batch's `{diff}`, `{checklist}`, and `{output_format}` and write it to that file
7. **Select executor** — choose execution method (see Executor Selection)
8. **Dispatch review** — send every batch required to cover the review target to the executor
9. **Collect candidates** — confirm that every changed path is covered, then aggregate and parse all batch findings and provisional Verdicts for the round
10. **Validate output contract** — require the sections and fields defined in `references/output-format.md`. If the output is malformed or incomplete, ask the same executor once to correct only the format without adding, removing, or changing findings. Do not count this correction as a review round. If the corrected output is still invalid, treat the executor as failed and follow the degradation strategy
11. **Verify findings** — independently check every candidate against the code, surrounding context, and project requirements; reject unsupported findings
12. **Validate current state** — run the relevant tests, type checks, lint, or build commands for the reviewed scope; treat failures caused by the reviewed changes as verified issues and record every command and result
13. **Fix and re-review** — if verified P0-P2 issues or relevant validation failures remain and `review_round < 7`, fix them, increment `review_round`, and return to step 1 with the validation results
14. **Stop on non-convergence** — if verified P0-P2 issues or relevant validation failures remain in round 7, stop without starting another cycle and report the remaining findings, completed fixes, validation results, and non-convergence
15. **Finish** — when no new verified P0-P2 issues remain and relevant validation passes, present the final result, fixes applied, and validation results; if a relevant check cannot run, report the limitation explicitly

## Review Target

| Scenario | Command |
|----------|---------|
| Uncommitted changes | `git status --short --untracked-files=all` + `git diff HEAD` + `git ls-files --others --exclude-standard` |
| Recent N commits | Pin `review_base` once with `git rev-parse HEAD~N`, then use `git diff "$review_base"` in every cycle (default N=1) |

For uncommitted changes:

1. Treat `git status --short --untracked-files=all` as the complete path inventory.
2. Collect the final combined state of all staged and unstaged tracked changes with `git diff HEAD`. Do not concatenate separate staged and unstaged patches.
3. Enumerate untracked files with `git ls-files --others --exclude-standard`. Render each untracked text file as a new-file diff from `/dev/null` to its repository path.
4. Verify that every path in the inventory is present in the assembled review input. List binary, generated, oversized, or unreadable files as explicit exclusions with a reason; never omit a path silently.

For recent commits:

1. Require `git status --short --untracked-files=all` to produce no output before the first review. If the working tree is not clean, stop and ask the user to switch to uncommitted review or clean it; never stash, reset, or discard changes automatically.
2. Resolve the review base once before the first review. Set `review_commit_count` from the user's requested N, defaulting to `1`, then run:

   ```bash
   review_base=$(git rev-parse "HEAD~${review_commit_count}")
   ```

3. Keep the resolved `review_base` unchanged for the entire fix-and-review loop. Do not recompute it if HEAD changes.
4. In every cycle, review `git diff "$review_base"` so the input contains the original commits plus all tracked fixes in the working tree. Include untracked files using the same inventory, rendering, exclusion, and coverage rules as uncommitted review.

## Checklist Loading & Batching

- Always read `references/review-checklist-core.md`.
- Read `references/review-checklist-extended.md` when the change touches performance-sensitive paths, concurrency, I/O, public interfaces, class or module design, or other non-trivial structural risks. Load it whenever the reviewer identifies another relevant risk; diff length does not restrict its use.
- Use diff size, file boundaries, and the executor's available context only to decide whether batching is needed. Let the reviewer choose the batching strategy.
- Treat all batches that collectively cover the same review target as one review round. Individual batch results do not increment `review_round`; aggregate all of them before verification, validation, or fixes begin.
- Give every batch its own `review_batch` number and prompt file. Never overwrite or reuse another batch's prompt file.

## Executor Selection

Default: use the current runtime's native subagent mechanism to run the review in an isolated context. Use `omp dispatch` only when the user explicitly requests review by a different runtime.

### Sub agent (default)

Dispatch the assembled prompt to an isolated subagent through the current runtime's native mechanism. Do not perform the review in the initiator's context unless the degradation strategy reaches its final fallback.

### Cross-runtime review with omp dispatch

When the user explicitly requests a different runtime, set `review_runtime` to the requested `claude`, `codex`, or `pi` runtime, then dispatch the current round's `review_prompt_file`:

```bash
review_runtime=codex  # Set to the user-requested claude, codex, or pi runtime.
omp dispatch run "$review_runtime" \
  --prompt-file "$review_prompt_file" \
  --timeout 600
```

ANSI-clean output goes to stdout. Exit codes: `0` success, `124` timeout, `1` worker error.

### Live observation (optional)

Spawn the selected runtime, then tail/wait separately if you want to watch progress:

```bash
review_session_id=$(omp dispatch spawn "$review_runtime" --prompt-file "$review_prompt_file")
omp dispatch tail "$review_session_id" --follow &
omp dispatch wait "$review_session_id" --timeout 600
```

### Cleanup

After the skill finishes or stops, clean up only resources created by this run:

```bash
if [[ -n "${review_run_dir:-}" && -d "$review_run_dir" ]]; then
  rm -r -- "$review_run_dir"
fi
```

## Degradation Strategy

When an executor fails, degrade and inform the user:

An output-contract failure after the single format-correction attempt counts as an executor failure. Enter the branch for the executor currently in use.

```
Cross-runtime review requested
  → omp dispatch fails (spawn error / timeout / worker error)
    → Inform user, degrade to the current runtime's native subagent

Native subagent fails (as the default executor or as a fallback)
  → Inform user that independent review is unavailable
    → Initiator performs review directly (load checklist, review inline)
```

## Key Constraints

- **Initiator prepares context** — executor receives a self-contained prompt with all necessary information
- **Executor works independently** — no access to initiator's conversation history
- **Initiator owns verification** — never forward executor findings or accept its Verdict without independently checking the evidence
- **Verified issues are fixed automatically** — before the round limit, fix every verified P0-P2 issue and relevant validation failure, then dispatch another independent review
- **Validation gate** — run relevant project checks in every completed review round; record commands and results, and never claim a clean result when a required check failed
- **Seven-round limit** — run at most 7 completed review rounds; if round 7 still has verified P0-P2 issues or relevant validation failures, stop and report non-convergence
- **Review until clean** — stop only when a review cycle produces no new verified P0-P2 issues and validation passes or unavailable checks are explicitly documented, the seven-round limit is reached, or a fix is blocked
- **Escalate blocked fixes** — if a verified issue requires a product decision, external authority, or scope expansion, stop and ask the user
- **Every degradation notifies user** — state the reason and current execution method
- **Run-scoped resources** — use unique prompt paths and session identifiers for every run; never reuse or clean up another review's resources
- **Conversation-only output** — present review results in the conversation; do not generate or publish HTML artifacts
