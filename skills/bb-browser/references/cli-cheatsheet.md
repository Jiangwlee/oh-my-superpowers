---
# bb-browser CLI Cheatsheet
# Purpose: Quick reference for all bb-browser commands
# Sections: Daemon | Navigation | Page Inspection | Network | Eval | Site Adapters | MCP
---

# bb-browser CLI Cheatsheet

## Daemon Management

```bash
bb-browser daemon                    # Start the daemon (port 19824)
curl http://localhost:19824/sse      # Check connectivity (expects: event: connected)
pkill -f "bb-browser daemon"         # Kill daemon if stuck
```

## Installation & Updates

```bash
bb-browser --version                 # Show version
bb-browser site update               # Pull latest community adapters
bb-browser site list                 # List all available site commands
bb-browser guide                     # Print full adapter development tutorial
```

## Navigation

```bash
bb-browser open <url>                # Open URL in a new tab
bb-browser refresh --tab <tabId>     # Refresh a tab
```

## Page Inspection

```bash
bb-browser snapshot                  # Full accessibility snapshot of current page
bb-browser snapshot | head -3        # Get tab ID from first lines
```

## Network Inspection

```bash
bb-browser network clear --tab <id>              # Clear captured requests
bb-browser network requests --tab <id>           # List captured requests
bb-browser network requests --filter "api" --tab <id>        # Filter by keyword
bb-browser network requests --with-body --json --tab <id>    # Include request bodies
```

## JavaScript Evaluation

```bash
bb-browser eval "<JS expression>"    # Evaluate JS in page context (returns string)

# Useful patterns:
bb-browser eval "document.title"
bb-browser eval "document.cookie"
bb-browser eval "JSON.stringify(window.__APP_STATE__, null, 2)"
bb-browser eval "fetch('/api/data', {credentials:'include'}).then(r=>r.json()).then(d=>JSON.stringify(d))"
```

## Site Adapters

```bash
bb-browser site <platform>/<command>            # Run an adapter
bb-browser site <platform>/<command> "arg"      # Run with positional argument
bb-browser site <platform>/<command> --json     # JSON output
bb-browser site info <platform>/<command>       # Show adapter metadata and usage
bb-browser site list                            # List all adapters
```

### Adapter file locations

```
~/.bb-browser/sites/<platform>/<command>.js     # Private (highest priority)
~/.bb-browser/bb-sites/<platform>/<command>.js  # Community (read-only)
```

## MCP Mode

```bash
bb-browser --mcp                     # Start as MCP server (stdio transport)
```

MCP config for Claude Code / Cursor:
```json
{
  "mcpServers": {
    "bb-browser": {
      "command": "bb-browser",
      "args": ["--mcp"]
    }
  }
}
```

## Systemd Service (auto-start)

```bash
systemctl --user status bb-browser-daemon.service
systemctl --user start bb-browser-daemon.service
systemctl --user stop bb-browser-daemon.service
systemctl --user restart bb-browser-daemon.service
```

## Common Examples

```bash
# Check what's hot on V2ex (no login needed)
bb-browser site v2ex/hot

# Search Wikipedia
bb-browser site wikipedia/summary "机器学习"

# Zhihu hot list (login required)
bb-browser site zhihu/hot --json

# Bilibili search (login required)
bb-browser site bilibili/search "Python教程"

# GitHub fork a repo
bb-browser site github/fork owner/repo
```
