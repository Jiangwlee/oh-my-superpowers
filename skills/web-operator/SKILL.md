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
  Shared shell helpers for all site workflows: tab lifecycle management (`find_or_create_tab`), worker tab pool (`acquire_worker_tab` / `release_worker_tab`), URL encoding, and CDP wrappers.
- `sites`
  Repeatable workflows for specific websites such as `reddit.com`, `tgb.cn`, and `x.com`. Each site uses `core/common.sh` for tab management.

This repository uses a `core + sites + tests` layout.

## Quick Start

- Confirm Chrome remote debugging is enabled at `chrome://inspect/#remote-debugging`.
- For bundled sites, start from `omp-web-operator` site commands first. Do not start with `curl` if a matching site workflow already exists.
- Use `omp-web-operator cdp list` to identify the target tab prefix.
- Prefer stable URL navigation when a workflow can avoid brittle click paths.
- Load the relevant core or site reference before running a non-trivial workflow.

## When To Load References

Load core references for shared browser behavior:

- [references/core/index.md](references/core/index.md)
  Command selection and common workflow guidance.
- [references/core/cli-reference.md](references/core/cli-reference.md)
  CLI semantics, low-level CDP commands, and full site command list.
- [references/core/tab-management.md](references/core/tab-management.md)
  Automatic tab lifecycle, shared library API, and concurrent execution guidelines.
- [references/core/troubleshooting.md](references/core/troubleshooting.md)
  Connection failures, stale `DevToolsActivePort`, and approval-prompt issues.
- [references/core/sop-development.md](references/core/sop-development.md)
  The SOP development process, project structure, and definition of done.
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
- For bundled sites with dedicated workflows, prefer the site workflow over raw HTTP fetching. Do not use `curl` to read main content from `reddit.com`, `x.com`, `xueqiu.com`, `tgb.cn` / `taoguba.com.cn`, or `365.kdocs.cn`; these sites rely on dynamic rendering, login state, or anti-bot defenses, and raw HTTP usually returns shell HTML or incomplete content.
- Treat `google.com` and `weixin.sogou.com` the same way for search tasks: prefer `omp-web-operator search ...` over `curl`, because the browser workflow is far more reliable for rendered results, anti-bot handling, and stable extraction.
- For `365.kdocs.cn`, prefer `omp-web-operator kdocs ask-ai` when the task is question answering, summarization, document lookup, or cross-document synthesis. Use `kdocs search`, `open-doc`, and `find-in-doc` when the task explicitly needs direct document inspection or keyword verification.

## Preferred Command Map

When a supported site appears in the task, start from these commands before considering any generic HTTP fallback. **You MUST use these commands — do NOT claim the site is inaccessible or fabricate results.**

| 关键词 / Site | 命令 |
|--------------|------|
| 任意 URL / read article | `omp-web-operator read-url <url> [--limit N]` |
| 多平台搜索 / research | `omp-web-operator search-multi --<site> "<query>" [...] --limit N` |
| Google / 谷歌 | `omp-web-operator search google <query> [limit]` |
| Baidu / 百度 | `omp-web-operator search baidu <query> [limit]` |
| 微信搜索 / Weixin-Sogou / 搜狗微信 | `omp-web-operator search weixin-sogou <query> [limit]` |
| Reddit | `omp-web-operator search reddit <query> [limit]` → `omp-web-operator open-post reddit <url> [comment_limit]` |
| X / Twitter / 推特 | `omp-web-operator search x <query> [limit]` → `omp-web-operator open-post x <url>` |
| 雪球 / Xueqiu | `omp-web-operator search xueqiu <query> [limit]`、`omp-web-operator xueqiu hot [limit]`、`omp-web-operator open-post xueqiu <url> [comment_limit]` |
| 淘股吧 / Taoguba / TGB | `omp-web-operator taoguba jinghua [hours] [limit]`、`omp-web-operator taoguba following [hours] [limit]`、`omp-web-operator open-post taoguba <url>` |
| 金山文档 / KDocs / WPS 365 | `omp-web-operator kdocs ask-ai <question>`、`kdocs search/open-doc/find-in-doc` |
