---
name: bb-browser
description: >
  Use bb-browser to access websites with real Chrome login state (cookies), without
  API keys or simulated login. Use when: (1) user wants to browse authenticated pages
  or extract content from sites that require login; (2) user wants to run bb-browser
  site commands (e.g., zhihu/hot, bilibili/search); (3) user wants to develop a new
  bb-browser site adapter for a specific website; (4) user says "用真实浏览器", "用 bb-browser",
  "开发 adapter", "逆向 API", "抓包". Do NOT use for headless browser tasks — use
  openclaw-browser instead.
---
# bb-browser

Purpose: Guide authenticated web access and adapter development via bb-browser CLI,
         which tunnels through your real Chrome instance using its live login state.
Input:   User goal, target website or command, and access to local `bb-browser` CLI.
Output:  Fetched content, structured JSON results, or a working `.js` adapter file.
Sections: Workflow | Adapter Development | Failure Handling | Output Format | Completion Criteria | Guardrails | References

<HARD-GATE>
NO ADAPTER WRITE WITHOUT VERIFYING THE API VIA `bb-browser eval` FIRST.

NO BLIND RETRY — COLLECT EVIDENCE BEFORE TRYING AGAIN.
</HARD-GATE>

## Workflow A: Using bb-browser Commands

Use this when the user wants to browse, extract, or interact with web pages.

### Step 1: Identify the right command

```bash
# List all available site adapters
bb-browser site list

# Update community adapters (104+ sites)
bb-browser site update

# Open a URL in Chrome
bb-browser open https://example.com

# Take a snapshot of the current page
bb-browser snapshot
```

### Step 2: Run site adapters

```bash
# Pattern: bb-browser site <platform>/<command> [args]

# No-login examples
bb-browser site v2ex/hot
bb-browser site wikipedia/summary "Python"

# Login-required examples (user must be logged in via Chrome)
bb-browser site zhihu/hot
bb-browser site bilibili/search "关键词"

# With JSON output
bb-browser site zhihu/hot --json
```

### Step 3: Use network inspection tools

```bash
# Get current tab ID
bb-browser snapshot | head -3

# Clear old requests
bb-browser network clear --tab <tabId>

# Refresh page to trigger requests
bb-browser refresh --tab <tabId>

# Capture API requests with body
bb-browser network requests --filter "api" --with-body --json --tab <tabId>
```

### Step 4: Evaluate JavaScript in page context

```bash
# Tier 1: direct fetch with cookies
bb-browser eval "fetch('/api/data', {credentials:'include'}).then(r=>r.json()).then(d=>JSON.stringify(d,null,2))"

# Tier 2: with CSRF token
bb-browser eval "
  const token = document.cookie.split(';').find(c=>c.trim().startsWith('ct0='))?.split('=')[1];
  fetch('/api/data', {headers:{'X-Csrf-Token':token},credentials:'include'})
    .then(r=>r.json()).then(d=>JSON.stringify(d,null,2))
"
```

## Workflow B: Developing a New Site Adapter

Use when the user wants to add bb-browser support for a new website. Read `references/adapter-development.md` for the full guide.

### Quick Overview

**Three tiers by authentication complexity:**

| Tier | Auth | Examples | Time |
|------|------|----------|------|
| 1 | Cookie `credentials:'include'` | Reddit, GitHub, 知乎, B站 | ~1 min |
| 2 | Bearer Token + CSRF header | Twitter/X, 微博 | ~3 min |
| 3 | Webpack/Pinia injection | 小红书, Twitter search | ~10 min |

### Four-step process

1. **Reverse the API** — Use `bb-browser network requests` to capture calls
2. **Verify feasibility** — Use `bb-browser eval` to test the fetch
3. **Write the adapter** — Create `~/.bb-browser/sites/<platform>/<command>.js`
4. **Test it** — Run `bb-browser site <platform>/<command> "test"`

Adapter save path:
```
~/.bb-browser/sites/<platform>/<command>.js   ← private (takes priority)
~/.bb-browser/bb-sites/<platform>/<command>.js ← community (read-only)
```

For AI-assisted adapter development, run:
```bash
bb-browser guide    # outputs full tutorial to feed to AI
```

## Failure Handling

1. **Daemon not running** (`curl localhost:19824/sse` fails) — ask user to run `bb-browser daemon` and ensure Chrome extension is connected.
2. **Extension not connected** (daemon shows "Waiting for extension connection") — ask user to open Chrome, go to `chrome://extensions/`, and reload the bb-browser extension.
3. **401/403 from `bb-browser eval`** — the site requires more headers; escalate to a higher Tier adapter.
4. **`bb-browser site` returns login error** — ask user to log in to the target site in their Chrome browser first.
5. **Same command fails twice** — stop retrying; run `bb-browser network requests` or `bb-browser eval` to collect evidence before diagnosing.
6. **`Daemon 已在运行` error on start** — kill the manual daemon first: `pkill -f "bb-browser daemon"`, then retry.

## Output Format

Default response shape:

- `Goal:` what was attempted
- `Command:` exact `bb-browser` command(s) run
- `Result:` success or failure with data summary
- `Evidence:` JSON output, snapshot excerpt, or error message
- `Next step:` only when blocked or needing user input

## Completion Criteria

The task is complete only when:

1. Target command or site adapter ran without error
2. Output data was collected and summarized
3. For new adapters: adapter file saved, tested with `bb-browser site <platform>/<command>`, and output verified

## Guardrails

- ALWAYS verify with `bb-browser eval` before writing an adapter.
- NEVER write an adapter without testing the API call first.
- NEVER keep retrying a failing command — collect evidence first.
- NEVER store session tokens or CSRF values in adapter files as hardcoded strings; always extract them dynamically from cookies or the DOM.
- Do not use `bb-browser` for sites that don't require authentication when simpler tools suffice.

## References

- For full adapter development guide with templates: read `references/adapter-development.md`
- For CLI command reference: read `references/cli-cheatsheet.md`
