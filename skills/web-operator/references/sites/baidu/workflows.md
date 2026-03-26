# Baidu Search Workflows

This reference covers the `baidu.com` search workflow implemented in this repository.

## Scope

- Site: `baidu.com`
- Scripts: `scripts/sites/baidu/`
- Supported workflows: `search`

## Prerequisites

- A Chrome-family browser tab open to any page (the script will navigate it to Baidu).
- A Baidu account login is not required for basic search.
- Chrome remote debugging enabled at `chrome://inspect/#remote-debugging`.

## Workflow: search

### Script entrypoint

```bash
scripts/sites/baidu/search.sh <query> [limit] [target_prefix]
```

### Inputs

| Parameter | Required | Default | Notes |
|---|---|---|---|
| `query` | yes | — | Search query string |
| `limit` | no | 20 | Max results to return; hard cap 20 |
| `target_prefix` | no | auto | Unique `targetId` prefix from `cdp.mjs list` |

### Output schema

JSON array of search results, at most `limit` items.

```json
[
  {
    "title":   "Result title text",
    "snippet": "Short description extracted from the result card (≤ 280 chars)",
    "url":     "https://example.com/actual-destination"
  }
]
```

| Field | Type | Notes |
|---|---|---|
| `title` | string | `h3` text from the result card |
| `snippet` | string | Description text from various possible selectors; may be empty for some result types |
| `url` | string | Actual destination URL (Baidu redirect link) |

### SOP steps

1. Resolve the target tab using `baidu_find_target` (prefers baidu.com/s tabs, falls back to any page tab).
2. Navigate to `https://www.baidu.com/s?wd=<encoded_query>&tn=baidu` using `Page.navigate`.
3. Wait for `.result.c-container` (organic results containers) to appear in the DOM.
4. Run one `eval` to extract all result fields from `.result.c-container` and `.result-op.c-container` containers.
5. Filter results to only include those with valid titles and URLs.
6. Emit a JSON array; each item has `title`, `snippet`, and `url`.

### DOM Selectors

| Element | Selector(s) |
|---|---|
| Result container | `.result.c-container`, `.result-op.c-container` |
| Title | `h3` |
| URL | `h3 a` href attribute |
| Snippet (priority) | `.c-color.summary-gap`, `.c-color`, `[class*="summary"]`, `[class*="abstract"]`, `[class*="content"]` |

### Known limitations

- Video search results, image carousels, and other special result types may be skipped.
- Baidu's DOM class names change periodically; `snippet` extraction may degrade and return an empty string before this script is updated.
- Baidu uses redirect links (baidu.com/link), so the returned URL is the Baidu redirect URL, not the final destination.
- Some results may have minimal or no snippet text depending on the result type.
