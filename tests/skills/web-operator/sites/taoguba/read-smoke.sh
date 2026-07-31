#!/usr/bin/env bash
# Smoke test for the public Taoguba main-post JSON reader.
# Requires Chrome CDP and a logged-in Taoguba session.

set -euo pipefail

DEFAULT_OUTPUT="$(
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
  and (.post.content | length) == 500
  and .post.content_length > 500
  and .post.content_returned_length == 500
  and .post.content_truncated == true
  and .post.content_limit == 500
  and (.post.published_at_asia_shanghai | endswith("+08:00"))
  and .source.cookies_persisted == false
' >/dev/null <<<"$DEFAULT_OUTPUT"

FULL_OUTPUT="$(
  omp web-operator taoguba read \
    "https://www.tgb.cn/a/2d85kP2xQdI" \
    --limit 0
)"

jq -e '
  .schema_version == 1
  and .ok == true
  and (.post.content | length) == .post.content_length
  and .post.content_returned_length == .post.content_length
  and .post.content_truncated == false
  and .post.content_limit == 0
' >/dev/null <<<"$FULL_OUTPUT"

DEFAULT_CONTENT="$(jq -r '.post.content' <<<"$DEFAULT_OUTPUT")"
FULL_PREFIX="$(jq -r '.post.content[0:500]' <<<"$FULL_OUTPUT")"
[[ "$DEFAULT_CONTENT" == "$FULL_PREFIX" ]]

printf '%s\n' "$DEFAULT_OUTPUT"
