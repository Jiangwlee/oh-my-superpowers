# Review Prompt Template

Reviewer-prompt template. Copy and fill for each review dispatch.
Save as `/tmp/orchestrator-review-<NN>.md`.

The reviewer reads this file top-to-bottom; every input it needs must be here.
Rubric and output format are fixed — do NOT rewrite them per task.

---

```markdown
# Review: task-<NN>

## Spec

<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/tasks/task-NN.md

## Changes

- Commit: <hash>
- Branch: <branch>
- Files:
  - <path> — <what changed, one line>

## Diff

<!-- Paste full `git diff <base>..<head>` below, OR give the reviewer the exact
     command to run. Do not summarize — the reviewer needs the raw diff. -->

\`\`\`diff
<full diff>
\`\`\`

## Rubric

Evaluate in order. Each finding must cite `file:line` evidence from the diff or spec.

1. **Must-Haves** — every Truth observable? every Artifact present with declared content? every Key Link matching its regex pattern? (see spec § Acceptance Criteria)
2. **File Scope** — all changes strictly inside the spec's `File Scope`? anything outside is 🔴.
3. **Test Layer** — the first red test at the layer declared by `test_layer` in `tasks.yaml`? (see `references/task-decomposition-rules.md` Rule 1)
4. **Cross-Layer Wiring** — any new shared API (store action, hook return, context value, event) shipped without its first consumer in the same diff? (Rule 2)
5. **Sizing & Batching** — single task ≤ 5 files and vertical-sliced? fix-batch only if each fix ≤ 30 lines and ≤ 3 fixes share one verify cycle? (Rules 3, 5)
6. **Deviations** — any change beyond the spec unreported in the worker's completion report? any 🔴-level edit made without orchestrator approval?
7. **Code Quality** — matches existing style, no speculative abstraction, no dead code introduced by this diff.

## Output Format

\`\`\`markdown
## REVIEW COMPLETE

**Task:** task-<NN>
**Verdict:** PASS | NEEDS_FIX | BLOCKED

### Issues
<!-- Severity reuses the worker deviation palette.
     🔴 = must fix before merge; 🟠 = blocking but fixable in place;
     🟡 = should fix; 🟢 = nit. Omit section if no issues. -->
- [🔴/🟠/🟡/🟢] <finding> — evidence: <file:line> — suggested fix: <one line>

### Must-Haves Verified
- Truths: <which ones you confirmed observable>
- Artifacts: <which ones exist with expected content>
- Key Links: <which ones match the declared pattern>

### Notes for Orchestrator
<!-- Anything the orchestrator needs for second judgment:
     ambiguous findings, tradeoffs, proposed follow-up tasks. -->
- <note or "none">
\`\`\`
```

---

## Template Usage Notes

**Input fidelity**: paste the raw diff. A summarized diff hides the evidence the rubric requires.

**Rubric is fixed**: the seven checks map 1-to-1 against artifacts the orchestrator already owns (spec, `tasks.yaml`, `task-decomposition-rules.md`). Do not reorder, drop, or add rubric items per task — dispatch a different reviewer if you need a different rubric.

**Severity palette** mirrors the worker's deviation levels (🟢🟡🟠🔴) on purpose — the orchestrator can route findings through the same second-judgment flow regardless of source.

**Verdict contract**:
- `PASS` — no 🔴/🟠 issues; 🟡/🟢 optional to fix
- `NEEDS_FIX` — at least one 🟠 or 🔴; task returns to `executing`
- `BLOCKED` — reviewer cannot judge (missing diff, spec contradiction, external dependency); orchestrator must unblock before re-dispatching
