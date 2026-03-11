# OpenClaw Browser Workflow Patterns

Purpose: Capture reusable multi-step flows for common OpenClaw browser tasks.
Input:   A user request that requires page reading, interaction, debugging, or environment checks.
Output:  Short procedural patterns that can be followed directly in the current session.
Sections: Read A Page | Interact With A Form | Handle SPA Updates | Gather Evidence | Simulate Environment

## Read A Page

Use this when the goal is to inspect visible content or page state.

1. `openclaw browser open <url>` or `navigate <url>`
2. `openclaw browser wait --load domcontentloaded`
3. `openclaw browser wait --text '<anchor text>'` if the page is dynamic
4. `openclaw browser snapshot --efficient`
5. If needed, `evaluate --fn '() => document.title'`
6. Return the extracted state and, if useful, a screenshot that proves the page reached the expected state

## Interact With A Form

Use this when the task is to click, type, select, submit, or upload.

1. Open or focus the correct tab
2. Wait for the form container or load state
3. `snapshot`
4. Use `fill` for multiple fields, `type` for one field, `select` for dropdowns
5. Use `click` or `type --submit` to submit
6. Wait for success text, redirect URL, or load state
7. Re-snapshot before any follow-up interaction and report the exact success signal you observed

## Handle SPA Updates

Use this when the page re-renders without full navigation.

1. Wait for a stable signal such as URL, text, or selector
2. Snapshot again before interacting with updated content
3. Avoid reusing refs from the pre-update snapshot
4. If state is unclear, inspect `console` or `requests`
5. Only use `wait --fn` when regular wait modes cannot describe readiness

## Gather Evidence

Use this when the user asks to debug, verify, or document what happened.

1. Capture the relevant state with `snapshot`
2. Capture a `screenshot` or `pdf` if visual proof matters
3. Read `console --level error`
4. Read `requests` or `responsebody` if network behavior matters
5. Read `errors` for page-level failures
6. Return exact artifacts or exact log signals, not just conclusions

## Simulate Environment

Use this when the user asks to test the page under a device or browser setting.

1. Apply the setting before opening the page when possible
2. Use `set device` or `resize` / `set viewport` for screen shape
3. Use `set timezone`, `set locale`, `set geo`, `set headers`, `set media`, `set offline` as needed
4. Open or reload the page
5. Wait for the page to settle
6. Verify the effect with screenshot, visible text, or requests

## Pattern Choice

- Choose **Read A Page** for passive inspection.
- Choose **Interact With A Form** for direct UI manipulation.
- Choose **Handle SPA Updates** whenever the DOM changes after clicks or filters.
- Choose **Gather Evidence** for debugging, QA, and incident reproduction.
- Choose **Simulate Environment** for device or location-dependent behavior.
