# Automatic Tab Management

Each site workflow automatically manages its own Chrome tab:

1. **Find existing tab**: Each script looks for an existing tab of its domain (e.g., `baidu.com`)
2. **Create if missing**: If no matching tab exists, the script automatically creates a new one
3. **Isolation**: Different sites never share the same tab, preventing navigation conflicts

This means you **no longer need to specify target tabs manually** for normal usage:

```bash
# Automatic tab management - each site uses its own tab
omp-web-operator search baidu "query" 5        # Uses/creates baidu tab
omp-web-operator search google "query" 5       # Uses/creates google tab
omp-web-operator search weixin-sogou "query" 5 # Uses/creates sogou tab
```

## Shared Core Library

All site scripts source the shared helpers from `scripts/core/common.sh`:

- `find_or_create_tab <homepage_url> [domain]` - Find existing site tab or create new one (for search workflows)
- `create_tab <homepage_url>` - Create and navigate to a new tab
- `acquire_worker_tab` - Get a persistent worker tab for stateless reads (for read-url)
- `release_worker_tab <target>` - Reset state and release worker tab back to pool
- `url_encode <string>` - URL encode strings
- `cdp_eval <target> <expression>` - Evaluate JavaScript in tab

Site-specific `common.sh` files (e.g., `scripts/sites/baidu/common.sh`) are thin wrappers that call these shared functions with domain-specific parameters.

## Concurrent Execution Guidelines

**Same site**: Never run multiple scripts for the same site in parallel on the same tab. They will race for navigation.

**Different sites**: Safe to run in parallel because each uses its own dedicated tab:

```bash
# SAFE: Different sites in parallel
omp-web-operator search baidu "query" 5 &
omp-web-operator search google "query" 5 &
omp-web-operator search weixin-sogou "query" 5 &
wait
```

**CDP connection limit**: While different sites are isolated by tab, they still share Chrome's DevTools WebSocket server. Avoid launching too many scripts simultaneously (more than ~5) to prevent connection timeouts.
