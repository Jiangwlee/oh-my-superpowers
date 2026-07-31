#!/usr/bin/env bash
# Smoke test for the public Taoguba login command.
# Requires Chrome CDP and saved Taoguba credentials when not already signed in.
# Validates compact JSON success without exposing account or password fields.

set -euo pipefail

OUTPUT="$(omp web-operator taoguba login)"

jq -e '
  type == "object"
  and .ok == true
  and .site == "taoguba"
  and (.status == "logged_in" or .status == "already_logged_in")
  and (has("username") | not)
  and (has("password") | not)
' >/dev/null <<<"$OUTPUT"

printf '%s\n' "$OUTPUT"
