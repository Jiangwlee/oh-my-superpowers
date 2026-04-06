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

### tmux codex — custom prompt

```bash
# 1. Write prompt to temp file
# 2. Launch tmux session
tmux new-session -d -s code-review \
  'cat /tmp/code-review-prompt.md | codex exec --ephemeral --dangerously-bypass-approvals-and-sandbox'
```

### tmux codex ��� built-in review

```bash
# For uncommitted changes:
tmux new-session -d -s code-review \
  'codex exec review --uncommitted --ephemeral --dangerously-bypass-approvals-and-sandbox'

# For specific commit:
tmux new-session -d -s code-review \
  'codex exec review --commit <SHA> --ephemeral --dangerously-bypass-approvals-and-sandbox'
```

### tmux claude

```bash
tmux new-session -d -s code-review \
  'cat /tmp/code-review-prompt.md | claude -p --no-session-persistence --dangerously-skip-permissions'
```

### tmux session management

- **Poll status** every 30s: `tmux has-session -t code-review 2>/dev/null && echo running || echo done`
- **Capture output**: redirect to file for large reviews (preferred over `tmux capture-pane` which truncates at ~2000 lines):
  ```bash
  tmux new-session -d -s code-review \
    'cat /tmp/code-review-prompt.md | claude -p --no-session-persistence --dangerously-skip-permissions > /tmp/code-review-result.md 2>&1'
  ```
- **Cleanup**: `tmux kill-session -t code-review 2>/dev/null; rm -f /tmp/code-review-prompt.md`

## Degradation Strategy

When an executor fails, degrade and inform the user:

```
tmux fails (launch error / timeout / crash)
  → Inform user, degrade to sub agent
    → Sub agent fails
      → Inform user, initiator performs review directly (load checklist, review inline)
```

## Key Constraints

- **Initiator prepares context** — executor receives a self-contained prompt with all necessary information
- **Executor works independently** — no access to initiator's conversation history
- **User decides fixes** — never auto-fix; present results and let user choose
- **Every degradation notifies user** — state the reason and current execution method
