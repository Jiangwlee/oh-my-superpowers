# Web Operator Troubleshooting

This file explains the common failure modes when `scripts/cdp.mjs` cannot
connect to Chrome or cannot act on a target. Input is an observed failure such
as a websocket error, missing target, or daemon startup timeout. Output is the
next diagnostic step and the command or configuration change most likely to fix
the issue.

## Connection failures

- `No DevToolsActivePort found`
  Remote debugging is not enabled or the browser profile path is not one of the
  standard locations. Enable remote debugging at `chrome://inspect/#remote-debugging`
  or set `CDP_PORT_FILE` to the full `DevToolsActivePort` path.

- `WebSocket error: Received network error or non-101 status code`
  The `DevToolsActivePort` file may contain a stale browser websocket path after
  a browser restart. `scripts/cdp.mjs` resolves the port from that file, then
  prefers the live `webSocketDebuggerUrl` from `http://127.0.0.1:<port>/json/version`
  before falling back to the port file path.

- `Daemon failed to start — did you click Allow in Chrome?`
  The per-tab daemon could not complete startup within the retry window. Check
  for a Chrome approval prompt in the target tab and retry after accepting it.

## Targeting failures

- `No target matching prefix`
  Re-run `scripts/cdp.mjs list` and use the currently displayed unique prefix.

- `Ambiguous prefix`
  Use more characters from the `list` output until only one target matches.

## Interaction failures

- DOM selection changed after a click
  Recompute everything in one `eval` or use stable selectors instead of
  `querySelectorAll(...)[i]` across multiple calls.

- Text entry fails in an iframe
  Focus the element with `click` or `clickxy`, then use `type` instead of `eval`.

## Script entrypoint

- Implementation: [../../scripts/cdp.mjs](../../scripts/cdp.mjs)
