# Core Common Library

This document describes the shared shell library at `scripts/core/common.sh` that provides tab lifecycle management and CDP utilities for all site workflows.

## Overview

All site-specific `common.sh` files source this shared library to eliminate code duplication for:

- Tab discovery and creation
- URL encoding
- CDP wrapper functions

## Usage

Source the library from any site `common.sh`:

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../core/common.sh"
```

## Functions

### `find_or_create_tab <homepage_url> [domain]`

Finds an existing tab for the given domain or creates a new one.

**Parameters:**
- `homepage_url` - Full URL to navigate to when creating new tab (e.g., `https://www.baidu.com`)
- `domain` - Optional domain pattern for matching existing tabs. Extracted from homepage_url if not provided.

**Returns:**
- Target ID of existing or newly created tab

**Example:**
```bash
# Find existing baidu tab or create new one
target=$(find_or_create_tab "https://www.baidu.com" "baidu.com")
```

### `create_tab <homepage_url>`

Creates a new browser tab and navigates to the specified homepage.

**Parameters:**
- `homepage_url` - URL to open in the new tab

**Returns:**
- Target ID of the new tab

**Example:**
```bash
target=$(create_tab "https://www.reddit.com")
```

### `find_existing_tab <domain> [homepage_url]`

Finds an existing tab matching the domain pattern.

**Parameters:**
- `domain` - Domain pattern to match in tab URLs (e.g., `baidu.com`)
- `homepage_url` - Optional exact URL to prefer when multiple tabs match

**Returns:**
- Target ID of matching tab, or empty string if not found

### `url_encode <string>`

URL-encodes a string using jq.

**Parameters:**
- `string` - String to encode

**Returns:**
- URL-encoded string

### `cdp <command> [args...]`

Invokes the cdp.mjs CLI.

**Parameters:**
- `command` - CDP command (list, list_raw, eval, nav, open, etc.)
- `args...` - Command-specific arguments

### `cdp_list_raw`

Returns raw JSON list of all browser tabs.

### `cdp_eval <target> <expression>`

Evaluates a JavaScript expression in the specified tab.

**Parameters:**
- `target` - Target ID prefix
- `expression` - JavaScript expression to evaluate

### `acquire_worker_tab`

Gets a persistent worker tab for stateless reads (used by `read-url`). Finds an existing idle `about:blank` tab or creates one. Uses directory-based locking to prevent concurrent access to the same worker tab.

**Returns:**
- Target ID of the worker tab

**Example:**
```bash
TARGET=$(acquire_worker_tab)
trap 'release_worker_tab "$TARGET"' EXIT
cdp_nav "$TARGET" "$URL"
# ... extract content ...
```

### `release_worker_tab <target>`

Releases a worker tab back to the pool. Resets tab state via `cdp reset` (clears storage for the current origin, navigates to `about:blank#read-worker` to preserve the worker marker) and removes the lock.

**Parameters:**
- `target` - Target ID of the worker tab

### `require_cmd <command>`

Checks if a required command exists, exits with error if not found.

## Implementation Pattern

A typical site `common.sh` using this library:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../core/common.sh"

require_cmd jq

# Site-specific target finder
example_find_target() {
  local preferred="${1:-}"
  if [[ -n "$preferred" ]]; then
    printf '%s\n' "$preferred"
    return 0
  fi
  
  # Automatic tab management
  find_or_create_tab "https://www.example.com" "example.com"
}

# Additional site-specific helpers...
```

## Benefits

1. **Automatic tab lifecycle** - No manual tab management needed
2. **Domain isolation** - Each site uses its own dedicated tab
3. **Code deduplication** - ~300 lines of common code eliminated across sites
4. **Consistent behavior** - All sites follow the same tab management pattern
