---
# bb-browser Adapter Development Guide
# Purpose: Step-by-step guide to building a new site adapter (.js file)
# Audience: AI agent developing adapters on behalf of the user
# Sections: Tier Classification | Step 1 Reverse | Step 2 Verify | Step 3 Write | Step 4 Test | Contributing
---

# bb-browser Adapter Development Guide

Adapters are JS files executed inside your Chrome extension. They have access to the
page's cookies, DOM, and can call `fetch` with full authentication context.

## Tier Classification

| Tier | Auth mechanism | Examples | Effort |
|------|----------------|----------|--------|
| 1 | `fetch` + `credentials:'include'` (cookie) | Reddit, GitHub, 知乎, B站 | ~1 min |
| 2 | Bearer token + CSRF header from cookie | Twitter/X, 微博 | ~3 min |
| 3 | Webpack module / Pinia store injection | 小红书, Twitter search | ~10 min |

Start with Tier 1 and escalate only if you get 401/403.

## Step 1: Reverse the API

Open the target site in Chrome, then capture network traffic:

```bash
# Get tab ID
bb-browser snapshot | head -3

# Clear previous requests
bb-browser network clear --tab <tabId>

# Trigger the page action (e.g., load feed, perform search)
bb-browser refresh --tab <tabId>

# Capture all API calls with request bodies
bb-browser network requests --filter "api" --with-body --json --tab <tabId>
```

Focus on:
- API endpoint URL and HTTP method
- Request headers (especially `Authorization`, `X-Csrf-Token`, `X-Client-Id`)
- Request body structure
- Response data structure (what fields contain useful content)

## Step 2: Verify Feasibility

Test in the extension's page context before writing any file:

### Tier 1 test
```bash
bb-browser eval "
  fetch('/api/endpoint', {credentials:'include'})
    .then(r => r.json())
    .then(d => JSON.stringify(d, null, 2))
"
```

### Tier 2 test
```bash
bb-browser eval "
  const ct0 = document.cookie.split(';')
    .find(c => c.trim().startsWith('ct0='))?.split('=')[1];
  fetch('/api/endpoint', {
    headers: {'X-Csrf-Token': ct0, 'Authorization': 'Bearer <token>'},
    credentials: 'include'
  }).then(r => r.json()).then(d => JSON.stringify(d, null, 2))
"
```

**Interpret results:**
- Returns data → tier is viable, proceed to Step 3
- 401/403 → more headers needed, try next tier
- Network error → check if you must run from the target domain tab

## Step 3: Write the Adapter

Create the file at: `~/.bb-browser/sites/<platform>/<command>.js`

### Tier 1 Template (Cookie fetch)

```javascript
/* @meta
{
  "name": "platform/command",
  "description": "功能描述（英文或中文均可）",
  "domain": "www.example.com",
  "args": {
    "query": {"required": true,  "description": "搜索词"},
    "count": {"required": false, "description": "返回数量，默认 20"}
  },
  "capabilities": ["network"],
  "readOnly": true,
  "example": "bb-browser site platform/command \"关键词\""
}
*/

async function(args) {
  if (!args.query) return {error: 'Missing argument: query'};

  const count = parseInt(args.count) || 20;
  const resp = await fetch(
    '/api/search?q=' + encodeURIComponent(args.query) + '&limit=' + count,
    {credentials: 'include'}
  );
  if (!resp.ok) return {
    error: 'HTTP ' + resp.status,
    hint: '请先登录 www.example.com'
  };

  const d = await resp.json();
  return {
    count: d.items.length,
    items: d.items.map(item => ({
      id:    item.id,
      title: item.title,
      url:   'https://www.example.com/item/' + item.id
    }))
  };
}
```

### Tier 2 Template (Bearer + CSRF)

```javascript
/* @meta
{
  "name": "platform/command",
  "description": "功能描述",
  "domain": "www.example.com",
  "args": {
    "query": {"required": true, "description": "搜索词"}
  },
  "capabilities": ["network"],
  "readOnly": true,
  "example": "bb-browser site platform/command \"关键词\""
}
*/

async function(args) {
  if (!args.query) return {error: 'Missing argument: query'};

  // Extract CSRF token dynamically from cookie — never hardcode
  const csrfToken = document.cookie.split(';')
    .map(c => c.trim())
    .find(c => c.startsWith('csrf_token='))
    ?.split('=')[1];
  if (!csrfToken) return {error: 'No CSRF token found', hint: '请先登录'};

  const resp = await fetch('/api/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Csrf-Token': csrfToken
    },
    body: JSON.stringify({query: args.query}),
    credentials: 'include'
  });
  if (!resp.ok) return {error: 'HTTP ' + resp.status};

  return await resp.json();
}
```

### @meta Field Reference

| Field | Required | Notes |
|-------|----------|-------|
| `name` | ✅ | `platform/command` format |
| `description` | ✅ | Shown in `bb-browser site list` |
| `domain` | ✅ | Domain tab where adapter must run |
| `args` | ✅ | Argument definitions with `required` flag |
| `capabilities` | ✅ | Usually `["network"]` |
| `readOnly` | ✅ | `true` for read-only, `false` for write ops |
| `example` | recommended | Shown in `bb-browser site info` |

## Step 4: Test

```bash
# Basic run
bb-browser site platform/command "测试关键词"

# Full JSON output
bb-browser site platform/command "测试关键词" --json

# View adapter metadata
bb-browser site info platform/command
```

Check:
- Returns expected fields
- `count` matches actual item count
- URLs are well-formed
- Login-required hint appears when not logged in

## Community Contribution (Optional)

```bash
# Fork the community repo
bb-browser site github/fork epiral/bb-sites

# Clone, branch, copy
git clone https://github.com/<YOU>/bb-sites && cd bb-sites
git checkout -b feat-<platform>
cp ~/.bb-browser/sites/<platform>/<command>.js <platform>/<command>.js

# Commit and push
git add . && git commit -m "feat(<platform>): add <command> adapter"
git push -u origin feat-<platform>

# Create PR
gh pr create --repo epiral/bb-sites --title "feat(<platform>): add <command>"
```

## Reference: Community Adapters

Browse existing adapters for real-world examples:

```bash
# Tier 1 reference
cat ~/.bb-browser/bb-sites/zhihu/hot.js

# Tier 2 reference
cat ~/.bb-browser/bb-sites/twitter/search.js

# Complex args reference
cat ~/.bb-browser/bb-sites/bilibili/search.js

# List all available
ls ~/.bb-browser/bb-sites/
```
