# Web Operator CLI Reference

This file documents the commands exposed by `scripts/cdp.mjs`, the expected
inputs for each command, and the typical outputs. Read it when selecting the
right command or composing repeatable browser workflows. The public interface
is the CLI command list below and the target-prefix workflow.

## Preconditions

- Chrome-family browser with remote debugging enabled.
- Node.js 22+.
- A unique target prefix from `scripts/cdp.mjs list`.

## Primary workflow

1. Discover tabs:
   `scripts/cdp.mjs list`
2. Inspect structure:
   `scripts/cdp.mjs snap <target>`
3. Navigate if needed:
   `scripts/cdp.mjs nav <target> <url>`
4. Extract or interact:
   `scripts/cdp.mjs eval <target> <expr>`

## Command summary

- `list`
  Lists open page targets and excludes `chrome://` pages.
- `snap <target>`
  Returns a compact accessibility tree snapshot for structure discovery.
- `eval <target> <expr>`
  Evaluates one JavaScript expression in the page context and returns the value.
- `shot <target> [file]`
  Captures the viewport screenshot and prints DPR guidance.
- `html <target> [selector]`
  Returns the whole document HTML or one element's HTML.
- `nav <target> <url>`
  Navigates to an `http` or `https` URL and waits for load completion.
- `net <target>`
  Returns resource timing entries from the page.
- `dom <target>`
  Lists interactive elements as `[n] <tag> "name"` (per-snapshot numbers). Numbers map to `backendNodeId`, held per-tab for the next `click-index`.
- `click-index <target> <n>`
  Clicks element `[n]` from the most recent `dom` snapshot on that tab (resolved via `backendNodeId`, not CSS). Returns `not-found` if `n` is absent or `stale` if the page changed — re-run `dom`.
- `click <target> <selector>`
  Clicks an element resolved by CSS selector.
- `clickxy <target> <x> <y>`
  Clicks by CSS pixel coordinates.
- `type <target> <text>`
  Inserts text at the current focus using CDP input APIs.
- `scroll <target> <up|down> [amount]`
  Scrolls the page up or down by viewport heights (default: 3). Useful for triggering lazy-loading on infinite-scroll pages (x.com, Reddit, etc.).
- `loadall <target> <selector> [ms]`
  Repeatedly clicks a "load more" control until it disappears.
- `evalraw <target> <method> [json]`
  Sends a raw CDP command with optional JSON params.
- `open [url]`
  Opens a new tab and may trigger a new Chrome approval prompt.
- `close <target>`
  Closes a specific browser tab by target prefix.
- `stop [target]`
  Stops one tab daemon or all daemons.

## Notes

- Prefer `nav` to page-internal clicks for stable navigation.
- Prefer one extraction `eval` over several index-based DOM probes.
- `type` is safer than `eval` for cross-origin iframe text input.

## High-Level Site Commands

All browser actions route through `omp web-operator`. The underlying CDP engine is `scripts/cdp.mjs`.

### Read URL Content

- `omp web-operator read-url <url> [--limit N] [--comments N] [--json]`
  Read the main text content of any URL. Returns Markdown (when defuddle is available) or plain text.
  Four-tier strategy (HTTP-first + CDP fallback):
  1. **Known sites** (reddit, x, xueqiu, taoguba) → delegates to `open-post` for structured extraction
  2. **HTTP-first** → `defuddle parse <URL> --markdown` directly fetches and parses (~200ms, no browser needed). Covers ~80% of static content (blogs, docs, papers)
  3. **CDP + defuddle** → navigates worker tab to URL, extracts HTML, converts via defuddle. For JS-heavy/SPA pages where HTTP-first fails quality gate
  4. **CDP fallback** → extracts `innerText` from semantic elements (`article` > `main` > `body`), stripping nav/header/footer

  Options:
  - `--limit N` — truncate output to N bytes
  - `--comments N` — comment count for supported sites (default 20, 0 = all)
  - `--json` — output `{title, url, domain, description, content}` JSON. Content is still markdown. Useful for ingest pipelines needing structured metadata.

  Tier 3-4 use **persistent worker tabs** (created once, reused across calls) to avoid the ~15s CDP authorization cost per new tab. Worker tabs are automatically reset between reads (`Storage.clearDataForOrigin` + navigate to `about:blank`).

  ```bash
  # Read an article (usually hits tier 2, ~200ms)
  omp web-operator read-url "https://www.paulgraham.com/writes.html"

  # Read with character limit
  omp web-operator read-url "https://arxiv.org/html/2603.23013v1" --limit 15000

  # JSON output with metadata (for pipelines)
  omp web-operator read-url "https://blog.samaltman.com/..." --json
  ```

### Single-Platform Search

- `omp web-operator search <site> "<query>" [limit] [--target TARGET]`
  Search one supported site and return a JSON array of results.
  Supported sites: `baidu`, `duckduckgo`, `github`, `google`, `reddit`, `taoguba`, `weixin-sogou`, `x`, `xueqiu`.

  The `search` command uses positional arguments. Do not use `--platform`, `--query`, or `--limit` with `search`.

  Examples:
  ```bash
  omp web-operator search google "AI agents" 10
  omp web-operator search baidu "AI 智能体" 5
  omp web-operator search reddit "Claude Code memory" 5
  omp web-operator search x "Claude Code" 5 --target 0
  ```

  Anti-examples:
  ```bash
  # BAD: these options do not exist for search
  omp web-operator search --platform google --query "AI agents"
  omp web-operator search google --query "AI agents" --limit 10
  ```

### Multi-Platform Parallel Search

- `omp web-operator search-multi --<platform> "<query>" [...] [--limit N]`
  Run searches on multiple platforms in parallel and return merged results.
  Supported platforms: `baidu`, `google`, `github`, `reddit`, `weixin-sogou`, `x`, `xueqiu`, `taoguba`, `duckduckgo`.
  Max 5 concurrent searches (CDP connection limit).

  Example:
  ```bash
  omp web-operator search-multi --google "AI agents" --baidu "AI 智能体" --reddit "AI agents" --limit 5
  ```

  Output format:
  ```json
  [
    { "platform": "google", "query": "AI agents", "results": [{ "title": "...", "snippet": "...", "url": "..." }] },
    { "platform": "baidu", "query": "AI 智能体", "results": [{ "title": "...", "snippet": "...", "url": "..." }] }
  ]
  ```

### Baidu

- `omp web-operator search baidu <query> [limit] [target]`
  Search `baidu.com` and extract up to 20 organic result summaries (title, snippet, url).

### GitHub

- `omp web-operator search github <query> [limit]`
  Search GitHub repos, issues, and discussions via `gh` CLI. Returns up to 60 results with type, title, summary, url, stars/labels. No browser needed.

### Google

- `omp web-operator search google <query> [limit] [target]`
  Search `google.com` and extract up to 20 organic result summaries (title, snippet, url).

### Reddit

- `omp web-operator search reddit <query> [limit] [target]`
  Search `reddit.com` and extract up to 10 result summaries.
- `omp web-operator open-post reddit <url> [comment_limit] [target]`
  Open one Reddit post URL and extract the main post plus top visible comments.

### Taoguba

- `omp web-operator taoguba login [--target TARGET] [--timeout SECONDS]`
  Sign in using account credentials already stored in Chrome.
- `omp web-operator taoguba jinghua [hours] [limit] [target]`
  Extract Taoguba `jinghua` posts from the last 24 hours by default.
- `omp web-operator taoguba following [hours] [limit] [target]`
  Extract followed-content updates from the last 12 hours by default.
- `omp web-operator open-post taoguba <url> [target]`
  Open one Taoguba post and extract the main post body.

### ChatGPT Images

- `omp web-operator generate-image chatgpt <prompt> [--out PATH] [--target TARGET] [--timeout SEC] [--overwrite] [--json]`
  Generate an image on `chatgpt.com/images` and save it locally. Requires a
  signed-in ChatGPT Chrome session. Uses the authenticated page context for the
  final image download because direct shell downloads of the rendered image URL
  may return `403 Forbidden`.

  Example:
  ```bash
  omp web-operator generate-image chatgpt "a blue circle on a white background" --out ./circle.png --json
  ```

### WPS 365 (365.kdocs.cn)

- Prefer `omp web-operator kdocs ask-ai <question> [target]` for document Q&A, summaries, fuzzy lookup, and multi-doc questions.
- `omp web-operator kdocs search <query> [limit] [target]`
  Search WPS 365 documents; returns snippets and version ranking.
- `omp web-operator kdocs open-doc <file_key> [main_target]`
  Open a document by file key; returns outline and first-page text.
- `omp web-operator kdocs find-in-doc <keyword> [target]`
  Search for a keyword in the open document; returns match count and context.
- `omp web-operator kdocs ask-ai <question> [target]`
  Ask WPS AI Docs Chat on the main page; returns answer text and referenced docs.
- `omp web-operator kdocs close-doc [target]`
  Close the document tab, keeping the main 365.kdocs.cn/latest tab alive.

### X

- `omp web-operator search x <query> [limit] [target]`
  Search `x.com` and extract up to 10 result summaries.
- `omp web-operator open-post x <url> [target]`
  Open one `x.com` post URL and extract the current visible post text.
- `omp web-operator x for-you [limit] [target]`
  Read the X.com For You recommendation feed.

### Weixin-Sogou

- `omp web-operator search weixin-sogou <query> [limit] [target]`
  Search `weixin.sogou.com` (搜狗微信搜索) and extract article metadata (title, summary, account, time, link). Note: Only search is supported; full article content requires WeChat environment.

### Xueqiu

- `omp web-operator search xueqiu <query> [limit] [target]`
  Search `xueqiu.com` and extract up to 10 discussion results.
- `omp web-operator open-post xueqiu <url> [comment_limit] [target]`
  Open one `xueqiu.com` post URL and extract the main article plus visible comments.
- `omp web-operator xueqiu hot [limit] [target]`
  Extract the current visible "热门" home timeline post list.
- `omp web-operator xueqiu stock-info <symbol_or_url> [limit] [target]`
  Open one stock page and extract the latest visible announcements and discussions.

## Script entrypoint

- Implementation: [../../scripts/cdp.mjs](../../scripts/cdp.mjs)
