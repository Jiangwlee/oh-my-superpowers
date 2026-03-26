# Google Search Workflows

This reference covers the `google.com` search workflow implemented in this repository.

## Scope

- Site: `google.com`
- Scripts: `scripts/sites/google/`
- Supported workflows: `search`

## Prerequisites

- A Chrome-family browser tab open to any page (the script will navigate it to Google).
- A Google account login is not required for basic search.
- Chrome remote debugging enabled at `chrome://inspect/#remote-debugging`.

## Workflow: search

### Script entrypoint

```bash
scripts/sites/google/search.sh <query> [limit] [target_prefix]
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
| `snippet` | string | Description text from `.VwiC3b` or similar selector; may be empty for some result types |
| `url` | string | Actual destination URL, not a Google redirect |

### SOP steps

1. Resolve the target tab using `google_find_target` (prefers google.com tabs, falls back to any page tab).
2. Navigate to `https://www.google.com/search?q=<encoded_query>&num=20` using `Page.navigate`.
3. Wait for URL to contain `google.com/search`.
4. Wait for `#rso` (organic results section) to appear in the DOM.
5. Run one `eval` to extract all result fields from `#rso .g` containers.
6. Emit a JSON array; each item has `title`, `snippet`, and `url`.

### Known limitations

- Featured snippets, knowledge panels, and news carousels at the top of the results page are skipped; only standard `#rso .g` result cards are extracted.
- Google may serve a CAPTCHA or consent gate if the IP triggers rate limiting. The script will time out waiting for `#rso` in that case.
- Result cards that lack an `h3` element (ads, map packs) are silently skipped.
- Google's DOM class names change periodically; `snippet` extraction may degrade and return an empty string before this script is updated.
