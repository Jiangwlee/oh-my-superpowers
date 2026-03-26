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
- `click <target> <selector>`
  Clicks an element resolved by CSS selector.
- `clickxy <target> <x> <y>`
  Clicks by CSS pixel coordinates.
- `type <target> <text>`
  Inserts text at the current focus using CDP input APIs.
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

## Script entrypoint

- Implementation: [../../scripts/cdp.mjs](../../scripts/cdp.mjs)
