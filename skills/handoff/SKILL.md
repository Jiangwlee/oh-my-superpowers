---
name: handoff
description: >-
  Use before running /compact to preserve session context. Generates a
  structured .handover.md and a ready-to-use /compact instruction so the
  next session resumes without information loss. Trigger when context
  reaches ~65-70%. Do NOT use for general summaries or task documentation.
---

# Handoff

Generates a structured handover document before compaction so the next session
resumes with full context. Three hooks automate the rest.

## Pipeline

**Step 1 — Load template**
Read `assets/handover-template.md`.

**Step 2 — Fill handover**
Fill every section from the current conversation. Follow each section's
guardrail. For Key Decisions: include all decisions made this session,
including implicit choices Claude made without explicit user confirmation.

**Step 3 — Write file**
Write to `.handover.md` in the project root (overwrite if exists).
`pending` in frontmatter must be `false` at write time.

**Step 4 — Output action sequence**
Extract 3–5 keywords from Key Decisions + Remaining Tasks to form a
focused `/compact` instruction. Show:

```
━━━ Handover saved → .handover.md ━━━

① /compact Focus on [task]. Preserve: [decision], [decision], [next task].

② (PostCompact hook will auto-restore on your next message)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
