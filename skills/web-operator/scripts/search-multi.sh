#!/usr/bin/env bash
# search-multi — run searches on multiple platforms in parallel.
# Input:  --<platform> "<query>" pairs + optional --limit N
# Output: JSON array of { platform, query, results } objects.
#
# Example:
#   search-multi --google "AI agents" --baidu "AI 智能体" --limit 5
#
# Supported platforms: baidu, google, reddit, weixin-sogou, x, xueqiu,
#                      taoguba, duckduckgo
#
# Different-site searches run safely in parallel (isolated browser tabs).
# Max 5 concurrent searches to respect CDP connection limits.

set -euo pipefail

SKILL="${OMP_HOME:-$HOME/.oh-my-superpowers}/skills/web-operator"
MAX_PARALLEL=5

# --- parse arguments -----------------------------------------------------------

declare -A QUERIES=()
LIMIT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --limit)
      LIMIT="${2:-}"; shift 2 ;;
    --baidu|--google|--reddit|--weixin-sogou|--x|--xueqiu|--taoguba|--duckduckgo)
      platform="${1#--}"
      query="${2:-}"
      if [[ -z "$query" ]]; then
        echo "error: --${platform} requires a query argument" >&2; exit 1
      fi
      QUERIES["$platform"]="$query"
      shift 2 ;;
    *)
      echo "error: unknown argument: '$1'" >&2; exit 1 ;;
  esac
done

if [[ ${#QUERIES[@]} -eq 0 ]]; then
  echo "error: at least one --<platform> <query> pair is required" >&2
  exit 1
fi

# --- run searches in parallel --------------------------------------------------

TMPDIR_BASE="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_BASE"' EXIT

PIDS=()
PLATFORMS=()

for platform in "${!QUERIES[@]}"; do
  query="${QUERIES[$platform]}"
  outfile="${TMPDIR_BASE}/${platform}.json"

  limit_args=()
  if [[ -n "$LIMIT" ]]; then
    limit_args=("$LIMIT")
  fi

  # find the search script
  script="${SKILL}/scripts/sites/${platform}/search.sh"
  if [[ ! -f "$script" ]]; then
    echo "error: no search script for platform '${platform}'" >&2
    exit 1
  fi

  # launch in background
  bash "$script" "$query" "${limit_args[@]}" > "$outfile" 2>/dev/null &
  PIDS+=($!)
  PLATFORMS+=("$platform")

  # throttle: wait if we hit the concurrency cap
  if [[ ${#PIDS[@]} -ge $MAX_PARALLEL ]]; then
    wait "${PIDS[0]}" 2>/dev/null || true
    PIDS=("${PIDS[@]:1}")
  fi
done

# wait for all remaining
for pid in "${PIDS[@]}"; do
  wait "$pid" 2>/dev/null || true
done

# --- merge results into single JSON array --------------------------------------

# Build JSON: [ { "platform": "...", "query": "...", "results": [...] }, ... ]
{
  echo "["
  first=true
  for platform in "${PLATFORMS[@]}"; do
    outfile="${TMPDIR_BASE}/${platform}.json"
    query="${QUERIES[$platform]}"

    # default to empty array if search failed
    if [[ -f "$outfile" ]] && jq empty "$outfile" 2>/dev/null; then
      results="$(cat "$outfile")"
    else
      results="[]"
    fi

    if [[ "$first" == "true" ]]; then
      first=false
    else
      echo ","
    fi

    jq -n \
      --arg platform "$platform" \
      --arg query "$query" \
      --argjson results "$results" \
      '{ platform: $platform, query: $query, results: $results }'
  done
  echo "]"
} | jq '.'
