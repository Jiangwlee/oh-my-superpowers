# Web Operator References

This reference index tells the agent what to read next, what each file covers,
and which script implements the behavior. Input is a browser task that needs
tab selection, page inspection, navigation, or extraction. Output is the
specific reference file to load and the `scripts/cdp.mjs` command to run.

## Read this file when

- You have already opened `SKILL.md` and need the next document to load.
- You need to choose between `list`, `nav`, `snap`, `eval`, or click/input commands.
- You need to debug why the local browser did not accept the CDP connection.

## Reference map

- [cli-reference.md](cli-reference.md)
  Command semantics, workflow guidance, and examples for the CLI implemented in [../../scripts/cdp.mjs](../../scripts/cdp.mjs).
- [common-library.md](common-library.md)
  Shared shell library (`scripts/core/common.sh`) providing automatic tab lifecycle management for all site workflows.
- [troubleshooting.md](troubleshooting.md)
  Failure modes for remote debugging, stale browser websocket paths, daemon startup, and tab targeting.
- [../sites/google/workflows.md](../sites/google/workflows.md)
  Stable SOPs and script entrypoints for `google.com` search result extraction.
- [../sites/kdocs/workflows.md](../sites/kdocs/workflows.md)
  Stable SOPs and script entrypoints for `365.kdocs.cn` document search, open, find, AI QA, and close.
- [../sites/chatgpt/workflows.md](../sites/chatgpt/workflows.md)
  Stable SOPs and script entrypoints for `chatgpt.com/images` prompt-to-image generation and local download.
- [../sites/x/workflows.md](../sites/x/workflows.md)
  Stable SOPs and script entrypoints for `x.com` search and single-post extraction.
- [../sites/reddit/workflows.md](../sites/reddit/workflows.md)
  Stable SOPs and script entrypoints for `reddit.com` search and post-plus-comments extraction.
- [../sites/taoguba/workflows.md](../sites/taoguba/workflows.md)
  Stable SOPs and script entrypoints for `tgb.cn` / Taoguba list filtering and post extraction.
- [../sites/xueqiu/workflows.md](../sites/xueqiu/workflows.md)
  Stable SOPs and script entrypoints for `xueqiu.com` search, hot posts, and post-plus-comments extraction.
- [sop-development.md](sop-development.md)
  The development workflow used to turn a new website task into a stable SOP, reference doc, and reusable script set.

## Common workflow

1. Run [../../scripts/cdp.mjs](../../scripts/cdp.mjs) `list` to discover targets.
2. Choose a target prefix that uniquely identifies the page you want.
3. Prefer `nav` when you know the destination URL.
4. Use `snap` to understand page structure before writing extraction logic.
5. Use a single `eval` to extract structured data.

## Script entrypoint

- Primary script: [../../scripts/cdp.mjs](../../scripts/cdp.mjs)
- Shared library: [../../scripts/core/common.sh](../../scripts/core/common.sh)
- Workflow scripts:
  [../../scripts/sites/google/search.sh](../../scripts/sites/google/search.sh),
  [../../scripts/sites/google/common.sh](../../scripts/sites/google/common.sh),
  [../../scripts/sites/kdocs/search.sh](../../scripts/sites/kdocs/search.sh),
  [../../scripts/sites/kdocs/open-doc.sh](../../scripts/sites/kdocs/open-doc.sh),
  [../../scripts/sites/kdocs/find-in-doc.sh](../../scripts/sites/kdocs/find-in-doc.sh),
  [../../scripts/sites/kdocs/ask-ai.sh](../../scripts/sites/kdocs/ask-ai.sh),
  [../../scripts/sites/kdocs/close-doc.sh](../../scripts/sites/kdocs/close-doc.sh),
  [../../scripts/sites/kdocs/common.sh](../../scripts/sites/kdocs/common.sh),
  [../../scripts/sites/chatgpt/generate-image.sh](../../scripts/sites/chatgpt/generate-image.sh),
  [../../scripts/sites/x/search.sh](../../scripts/sites/x/search.sh),
  [../../scripts/sites/x/open-post.sh](../../scripts/sites/x/open-post.sh),
  [../../scripts/sites/x/common.sh](../../scripts/sites/x/common.sh),
  [../../scripts/sites/xueqiu/search.sh](../../scripts/sites/xueqiu/search.sh),
  [../../scripts/sites/xueqiu/open-post.sh](../../scripts/sites/xueqiu/open-post.sh),
  [../../scripts/sites/xueqiu/hot.sh](../../scripts/sites/xueqiu/hot.sh),
  [../../scripts/sites/xueqiu/stock-info.sh](../../scripts/sites/xueqiu/stock-info.sh),
  [../../scripts/sites/xueqiu/common.sh](../../scripts/sites/xueqiu/common.sh),
  [../../scripts/sites/reddit/search.sh](../../scripts/sites/reddit/search.sh),
  [../../scripts/sites/reddit/open-post.sh](../../scripts/sites/reddit/open-post.sh),
  [../../scripts/sites/reddit/common.sh](../../scripts/sites/reddit/common.sh),
  [../../scripts/sites/taoguba/jinghua.sh](../../scripts/sites/taoguba/jinghua.sh),
  [../../scripts/sites/taoguba/following.sh](../../scripts/sites/taoguba/following.sh),
  [../../scripts/sites/taoguba/open-post.sh](../../scripts/sites/taoguba/open-post.sh),
  [../../scripts/sites/taoguba/common.sh](../../scripts/sites/taoguba/common.sh)
