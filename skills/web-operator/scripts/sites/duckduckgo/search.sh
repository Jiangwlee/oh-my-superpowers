#!/usr/bin/env bash
# Search DuckDuckGo and return top results via ddgs Python package.
# Input: <query> [limit]
# Output: JSON array [{title, snippet, url}], same format as google/search.sh.
# Requires: uv (https://docs.astral.sh/uv/), no browser needed.
# Errors are printed to stderr and the script exits non-zero.

set -euo pipefail

usage() {
  printf 'usage: %s <query> [limit]\n' "$(basename "$0")" >&2
  exit 1
}

QUERY="${1:-}"
LIMIT="${2:-20}"

[[ -n "$QUERY" ]] || usage
[[ "$LIMIT" =~ ^[0-9]+$ ]] || { printf 'limit must be an integer\n' >&2; exit 1; }
(( LIMIT > 0 )) || { printf 'limit must be greater than zero\n' >&2; exit 1; }
(( LIMIT <= 20 )) || LIMIT=20

command -v uv >/dev/null 2>&1 || { printf 'uv is required: https://docs.astral.sh/uv/\n' >&2; exit 1; }

uv run --quiet --with ddgs python3 - "$LIMIT" "$QUERY" <<'PYEOF'
import sys, json
from ddgs import DDGS

limit = int(sys.argv[1])
query = sys.argv[2]

with DDGS() as ddgs:
    raw = list(ddgs.text(query, max_results=limit))

results = [
    {"title": r.get("title", ""), "snippet": r.get("body", "")[:280], "url": r.get("href", "")}
    for r in raw
    if r.get("href") and r.get("title")
]

print(json.dumps(results))
PYEOF
