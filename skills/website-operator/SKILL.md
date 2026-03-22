---
name: website-operator
description: |
  Use mcp-cli to control Chrome via chrome-devtools MCP for browser automation and debugging.
  Use when: (1) user asks to automate a website task — click, fill form, login, search;
  (2) user says "访问/打开/操作某网站", "搜索XXX", "在浏览器里做XXX", "open/navigate to URL";
  (3) user needs to inspect console errors, network requests, or run a Lighthouse audit;
  (4) user says "take screenshot" or "截图".
---

# Website Operator

Use `mcp-cli` to control Chrome browser through the chrome-devtools MCP server. This skill provides command reference for browser automation and debugging tasks.

## Iron Law

**NO `click`, `fill`, or `fill_form` WITHOUT calling `take_snapshot` FIRST to obtain valid uids.**

No exceptions. Always get a fresh snapshot before any element interaction.

---

## Prerequisite Check

Before executing any browser command:

1. **Verify mcp-cli is installed:**
   ```bash
   command -v mcp-cli || echo "NOT FOUND"
   ```
   If not found, stop and tell the user: "mcp-cli is not installed. Install it first."

2. **Verify chrome-devtools tools are accessible:**
   ```bash
   mcp-cli 2>/dev/null | grep -q navigate_page || echo "NOT FOUND"
   ```
   If not found, stop and tell the user to add the chrome-devtools MCP server to their configuration.

---

## Core Concepts

**Browser lifecycle**: Browser starts automatically on first tool call using a persistent Chrome profile. Configure via CLI args in MCP server configuration: `npx chrome-devtools-mcp@latest --help`.

**Page selection**: Tools operate on the currently selected page. Use `list_pages` to see available pages, then `select_page` to switch context.

**Element interaction**: Use `take_snapshot` to get page structure with element `uid`s. Each element has a unique `uid` for interaction. If an element isn't found, take a fresh snapshot — the page may have changed.

## Command Format

```bash
mcp-cli call chrome-devtools <tool> '<json-args>'
```

Both formats work: `<server> <tool>` or `<server>/<tool>`

```bash
mcp-cli call chrome-devtools navigate_page '{"url": "https://example.com"}'
mcp-cli call chrome-devtools/navigate_page '{"url": "https://example.com"}'
```

If you need full parameter details for a specific command, read `references/command-reference.md`.

---

## Workflow Patterns

### Before interacting with a page

1. **Navigate**: `navigate_page` or `new_page` to load the target URL
2. **Wait** (optional): `wait_for` to ensure content is loaded if you know what to look for
3. **Snapshot**: `take_snapshot` to understand page structure and get element uids
4. **Interact**: Use element `uid`s from snapshot for `click`, `fill`, etc.

**Done:** The requested user action has been performed and the resulting page state (via `take_snapshot` or `wait_for`) confirms the expected outcome.

### Efficient data retrieval

- Use `filePath` parameter for large outputs (screenshots, snapshots, traces)
- Use pagination (`pageIdx`, `pageSize`) and filtering (`types`) to minimize data
- Set `includeSnapshot: false` on input actions unless you need updated page state

### Tool selection

- **Automation/interaction**: `take_snapshot` (text-based, faster, better for automation)
- **Visual inspection**: `take_screenshot` (when visual state is needed)
- **Additional details**: `evaluate_script` for data not in accessibility tree

---

## Common Patterns

### Login Flow

```bash
# Navigate to login page
mcp-cli call chrome-devtools navigate_page '{"url": "https://example.com/login"}'

# Get page structure
mcp-cli call chrome-devtools take_snapshot

# Fill username and password (use uids from snapshot)
mcp-cli call chrome-devtools fill_form '{"elements": [{"uid": "1_5", "value": "user"}, {"uid": "1_6", "value": "pass"}]}'

# Click submit button
mcp-cli call chrome-devtools click '{"uid": "1_8", "includeSnapshot": true}'

# Wait for navigation
mcp-cli call chrome-devtools wait_for '{"text": ["Dashboard", "Welcome"]}'
```

### Extract Data from Dynamic Page

```bash
# Navigate and wait for content
mcp-cli call chrome-devtools navigate_page '{"url": "https://example.com/data"}'
mcp-cli call chrome-devtools wait_for '{"text": ["Results found"]}'

# Get snapshot to find element uids
mcp-cli call chrome-devtools take_snapshot

# Extract specific data using JavaScript
mcp-cli call chrome-devtools evaluate_script '{"function": "(el) => el.textContent", "args": ["1_15"]}'
```

### Debug Page Issues

```bash
# Check for console errors
mcp-cli call chrome-devtools list_console_messages '{"types": ["error", "issue"]}'

# Inspect network requests
mcp-cli call chrome-devtools list_network_requests '{"resourceTypes": ["xhr", "fetch"]}'

# Take screenshot for visual inspection
mcp-cli call chrome-devtools take_screenshot '{"filePath": "/tmp/debug.png"}'
```

---

## Failure Handling

- **Element uid not found**: Call `take_snapshot` again — the page may have changed. If uid still absent after retry, report to user with the snapshot excerpt.

- **navigate_page timeout**: Report the URL and timeout value to the user. Do NOT retry silently.

- **mcp-cli call returns error**: Report the exact error message verbatim. Do NOT guess a fix.

- **Browser fails to start**: Check prerequisite configuration and report the error to the user.

---

## Output Format

After completing a task, report:

1. **What action was performed** (e.g., "Clicked submit button uid=1_8")
2. **The resulting page state** (snapshot excerpt or wait_for confirmation text)
3. **Any extracted data** in plain text or markdown table

Example:
```
Action: Filled login form and clicked submit
Result: Page navigated to dashboard (confirmed by "Welcome" text appearing)
Extracted: User name = "John Doe", Email = "john@example.com"
```

---

## Guardrails

- **ALWAYS** call `take_snapshot` before any `click` or `fill` — **NEVER** guess a uid.
- **NEVER** call `upload_file` or submit a form containing sensitive data without confirming the target URL with the user first.
- Do NOT use system browser tools. **ONLY** use `mcp-cli call chrome-devtools` commands.
- If `mcp-cli` is unavailable, stop immediately. Do NOT fall back to any other browser tool.
- Do NOT perform destructive actions (form submission, file upload) without explicit user confirmation.

---

## Reference

- [Command Reference](references/command-reference.md) - Complete API command reference
- REQUIRED SUB-SKILL: Use mcp-cli for general mcp-cli invocation reference.
- [chrome-devtools-mcp GitHub](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [Chrome DevTools Documentation](https://developer.chrome.com/docs/devtools)
