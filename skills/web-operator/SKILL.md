---
name: web-operator
description: Use Web Operator to inspect, navigate, extract, and run site-specific SOP workflows in a local Chrome-family browser. Use when the user needs a workflow on a live Chrome tab, a bundled site workflow script should run, or a page already open in Chrome should be inspected or debugged.
---

# Web Operator

Use this skill when you need deterministic access to a local Chrome-family browser tab through the DevTools Protocol and when a site-specific SOP in this repository should run on top of that browser connection.

This skill is no longer just a thin browser utility. It is the core browser layer for a growing SOP skill platform.

## Skill Model

Treat this skill as three layers:

- `core`
  Chrome connection, tab targeting, navigation, extraction primitives, and SOP development guidance.
- `core/common.sh`
  Shared shell helpers for all site workflows: tab lifecycle management (`find_or_create_tab`), URL encoding, and CDP wrappers.
- `sites`
  Repeatable workflows for specific websites such as `reddit.com`, `tgb.cn`, and `x.com`. Each site uses `core/common.sh` for tab management.

This repository uses a `core + sites + tests` layout.

## Quick Start

- Confirm Chrome remote debugging is enabled at `chrome://inspect/#remote-debugging`.
- Use `omp-web-operator cdp list` to identify the target tab prefix.
- Prefer stable URL navigation when a workflow can avoid brittle click paths.
- Load the relevant core or site reference before running a non-trivial workflow.

## When To Load References

Load core references for shared browser behavior:

- [references/core/index.md](references/core/index.md)
  Command selection and common workflow guidance.
- [references/core/cli-reference.md](references/core/cli-reference.md)
  CLI semantics and examples.
- [references/core/troubleshooting.md](references/core/troubleshooting.md)
  Connection failures, stale `DevToolsActivePort`, and approval-prompt issues.
- [references/core/sop-development.md](references/core/sop-development.md)
  The SOP development process used in this repository.
- [references/core/common-library.md](references/core/common-library.md)
  API reference for `scripts/core/common.sh`: tab lifecycle, URL encoding, and CDP wrappers. Load when writing or debugging a site script.

Load site references for website-specific workflows:

- [references/sites/baidu/workflows.md](references/sites/baidu/workflows.md)
  `baidu.com` search workflow: returns top organic results with title, snippet, and URL.
- [references/sites/google/workflows.md](references/sites/google/workflows.md)
  `google.com` search workflow: returns top organic results with title, snippet, and URL.
- [references/sites/weixin-sogou/workflows.md](references/sites/weixin-sogou/workflows.md)
  `weixin.sogou.com` WeChat article search: returns title, summary, account, and link (search only, no full content).
- [references/sites/kdocs/workflows.md](references/sites/kdocs/workflows.md)
  `365.kdocs.cn` / WPS 365 document search, open, find-in-doc, AI QA, and close workflows.
- [references/sites/reddit/workflows.md](references/sites/reddit/workflows.md)
  `reddit.com` search and post-plus-comments workflows.
- [references/sites/taoguba/workflows.md](references/sites/taoguba/workflows.md)
  `tgb.cn` / Taoguba workflow guidance.
- [references/sites/x/workflows.md](references/sites/x/workflows.md)
  `x.com` search and post-extraction workflows.
- [references/sites/xueqiu/workflows.md](references/sites/xueqiu/workflows.md)
  `xueqiu.com` search, hot-post list, and post-plus-comments workflows.

## Core Rules

- The `<target>` argument is a unique `targetId` prefix from `omp-web-operator cdp list`.
- Prefer `nav` over click-driven navigation when a stable URL is known.
- Prefer one `eval` that collects all needed data over multiple DOM-indexed `eval` calls.
- Use `type` instead of `eval` for text entry in cross-origin iframes.
- Expect one Chrome "Allow debugging" prompt per tab daemon on first access.
- Keep browser primitives in the core layer. Do not bury general CDP logic inside a site-specific workflow unless the behavior is truly site-bound.

## ✅ Automatic Tab Management

Each site workflow automatically manages its own Chrome tab:

1. **Find existing tab**: Each script looks for an existing tab of its domain (e.g., `baidu.com`)
2. **Create if missing**: If no matching tab exists, the script automatically creates a new one
3. **Isolation**: Different sites never share the same tab, preventing navigation conflicts

This means you **no longer need to specify target tabs manually** for normal usage:

```bash
# ✓ Automatic tab management - each site uses its own tab
omp-web-operator search baidu "query" 5        # Uses/creates baidu tab
omp-web-operator search google "query" 5       # Uses/creates google tab
omp-web-operator search weixin-sogou "query" 5 # Uses/creates sogou tab
```

### Shared Core Library

All site scripts source the shared helpers from `scripts/core/common.sh`:

- `find_or_create_tab <homepage_url> [domain]` - Find existing tab or create new one
- `create_tab <homepage_url>` - Create and navigate to a new tab
- `url_encode <string>` - URL encode strings
- `cdp_eval <target> <expression>` - Evaluate JavaScript in tab

Site-specific `common.sh` files (e.g., `scripts/sites/baidu/common.sh`) are now thin wrappers that call these shared functions with domain-specific parameters.

## ⚠️ Concurrent Execution Guidelines

**Same site**: Never run multiple scripts for the same site in parallel on the same tab. They will race for navigation.

**Different sites**: Safe to run in parallel because each uses its own dedicated tab:

```bash
# ✓ SAFE: Different sites in parallel
omp-web-operator search baidu "query" 5 &
omp-web-operator search google "query" 5 &
omp-web-operator search weixin-sogou "query" 5 &
wait
```

**CDP connection limit**: While different sites are isolated by tab, they still share Chrome's DevTools WebSocket server. Avoid launching too many scripts simultaneously (more than ~5) to prevent connection timeouts.

## Main Entrypoint

All browser actions route through `omp-web-operator`. The underlying CDP engine is `scripts/cdp.mjs`.

## Available Commands

### Baidu

- `omp-web-operator search baidu <query> [limit] [target]`
  Search `baidu.com` and extract up to 20 organic result summaries (title, snippet, url).

### Google

- `omp-web-operator search google <query> [limit] [target]`
  Search `google.com` and extract up to 20 organic result summaries (title, snippet, url).

### Reddit

- `omp-web-operator search reddit <query> [limit] [target]`
  Search `reddit.com` and extract up to 10 result summaries.
- `omp-web-operator open-post reddit <url> [comment_limit] [target]`
  Open one Reddit post URL and extract the main post plus top visible comments.

### Taoguba

- `omp-web-operator taoguba jinghua [hours] [limit] [target]`
  Extract Taoguba `jinghua` posts from the last 24 hours by default.
- `omp-web-operator taoguba following [hours] [limit] [target]`
  Extract followed-content updates from the last 12 hours by default.
- `omp-web-operator open-post taoguba <url> [target]`
  Open one Taoguba post and extract the main post body.

### WPS 365 (365.kdocs.cn)

- `omp-web-operator kdocs search <query> [limit] [target]`
  Search WPS 365 documents; returns snippets and version ranking.
- `omp-web-operator kdocs open-doc <file_key> [main_target]`
  Open a document by file key; returns outline and first-page text.
- `omp-web-operator kdocs find-in-doc <keyword> [target]`
  Search for a keyword in the open document; returns match count and context.
- `omp-web-operator kdocs ask-ai <question> [target]`
  Ask WPS AI Docs Chat on the main page; returns answer text and referenced docs.
- `omp-web-operator kdocs close-doc [target]`
  Close the document tab, keeping the main 365.kdocs.cn/latest tab alive.

### X

- `omp-web-operator search x <query> [limit] [target]`
  Search `x.com` and extract up to 10 result summaries.
- `omp-web-operator open-post x <url> [target]`
  Open one `x.com` post URL and extract the current visible post text.
- `omp-web-operator x for-you [limit] [target]`
  Read the X.com For You recommendation feed.

### Weixin-Sogou

- `omp-web-operator search weixin-sogou <query> [limit] [target]`
  Search `weixin.sogou.com` (搜狗微信搜索) and extract article metadata (title, summary, account, time, link). Note: Only search is supported; full article content requires WeChat environment.

### Xueqiu

- `omp-web-operator search xueqiu <query> [limit] [target]`
  Search `xueqiu.com` and extract up to 10 discussion results.
- `omp-web-operator open-post xueqiu <url> [comment_limit] [target]`
  Open one `xueqiu.com` post URL and extract the main article plus visible comments.
- `omp-web-operator xueqiu hot [limit] [target]`
  Extract the current visible "热门" home timeline post list.
- `omp-web-operator xueqiu stock-info <symbol_or_url> [limit] [target]`
  Open one stock page and extract the latest visible announcements and discussions.

## Expected Future Structure

Each supported site should eventually have:

- scripts under `scripts/sites/<site>/`
- references under `references/sites/<site>/`
- tests under `tests/sites/<site>/`

Test commands:

- `omp-web-operator test list`
- `omp-web-operator test core`
- `omp-web-operator test site baidu`
- `omp-web-operator test site google`
- `omp-web-operator test site reddit`
- `omp-web-operator test site taoguba`
- `omp-web-operator test site weixin-sogou`
- `omp-web-operator test site x`
- `omp-web-operator test site xueqiu`
- `omp-web-operator test all`

## Definition Of Done For New Site Support

New site support is not complete unless it includes:

- workflow scripts
- a site reference document
- at least one smoke test
- registration in the unified test runner
