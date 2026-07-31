#!/usr/bin/env bash
# Smoke test for authenticated, historical Taoguba search.
# Requires Chrome CDP and a logged-in Taoguba session.

set -euo pipefail

OUTPUT="$(
  omp web-operator search taoguba "1112 复盘" 12 \
    --year 2024 \
    --sort hot
)"

jq -e '
  .ok == true
  and .site == "taoguba"
  and .requested_filters.year == "2024"
  and .applied_filters.year == "2024"
  and .applied_filters.sort == "hot"
  and .result_count == 12
  and (.pagination.pages_visited | length) >= 2
  and ([.results[].displayed_time | startswith("2024-")] | all)
  and ([.results[].url | startswith("https://www.tgb.cn/a/")] | all)
' >/dev/null <<<"$OUTPUT"

printf '%s\n' "$OUTPUT"
