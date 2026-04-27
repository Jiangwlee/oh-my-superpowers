---
name: code-review
description: >-
  Review local code changes: uncommitted work (staged/unstaged) or recent
  unpushed commits. Use when code needs quality review during local development.
  Do NOT use for PR review or branch comparison.
---

## Review Flow

Create a task for each step and complete them in order:

1. **Get diff** — determine review target and collect changes
2. **Assess diff size** — count lines to select checklist depth
3. **Gather context** — collect module descriptions, original requirements
4. **Load checklist** — read references based on diff size (see below)
5. **Load output format** — read `references/output-format.md`
6. **Assemble review prompt** — fill `assets/review-prompt-template.md` with `{context}`, `{diff}`, `{checklist}`, `{output_format}`
7. **Select executor** — choose execution method (see Executor Selection)
8. **Dispatch review** — send to executor
9. **Collect result** — parse structured output and Verdict
10. **Present to user** — show review result; user decides next action
11. **Fix (if requested)** — initiator executes fixes per user's decision
12. **Re-review (if requested)** — user may request another review cycle → go to step 1

## Review Target

| Scenario | Command |
|----------|---------|
| Uncommitted changes | `git diff` + `git diff --cached` |
| Recent N commits | `git diff HEAD~N..HEAD` (default N=1) |

## Diff Size & Checklist Loading

Count **diff output total lines** (including context lines) to determine size:

| Size | Lines | Action |
|------|-------|--------|
| Small | <50 | Read `references/review-checklist-core.md` |
| Medium | 50-300 | Read `references/review-checklist-core.md` + `references/review-checklist-extended.md` |
| Large | >300 | Same as Medium; review file-by-file in batches |

## Executor Selection

Default: **Sub agent**. Switch to tmux only when user explicitly requests.

### Sub agent (default)

Use Claude Code Agent tool to dispatch review in an isolated sub-context. Pass the assembled prompt as the agent's task.

### omp dispatch — custom prompt (codex / claude)

Write the assembled review prompt to a temp file, then dispatch:

```bash
omp dispatch run codex --prompt-file /tmp/code-review-prompt.md --timeout 600
# or
omp dispatch run claude --prompt-file /tmp/code-review-prompt.md --timeout 600
```

ANSI-clean output goes to stdout. Exit codes: `0` success, `124` timeout, `1` worker error.

### Live observation (optional)

Spawn first, then tail/wait separately if you want to watch progress:

```bash
SID=$(omp dispatch spawn codex --prompt-file /tmp/code-review-prompt.md --session-name code-review)
omp dispatch tail "$SID" --follow &
omp dispatch wait "$SID" --timeout 600
```

### codex built-in review (no custom prompt)

`codex exec review` is a Codex-native subcommand and not driven by a prompt file, so dispatch does not wrap it. Run it directly via tmux when needed:

```bash
# Uncommitted changes:
tmux new-session -d -s code-review-builtin \
  'codex exec review --uncommitted --ephemeral --dangerously-bypass-approvals-and-sandbox; exit'

# Specific commit:
tmux new-session -d -s code-review-builtin \
  'codex exec review --commit <SHA> --ephemeral --dangerously-bypass-approvals-and-sandbox; exit'
```

Cleanup: `tmux kill-session -t code-review-builtin 2>/dev/null; rm -f /tmp/code-review-prompt.md`

## Degradation Strategy

When an executor fails, degrade and inform the user:

```
omp dispatch fails (spawn error / timeout / worker error)
  → Inform user, degrade to sub agent
    → Sub agent fails
      → Inform user, initiator performs review directly (load checklist, review inline)
```

## Key Constraints

- **Initiator prepares context** — executor receives a self-contained prompt with all necessary information
- **Executor works independently** — no access to initiator's conversation history
- **User decides fixes** — never auto-fix; present results and let user choose
- **Every degradation notifies user** — state the reason and current execution method
