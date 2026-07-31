#!/usr/bin/env bash
# Smoke test for the public Taoguba main-post JSON reader.
# Requires Chrome CDP and a logged-in Taoguba session.

set -euo pipefail

OUTPUT="$(
  omp web-operator taoguba read \
    "https://www.tgb.cn/a/2d85kP2xQdI"
)"

jq -e '
  .schema_version == 1
  and .ok == true
  and .site == "taoguba"
  and .post.post_id == "2d85kP2xQdI"
  and (.post.url | startswith("https://www.tgb.cn/a/"))
  and (.post.title | length) > 0
  and (.post.content | length) > 100
  and (.post.published_at_asia_shanghai | endswith("+08:00"))
  and .source.cookies_persisted == false
' >/dev/null <<<"$OUTPUT"

printf '%s\n' "$OUTPUT"
