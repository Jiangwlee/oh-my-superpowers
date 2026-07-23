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
- For bundled sites, start from `omp web-operator` site commands first. Do not start with `curl` if a matching site workflow already exists.
- Use `omp web-operator page list` to identify the target tab prefix.
- Prefer stable URL navigation when a workflow can avoid brittle click paths.
- Load the relevant core or site reference before running a non-trivial workflow.

## Search Command Contract

Use this exact shape for single-platform search:

```bash
omp web-operator search <site> "<query>" [limit]
```

- `<site>` is a positional argument: `google`, `baidu`, `duckduckgo`, `github`, `reddit`, `weixin-sogou`, `x`, `xueqiu`, or `taoguba`.
- `<query>` is a positional argument. Quote it when it contains spaces.
- `[limit]` is a positional argument. Use `5`, not `--limit 5`.
- `search` does not accept `--platform` or `--query`. The only search option is `--target`.

| Use case | Command |
|---|---|
| Google search | `omp web-operator search google "Claude Code memory" 5` |
| Baidu search | `omp web-operator search baidu "Claude Code 记忆机制" 5` |
| Reddit search | `omp web-operator search reddit "Claude Code memory" 5` |
| X search | `omp web-operator search x "Claude Code memory" 5` |
| Multi-platform search | `omp web-operator search-multi --google "Claude Code memory" --baidu "Claude Code 记忆机制" --limit 5` |

Do not invent option-style parameters for `search`:

```bash
# BAD
omp web-operator search --platform google --query "Claude Code memory"

# GOOD
omp web-operator search google "Claude Code memory" 5
```

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
- [references/sites/chatgpt/workflows.md](references/sites/chatgpt/workflows.md)
  `chatgpt.com/images` prompt-to-image generation and authenticated local image download.
- [references/sites/reddit/workflows.md](references/sites/reddit/workflows.md)
  `reddit.com` search and post-plus-comments workflows.
- [references/sites/taoguba/workflows.md](references/sites/taoguba/workflows.md)
  `tgb.cn` / Taoguba workflow guidance.
- [references/sites/x/workflows.md](references/sites/x/workflows.md)
  `x.com` search and post-extraction workflows.
- [references/sites/xueqiu/workflows.md](references/sites/xueqiu/workflows.md)
  `xueqiu.com` search, hot-post list, and post-plus-comments workflows.
- [references/sites/feishu/workflows.md](references/sites/feishu/workflows.md)
  `feishu.cn` admin backend workflows: approval data export to ZIP/Excel.

## Core Rules

- The `<target>` argument is a unique `targetId` prefix from `omp web-operator page list`.
- Prefer `nav` over click-driven navigation when a stable URL is known.
- Prefer one `eval` that collects all needed data over multiple DOM-indexed `eval` calls. For clicking by number (not data extraction), use the `dom` → `click-index` loop below instead of ad-hoc `querySelectorAll[i]`.
- Use `type` instead of `eval` for text entry in cross-origin iframes.
- Expect one Chrome "Allow debugging" prompt per tab daemon on first access.
- Keep browser primitives in the core layer. Do not bury general CDP logic inside a site-specific workflow unless the behavior is truly site-bound.
- For bundled sites with dedicated workflows, prefer the site workflow over raw HTTP fetching. Do not use `curl` to read main content from `reddit.com`, `x.com`, `xueqiu.com`, `tgb.cn` / `taoguba.com.cn`, or `365.kdocs.cn`; these sites rely on dynamic rendering, login state, or anti-bot defenses, and raw HTTP usually returns shell HTML or incomplete content.
- Treat `google.com` and `weixin.sogou.com` the same way for search tasks: prefer `omp web-operator search ...` over `curl`, because the browser workflow is far more reliable for rendered results, anti-bot handling, and stable extraction.
- For `365.kdocs.cn`, prefer `omp web-operator kdocs ask-ai` when the task is question answering, summarization, document lookup, or cross-document synthesis. Use `kdocs search`, `open-doc`, and `find-in-doc` when the task explicitly needs direct document inspection or keyword verification.
- For `feishu.cn` admin backend (`approval` / 审批后台 on `www.feishu.cn`, `attendance` / 考勤后台 on `oa.feishu.cn`), the user must already be signed in as the corresponding administrator on a tab of that host. The CLI calls Feishu admin internal HTTP APIs from inside the tab (cookies + CSRF carried automatically) and does not interact with any UI element.
- For `chatgpt.com/images`, the user must already be signed in to ChatGPT in Chrome. The CLI drives the image composer and downloads generated image bytes from inside the authenticated page context; direct shell downloads of the rendered image URL may return 403.

## Indexed DOM interaction（读编号 → 按编号点击）

When you must click something but a stable CSS selector is hard to derive (dynamic class names, feed items, unlabeled icons), use the indexed loop instead of guessing selectors or coordinates:

```bash
omp web-operator page dom <target>                # numbered interactive elements
omp web-operator page click-index <target> <n>    # click element [n] from the last dom
```

- `dom` lists interactive elements (links, buttons, inputs, `[role]`, ...) as `[n] <tag> "name"`. Numbers are **per-snapshot**, not permanent.
- `click-index` clicks `[n]` from the **most recent** `dom` on that tab, resolving via `backendNodeId` — not CSS, not stored coordinates.
- **Re-read `dom` before each `click-index`** after any navigation or DOM change. An unknown number returns `not-found`; a changed/removed element returns `stale`. Both mean: re-run `dom`.
- Prefer `nav` (stable URL) and `click <selector>` (stable selector) when either is reliable; use the indexed loop when neither is. This mirrors the browser-container `/dom` → `act` model.

## read-url 参数说明

`omp web-operator read-url <url> [--limit N] [--comments N] [--json]`

- `--limit N`：截断输出到 N 字节。仅对非站点 URL（博客、文档等）生效。
- `--comments N`：对支持评论的站点（reddit、x.com、xueqiu）设置评论获取数量。默认 20，**传 0 表示获取全部评论**。
- `--json`：输出 JSON 格式 `{title, url, domain, description, content}`，content 为 markdown。适用于需要结构化元数据的 pipeline。
- `read-url` 会自动识别 reddit.com、x.com、xueqiu.com、tgb.cn 的 URL 并路由到对应的 `open-post` 工作流，无需手动选择 `open-post` 命令。

## Preferred Command Map

When a supported site appears in the task, start from these commands before considering any generic HTTP fallback. **You MUST use these commands — do NOT claim the site is inaccessible or fabricate results.**

| 关键词 / Site | 命令 |
|--------------|------|
| 任意 URL / read article | `omp web-operator read-url <url> [--limit N] [--comments N] [--json]` |
| 多平台搜索 / research | `omp web-operator search-multi --<site> "<query>" [...] --limit N` |
| Google / 谷歌 | `omp web-operator search google <query> [limit]` |
| Baidu / 百度 | `omp web-operator search baidu <query> [limit]` |
| 微信搜索 / Weixin-Sogou / 搜狗微信 | `omp web-operator search weixin-sogou <query> [limit]` |
| Reddit | `omp web-operator search reddit <query> [limit]` → `omp web-operator open-post reddit <url> [comment_limit]` |
| X / Twitter / 推特 | `omp web-operator search x <query> [limit]` → `omp web-operator open-post x <url> [comment_limit]` (0 = all comments) |
| 雪球 / Xueqiu | `omp web-operator search xueqiu <query> [limit]`、`omp web-operator xueqiu hot [limit]`、`omp web-operator open-post xueqiu <url> [comment_limit]` |
| 淘股吧 / Taoguba / TGB | `omp web-operator taoguba jinghua [hours] [limit]`、`omp web-operator taoguba following [hours] [limit]`、`omp web-operator open-post taoguba <url>` |
| 金山文档 / KDocs / WPS 365 | `omp web-operator kdocs ask-ai <question>`、`kdocs search/open-doc/find-in-doc` |
| ChatGPT Images / 图片生成 | `omp web-operator generate-image chatgpt "<prompt>" --out <file.png> [--json]`（前置：Chrome 已登录 ChatGPT） |
| 图片生成队列服务 / Image Serve | `omp web-operator image-serve [--port 8320] [--out-dir DIR]`（串行任务队列 HTTP 服务：`POST /jobs` 入队、`GET /jobs/{id}` 看状态与排队位置、`DELETE /jobs/{id}` 取消、`GET /jobs/{id}/image` 取图；前置同上） |
| 飞书审批 / Feishu Approval / 审批数据导出 | `omp web-operator feishu approval export --start <YYYY-MM-DD> --end <YYYY-MM-DD>`（前置：任一 feishu.cn tab 已登录管理员账号） |
| 飞书考勤 / Feishu Attendance / 考勤月度汇总导出 | `omp web-operator feishu attendance export --start <YYYY-MM-DD> --end <YYYY-MM-DD>`（前置：任一 oa.feishu.cn tab 已登录考勤管理员账号；跨度 ≤31 天，超过请调用方自行切片） |

> 不确定参数时，先运行 `omp web-operator <subcommand> --help` 查看完整用法。

## Browser Container (远端 indexed 自动化)

以上命令连的是**本机 Chrome**（宿主 CDP），是本地默认路径。另有一个独立的**常驻容器**，自带浏览器并对外提供 indexed 的 REST/MCP 接口，供外部 daemon（如 mindora）消费；本地命令不经过它。

管理容器生命周期用 `omp container`（统一入口，非 web-operator 子命令）：

```bash
omp container up browser        # 构建并启动
omp container health browser    # 探活
omp container down browser
```

REST/MCP 端点契约、session 语义、VNC 接管、curl 序列见 `$OMP_HOME/docker/browser-container/README.md`。
