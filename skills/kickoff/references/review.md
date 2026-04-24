# Code Review Protocol

How to dispatch and consume code review for one task. Read this when you are about to enter the Review step of a wave loop.

---

## Hard Constraint

**Review MUST run in an isolated context** — never inline. Choose one of:

- **Sub Agent** (default) — dispatch the `code-reviewer` agent (`agents/code-reviewer.md`).
- **Tmux** — dispatch via external runtime (Claude / Codex / Pi) per `references/commands.md`. Use this only when the sub-agent mechanism is unavailable or the user explicitly asks for a different model.

Self-review (you reading your own diff and judging it) is forbidden. Bias kills the audit.

---

## Dispatch Prompt Shape

The reviewer receives THREE concatenated parts:

1. **Protocol body** — `agents/code-reviewer.md` content (system context that defines verdict format and severity).
2. **Task spec** — verbatim contents of `<story-dir>/tasks/task-NN.md` (Objective / Protocol / Acceptance Checklist).
3. **Diff context** — the git diff (and any new files) for this task. Use `git diff <base>..HEAD -- <file-scope>` scoped to `tasks[NN].files_modified`.

Optional: when relevant gotchas exist in `story-memory.md`, append a fourth part `## Known False Positives` listing entries from the file's same-named section. This stops the reviewer from re-flagging intentional patterns.

---

## Review Checklist (what the reviewer evaluates)

1. **Must-Haves** — every truth, artifact, key link in the spec's Acceptance Checklist verified.
2. **File Scope** — no edits outside the declared `files_modified` (deviations must be justified).
3. **Deviations** — diff vs Objective: any unapproved scope creep flagged.
4. **Tests** — verification layer matches `tasks[NN].test_layer` and covers all acceptance items.

---

## Severity Levels

| Level | Meaning |
|---|---|
| **CRITICAL** | Blocks acceptance; must fix before merge |
| **HIGH** | Significant risk or missing must-have |
| **MEDIUM** | Quality issue or partial deviation |
| **LOW** | Minor note for kickoff |

The reviewer's verdict is `PASS` only if zero CRITICAL or HIGH issues remain.

---

## Verdict and Loop

The reviewer outputs one of three verdicts:

| Verdict | Your action |
|---|---|
| `PASS` | Accept the task. Run `omp kickoff task update --reviewer <id> --status completed`. |
| `NEEDS_FIX` | Stay on the same task. Fix the CRITICAL/HIGH issues (inline). Re-run review. |
| `BLOCKED` | The reviewer cannot complete (missing context, contradiction, ambiguous spec). Read the reviewer's notes, resolve the blocker (clarify spec / add missing context / consult the user), then re-dispatch. |

You decide whether the reviewer's findings are valid before looping. The reviewer cannot modify code (hard constraint in `agents/code-reviewer.md`); all fixes happen in your context.

---

## Recording

On every review attempt:

```bash
omp kickoff task update --story-dir <root> --story <slug> --id <NN> \
  --reviewer "<agent-id-or-tmux-runtime>" \
  [--status completed]   # only when verdict is PASS and acceptance verified
```

Multiple review rounds on one task are normal — each `--reviewer` call overwrites the field with the latest reviewer id (keeps task.yaml lean; full review history lives in conversation transcripts).
