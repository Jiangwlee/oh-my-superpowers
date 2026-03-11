---
name: openclaw-browser
description: >
  Use OpenClaw CLI to read pages, click elements, fill forms, wait for UI state,
  capture screenshots or PDFs, inspect console or network activity, and emulate
  browser environments. Use when the user asks to operate a website with OpenClaw,
  extract page content through OpenClaw browser, debug a web page, verify browser
  behavior, or simulate device, timezone, locale, geolocation, headers, or media settings.
---
# OpenClaw Browser

Purpose: Guide stable browser work with `openclaw browser` for reading, interaction,
         debugging, capture, and environment simulation.
Input:   User goal, URL, browser state, and local `openclaw` CLI access.
Output:  Verified page actions plus evidence such as snapshots, screenshots, PDFs,
         console logs, request logs, or extracted content.
Sections: Prerequisite Check | Workflow | Failure Handling | Output Format | Completion Criteria | Guardrails | References

<HARD-GATE>
NO REF ACTION WITHOUT SNAPSHOT FIRST.

NO `evaluate --fn` OR `wait --fn` WITHOUT A CLEAR NEED THAT SIMPLER WAIT MODES CANNOT COVER.

NO STALE REF REUSE AFTER DOM-CHANGING ACTIONS. RE-SNAPSHOT FIRST.
</HARD-GATE>

## Prerequisite Check

Stop and resolve before proceeding:

1. `command -v openclaw`
2. `openclaw browser status`
3. If the browser is not running, `openclaw browser start`
4. If isolation matters, choose a profile with `--browser-profile <name>`
5. If machine-readable output helps, prefer `--json`

## Workflow

### Step 1: Classify the task

Choose the narrowest matching flow:

- **Read**: open a page, inspect content, extract visible state
- **Interact**: click, type, fill, select, drag, upload, handle dialogs
- **Debug**: inspect console, requests, errors, response bodies, traces
- **Capture**: screenshot, PDF, highlighted evidence
- **Simulate**: device, viewport, timezone, locale, geolocation, media, headers, offline

### Step 2: Enter the right page context

Use the smallest command set that establishes page context:

- Open a new tab: `openclaw browser open <url>`
- Reuse the current tab: `openclaw browser navigate <url>`
- Inspect tabs: `openclaw browser tabs`
- Switch focus when needed: `openclaw browser focus <target-id>`

If the page is loading or changing, wait explicitly before acting.

### Step 3: Wait before guessing

Prefer these synchronization methods in order:

1. `openclaw browser wait --load <state>`
2. `openclaw browser wait --url <pattern>`
3. `openclaw browser wait --text <value>`
4. `openclaw browser wait '<selector>'`

Use `--fn` only when the state cannot be expressed with the commands above.

### Step 4: Snapshot before interaction

Create a fresh snapshot before any ref-based action:

```bash
openclaw browser snapshot
openclaw browser snapshot --efficient
openclaw browser snapshot --format aria --limit 200
```

Use the snapshot output to choose the exact `ref` for:

- `click`
- `hover`
- `type`
- `fill`
- `select`
- `drag`
- `scrollintoview`
- `highlight`

If the page changes after an action, go back to Step 3 and then re-run `snapshot`.

### Step 5: Execute the smallest safe action

Prefer built-in commands over JS evaluation:

- Text input: `type` or `fill`
- Pointer action: `click`, `hover`, `drag`
- Form controls: `select`, `upload`, `dialog`
- Inspection: `snapshot`, `console`, `requests`, `errors`, `responsebody`

Use `evaluate --fn` only for information that is not available from snapshot or other commands.

### Step 6: Verify with evidence

After completing the task, verify the result with one or more of:

- `wait`
- `snapshot`
- `screenshot`
- `pdf`
- `console`
- `requests`
- `errors`

For debugging or QA tasks, return at least one concrete artifact or log signal.

## Failure Handling

If a required command fails, do not keep clicking or guessing. Use the smallest recovery path:

1. If `openclaw` is missing or `openclaw browser status` fails, stop and report the browser is unavailable.
2. If the active page or tab is uncertain, run `openclaw browser tabs` and `openclaw browser focus <target-id>` before continuing.
3. If the page is still loading or re-rendering, re-run an explicit `wait` command before any next action.
4. If a ref-based action changed the DOM, re-run `snapshot` before any next ref-based action.
5. If the same action fails twice, stop retrying blindly and collect evidence with `console`, `requests`, `errors`, `snapshot`, or `screenshot`.

## Output Format

Use this default response shape unless the user asks for something else:

- `Goal:` what you attempted
- `Page:` URL or `target-id`
- `Result:` success or failure
- `Evidence:` exact artifact, command result, or log signal collected
- `Next step:` only when the workflow is blocked or needs user input

## Completion Criteria

The task is complete only when all relevant checks pass:

1. The browser is focused on the intended page or tab
2. The target action or extraction has been performed
3. Post-action state has been verified
4. If the DOM changed, actions used a fresh snapshot
5. If the user asked for debugging, capture, or verification, evidence was collected

## Guardrails

- ALWAYS use `snapshot` before any ref-based action.
- ALWAYS use `tabs` plus `focus` when the active tab is uncertain.
- ALWAYS re-run `snapshot` after navigation, major re-render, dialog resolution, or form submission.
- ALWAYS prefer `--json` when output may be consumed by another tool or script.
- NEVER use `evaluate --fn` or `wait --fn` when `snapshot` or ordinary `wait` modes can express the same check.
- Use `open` for side-by-side work and `navigate` for replacing the current page.
- Use explicit environment commands under `set` instead of vague narration.
- Do not invent `ref` values or selectors.
- Do not keep using a ref after navigation, major re-render, dialog resolution, or form submission.
- Do not turn this skill into a site-specific scraper; keep domain logic outside.

## References

- If you need exact command syntax by category, read `references/cli-cheatsheet.md`.
- If the task is multi-step and you need a reusable execution flow, read `references/workflow-patterns.md`.
- If refs are stale, tabs are ambiguous, or `--fn` seems necessary, read `references/safety-and-debugging.md`.
