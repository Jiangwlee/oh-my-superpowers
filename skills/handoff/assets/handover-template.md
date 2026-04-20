---
context_pct: 0
timestamp: ""
task_id: ""
pending: false
---

## Current Status
<!-- What phase is the task in right now? Include task name, current step, and
     any active blocker. Do NOT list history — only describe where you ARE. -->

## Completed Work
<!-- File name + one-line description per item. No process narrative.
     Skip anything already tested and merged. -->

## Remaining Tasks
<!-- Prioritized list. Each item must be concrete enough to start immediately:
     include function names, line numbers, port numbers, or exact next command. -->

## Key Decisions
<!-- Every decision made this session — explicit ones the user confirmed AND
     implicit choices Claude made on its own. Each entry must include WHY. -->

## Active Files
<!-- Only files created or modified this session. Note their current state:
     done / in-progress / needs attention. -->

## Resume
<!-- One line, fixed format:
     Read .handover.md and continue [exact next action] -->

## Compaction Rules
- Turn -1 (last): remove tool results; keep user + assistant in full
- Turn -2: remove tool results; keep user in full; summarize assistant ≤100 chars
- Turn -3: remove tool results; keep user in full; summarize assistant ≤50 chars
